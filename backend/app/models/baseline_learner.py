import math
from dataclasses import asdict, dataclass
from datetime import datetime

import pandas as pd

from app.cache.cache_manager import cache, cache_result
from app.ingestion.es_client import INDEX_NAMES
from app.logging_config import get_logger

logger = get_logger(__name__)

@dataclass
class EntityBaseline:
    entity_key: str
    last_updated: datetime
    observation_count: int
    # Network baselines
    avg_conn_per_minute: float
    std_conn_per_minute: float
    avg_unique_dst_ports: float
    std_unique_dst_ports: float
    typical_protocols: list[str]
    typical_dst_ports: list[int]
    # Process baselines
    avg_process_spawn_count: float
    std_process_spawn_count: float
    known_process_names: list[str]
    avg_args_count: float
    # Alert baselines
    avg_alert_count: float
    std_alert_count: float
    avg_risk_score: float

class BaselineLearner:
    def __init__(self, min_observations: int = 10, decay_factor: float = 0.95):
        self.min_observations = min_observations
        self.decay_factor = decay_factor

    @cache_result(ttl_seconds=300, key_fn=lambda self, es, entity_key: f"baseline:{entity_key}")
    async def get_baseline(self, es, entity_key: str) -> EntityBaseline | None:
        try:
            resp = await es.get(index=INDEX_NAMES["baselines"], id=entity_key)
            source = resp.get("_source", {})
            if "last_updated" in source and isinstance(source["last_updated"], str):
                source["last_updated"] = datetime.fromisoformat(source["last_updated"].replace("Z", "+00:00"))
            return EntityBaseline(**source)
        except Exception:
            return None

    def _update_ema(self, old_avg: float, old_std: float, new_value: float) -> tuple[float, float]:
        """Calculates new EMA for mean and standard deviation."""
        new_avg = self.decay_factor * old_avg + (1 - self.decay_factor) * new_value
        variance = self.decay_factor * (old_std ** 2) + (1 - self.decay_factor) * ((new_value - new_avg) ** 2)
        new_std = math.sqrt(variance)
        return new_avg, new_std

    async def update_baseline(self, es, entity_key: str, feature_row: dict):
        baseline = await self.get_baseline(es, entity_key)

        if baseline is None:
            baseline = EntityBaseline(
                entity_key=entity_key,
                last_updated=datetime.utcnow(),
                observation_count=1,
                avg_conn_per_minute=float(feature_row.get("conn_count_1m", 0)),
                std_conn_per_minute=0.0,
                avg_unique_dst_ports=float(feature_row.get("unique_dst_ports_1m", 0)),
                std_unique_dst_ports=0.0,
                typical_protocols=[],
                typical_dst_ports=[],
                avg_process_spawn_count=float(feature_row.get("process_spawn_count_1m", 0)),
                std_process_spawn_count=0.0,
                known_process_names=[],
                avg_args_count=float(feature_row.get("avg_args_count", 0)),
                avg_alert_count=float(feature_row.get("recent_alert_count", 0)),
                std_alert_count=0.0,
                avg_risk_score=float(feature_row.get("avg_risk_score", 0))
            )
        else:
            baseline.observation_count += 1
            baseline.last_updated = datetime.utcnow()

            # Network Updates
            c_val = float(feature_row.get("conn_count_1m", 0))
            baseline.avg_conn_per_minute, baseline.std_conn_per_minute = self._update_ema(
                baseline.avg_conn_per_minute, baseline.std_conn_per_minute, c_val
            )

            p_val = float(feature_row.get("unique_dst_ports_1m", 0))
            baseline.avg_unique_dst_ports, baseline.std_unique_dst_ports = self._update_ema(
                baseline.avg_unique_dst_ports, baseline.std_unique_dst_ports, p_val
            )

            # Process Updates
            sp_val = float(feature_row.get("process_spawn_count_1m", 0))
            baseline.avg_process_spawn_count, baseline.std_process_spawn_count = self._update_ema(
                baseline.avg_process_spawn_count, baseline.std_process_spawn_count, sp_val
            )

            arg_val = float(feature_row.get("avg_args_count", 0))
            baseline.avg_args_count = self.decay_factor * baseline.avg_args_count + (1 - self.decay_factor) * arg_val

            # Alert Updates
            al_val = float(feature_row.get("recent_alert_count", 0))
            baseline.avg_alert_count, baseline.std_alert_count = self._update_ema(
                baseline.avg_alert_count, baseline.std_alert_count, al_val
            )

            r_val = float(feature_row.get("avg_risk_score", 0))
            baseline.avg_risk_score = self.decay_factor * baseline.avg_risk_score + (1 - self.decay_factor) * r_val

        doc = asdict(baseline)
        doc["last_updated"] = doc["last_updated"].isoformat()

        try:
            await es.index(index=INDEX_NAMES["baselines"], id=entity_key, document=doc)
        except Exception as e:
            logger.warning("failed_to_store_baseline", entity_key=entity_key, error=str(e))

    def compute_deviation_ratios(self, baseline: EntityBaseline, feature_row: dict) -> dict[str, float]:
        if baseline.observation_count < self.min_observations:
            return {}

        deviations = {}

        def calc_dev(current: float, avg: float, std: float) -> float:
            ratio = abs(current - avg) / max(std, 0.01)
            return min(ratio, 10.0) # Cap at 10x

        if "conn_count_1m" in feature_row:
            deviations["conn_count_1m"] = calc_dev(
                float(feature_row["conn_count_1m"]),
                baseline.avg_conn_per_minute,
                baseline.std_conn_per_minute
            )

        if "unique_dst_ports_1m" in feature_row:
            deviations["unique_dst_ports_1m"] = calc_dev(
                float(feature_row["unique_dst_ports_1m"]),
                baseline.avg_unique_dst_ports,
                baseline.std_unique_dst_ports
            )

        if "process_spawn_count_1m" in feature_row:
            deviations["process_spawn_count_1m"] = calc_dev(
                float(feature_row["process_spawn_count_1m"]),
                baseline.avg_process_spawn_count,
                baseline.std_process_spawn_count
            )

        return deviations

    def format_deviation_context(self, deviations: dict[str, float], feature_row: dict, baseline: EntityBaseline) -> str:
        parts = []

        mapping = {
            "conn_count_1m": ("conn_per_minute", baseline.avg_conn_per_minute, baseline.std_conn_per_minute),
            "unique_dst_ports_1m": ("unique_dst_ports", baseline.avg_unique_dst_ports, baseline.std_unique_dst_ports),
            "process_spawn_count_1m": ("process_spawn_count", baseline.avg_process_spawn_count, baseline.std_process_spawn_count)
        }

        for feat, dev in deviations.items():
            if dev > 2.0 and feat in mapping:
                friendly_name, avg, std = mapping[feat]
                current = float(feature_row.get(feat, 0))
                parts.append(f"{friendly_name} is {dev:.1f}x above baseline (current: {current:.1f}, normal: {avg:.1f}±{std:.1f})")

        return "; ".join(parts)

    async def update_all_baselines(self, es, feature_df: pd.DataFrame):
        if feature_df.empty:
            return

        grouped = feature_df.groupby("entity_key")
        for entity_key, group in grouped:
            latest_row = group.iloc[-1].to_dict()
            await self.update_baseline(es, entity_key, latest_row)
            await cache.delete(f"baseline:{entity_key}")
