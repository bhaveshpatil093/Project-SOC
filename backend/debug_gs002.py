import asyncio
import pandas as pd
from tests.regression.golden_dataset import GOLDEN_SCENARIOS
from app.ingestion.normalizer import normalize_batch, to_dataframe
from app.features.network_features import extract_all_network_features
from app.features.feature_merger import merge_features
from app.models.rule_engine import evaluate_rules

async def run():
    scenario = next(s for s in GOLDEN_SCENARIOS if s["scenario_id"] == "GS-002")
    raw_logs = scenario["raw_logs"]
    
    net_logs = [l for l in raw_logs if "message" in l and "SRC=" in l.get("message", "")]
    
    from app.ingestion.scheduler import get_window_bucket
    import dataclasses

    def enrich_normalized(logs):
        if not logs:
            return pd.DataFrame()
        enriched = []
        for log in logs:
            doc = dataclasses.asdict(log)
            doc["window_bucket"] = get_window_bucket(log.timestamp).isoformat() + "Z"
            user = log.user_name or "system"
            doc["entity_key"] = f"{log.host_id}|{user}"
            enriched.append(doc)
        return pd.DataFrame(enriched)

    net_df = enrich_normalized(normalize_batch(net_logs, "network"))
    print("Net DF columns:", net_df.columns if not net_df.empty else "Empty")
    if not net_df.empty:
        print("Net DF sample src_port:", net_df.iloc[0].get("src_port"))
    
    net_feat = extract_all_network_features(net_df) if not net_df.empty else pd.DataFrame()
    print("Net Feat:", net_feat.to_dict('records') if not net_feat.empty else "Empty")
    
    # rule
    if not net_feat.empty:
        rule_eval = evaluate_rules(net_feat.iloc[0].to_dict())
        print("Rule eval:", rule_eval)

asyncio.run(run())
