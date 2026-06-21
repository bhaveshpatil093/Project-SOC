import numpy as np
import pandas as pd
from datetime import datetime
from dataclasses import dataclass, asdict
import pytz
import logging

logger = logging.getLogger(__name__)

@dataclass
class TemporalBaseline:
    entity_key: str
    hourly_profiles: dict
    business_hours: tuple
    is_business_hours_entity: bool

class TemporalAnalyzer:
    def __init__(self, timezone: str = "Asia/Kolkata"):
        self.timezone = pytz.timezone(timezone)
        self.INDEX_NAME = "soc-temporal-baselines"

    def _get_local_time(self, timestamp: datetime) -> datetime:
        if timestamp.tzinfo is None:
            timestamp = pytz.utc.localize(timestamp)
        return timestamp.astimezone(self.timezone)

    def build_temporal_baselines(self, feature_df: pd.DataFrame, entity_key: str) -> TemporalBaseline:
        """Builds a 168-hour baseline profile from a feature dataframe."""
        if feature_df.empty:
            return TemporalBaseline(entity_key, {}, (9, 18), False)
            
        profiles = {}
        # Assumes feature_df has 'timestamp' column
        if 'timestamp' in feature_df.columns:
            # Add hour and weekday columns
            df = feature_df.copy()
            df['local_time'] = pd.to_datetime(df['timestamp']).apply(self._get_local_time)
            df['hour'] = df['local_time'].dt.hour
            df['weekday'] = df['local_time'].dt.weekday
            
            # Numeric features only
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            exclude_cols = ['hour', 'weekday', 'timestamp', 'event_id']
            features = [c for c in numeric_cols if c not in exclude_cols]
            
            grouped = df.groupby(['weekday', 'hour'])
            
            for (weekday, hour), group in grouped:
                key = f"{weekday}_{hour}"
                profiles[key] = {}
                for feat in features:
                    mean_val = float(group[feat].mean())
                    std_val = float(group[feat].std())
                    if np.isnan(std_val): std_val = 0.0
                    profiles[key][feat] = (mean_val, std_val)
                    
            # Determine if this is a business hours entity (most activity between 9 and 18, Mon-Fri)
            bus_df = df[(df['weekday'] < 5) & (df['hour'] >= 9) & (df['hour'] <= 18)]
            is_bus_entity = len(bus_df) > (len(df) * 0.5)
        else:
            is_bus_entity = False
            
        return TemporalBaseline(
            entity_key=entity_key,
            hourly_profiles=profiles,
            business_hours=(9, 18),
            is_business_hours_entity=is_bus_entity
        )

    def is_off_hours(self, timestamp: datetime, baseline: TemporalBaseline) -> tuple[bool, float]:
        """Returns (is_off_hours, severity_multiplier)"""
        local_t = self._get_local_time(timestamp)
        hour = local_t.hour
        weekday = local_t.weekday()
        
        # Weekend
        if weekday >= 5:
            if hour >= 0 and hour < 6:
                return True, 2.0
            return True, 1.5
            
        # Weekday
        start, end = baseline.business_hours
        if hour >= start and hour <= end:
            return False, 1.0
        elif hour > end and hour < 22:
            return True, 1.3  # Evening
        elif hour >= 22 or hour < 6:
            return True, 1.8  # Night / Early morning
        else:
            return True, 1.5

    def compute_temporal_anomaly_score(self, feature_row: dict, baseline: TemporalBaseline, timestamp: datetime) -> dict:
        local_t = self._get_local_time(timestamp)
        hour = local_t.hour
        weekday = local_t.weekday()
        key = f"{weekday}_{hour}"
        
        is_off, severity = self.is_off_hours(timestamp, baseline)
        
        # If no profile for this exact slot, we consider it a mild temporal anomaly
        if key not in baseline.hourly_profiles or not baseline.hourly_profiles[key]:
            return {
                "temporal_score": 0.5 * severity,
                "is_off_hours": is_off,
                "off_hours_severity": severity,
                "most_anomalous_time_features": [],
                "context": f"Activity at {local_t.strftime('%H:%M')} {self.timezone.zone} (No prior baseline for this time slot)"
            }
            
        profile = baseline.hourly_profiles[key]
        anomalies = []
        max_z = 0.0
        
        for feat, val in feature_row.items():
            if feat in profile and isinstance(val, (int, float)):
                mean_v, std_v = profile[feat]
                if std_v > 0:
                    z = (val - mean_v) / std_v
                    if z > 2.0:
                        anomalies.append((feat, z, val, mean_v))
                        max_z = max(max_z, z)
                elif val > 0 and mean_v == 0:
                    # Occurred when historical std and mean were 0
                    z = 3.0
                    anomalies.append((feat, z, val, mean_v))
                    max_z = max(max_z, z)
                    
        anomalies.sort(key=lambda x: x[1], reverse=True)
        top_features = [a[0] for a in anomalies[:3]]
        
        if max_z > 0:
            temporal_score = min(1.0, (max_z / 10.0)) * severity
            top_feat = anomalies[0]
            context = f"Activity at {local_t.strftime('%H:%M %Z')} is {top_feat[1]:.1f}x above the normal {local_t.strftime('%A %I%p')} baseline for {top_feat[0]}."
        else:
            temporal_score = 0.0
            context = f"Activity conforms to typical {local_t.strftime('%A %I%p')} baseline."
            
        return {
            "temporal_score": temporal_score,
            "is_off_hours": is_off,
            "off_hours_severity": severity,
            "most_anomalous_time_features": top_features,
            "context": context
        }

    async def store_temporal_baseline(self, es, baseline: TemporalBaseline):
        try:
            doc = asdict(baseline)
            await es.index(index=self.INDEX_NAME, id=baseline.entity_key, document=doc)
            logger.info(f"Stored temporal baseline for {baseline.entity_key}")
        except Exception as e:
            logger.error(f"Failed to store temporal baseline: {e}")

    async def load_temporal_baseline(self, es, entity_key: str) -> TemporalBaseline | None:
        try:
            res = await es.get(index=self.INDEX_NAME, id=entity_key, ignore_unavailable=True)
            if res and res.get("found"):
                data = res["_source"]
                return TemporalBaseline(**data)
        except Exception as e:
            logger.debug(f"No temporal baseline found for {entity_key}: {e}")
        return None
