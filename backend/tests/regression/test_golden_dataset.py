import pytest
import pandas as pd
from unittest.mock import AsyncMock, patch

from app.ingestion.normalizer import normalize_batch, to_dataframe
from app.features.network_features import extract_all_network_features
from app.features.process_features import extract_all_process_features
from app.features.alert_features import extract_all_alert_features
from app.features.feature_merger import merge_features
from app.scoring.explainability import explain_scoring_result
from app.scoring.threat_engine import ThreatEngine

# Import the generated scenarios
from tests.regression.golden_dataset import GOLDEN_SCENARIOS

import pytest_asyncio

@pytest_asyncio.fixture
async def full_pipeline():
    """Returns a fully initialized ThreatEngine for regression testing."""
    from app.models.model_manager import ModelManager
    from app.scoring.explainability import ExplainabilityEngine
    
    model_manager = ModelManager()
    await model_manager.initialize()
    explain_engine = ExplainabilityEngine()
    
    engine = ThreatEngine(es=AsyncMock(), model_manager=model_manager, explainability_engine=explain_engine)
    return engine

async def run_full_pipeline_on_logs(raw_logs, threat_engine):
    """Manually push raw_logs through the normalized extraction, scoring, and explaining phases."""
    net_logs = [l for l in raw_logs if "message" in l and "SRC=" in l.get("message", "")]
    proc_logs = [l for l in raw_logs if "process" in l]
    alert_logs = [l for l in raw_logs if "kibana" in l]

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
    proc_df = enrich_normalized(normalize_batch(proc_logs, "process"))
    alert_df = enrich_normalized(normalize_batch(alert_logs, "security_alert"))

    net_feat = extract_all_network_features(net_df) if not net_df.empty else pd.DataFrame()
    proc_feat = extract_all_process_features(proc_df) if not proc_df.empty else pd.DataFrame()
    alert_feat = extract_all_alert_features(alert_df) if not alert_df.empty else pd.DataFrame()

    feat_df = merge_features(net_feat, proc_feat, alert_feat)
    normalized_df = pd.concat([net_df, proc_df, alert_df], ignore_index=True) if any(not d.empty for d in [net_df, proc_df, alert_df]) else pd.DataFrame()

    if feat_df.empty:
        return None

    scoring_results = await threat_engine.model_manager.score_all_entities(feat_df, normalized_df)
    if not scoring_results:
        return None

    res = scoring_results[0]
    
    # Evaluate Threat Level manually (normally done in ThreatEngine cycle)
    if res.threat_score >= 0.8:
        res.threat_level = "critical"
    elif res.threat_score >= 0.6:
        res.threat_level = "high"
    elif res.threat_score >= 0.4:
        res.threat_level = "medium"
    else:
        res.threat_level = "low"

    row_match = feat_df[feat_df['entity_key'] == res.entity_key]
    feature_row = row_match.iloc[0].to_dict() if not row_match.empty else {}
    
    explained_res = explain_scoring_result(res, feature_row, threat_engine.explainability_engine)
    return explained_res

@pytest.mark.parametrize("scenario", GOLDEN_SCENARIOS, ids=lambda s: s["scenario_id"])
@pytest.mark.asyncio
async def test_golden_scenario(scenario, full_pipeline):
    result = await run_full_pipeline_on_logs(scenario["raw_logs"], full_pipeline)

    assert result is not None, f"{scenario['scenario_id']}: Pipeline returned no results."

    expected = scenario["expected"]
    low, high = expected["threat_score_range"]
    assert low <= result.threat_score <= high, \
        f"{scenario['scenario_id']}: score {result.threat_score} outside [{low},{high}]"

    if "threat_level" in expected:
        assert result.threat_level == expected["threat_level"]

    if "triggered_rules" in expected:
        triggered_ids = result.triggered_rules
        for expected_rule in expected["triggered_rules"]:
            assert expected_rule in triggered_ids

    if "mitre_techniques" in expected:
        for technique in expected["mitre_techniques"]:
            assert technique in result.mitre_technique_ids

@pytest.mark.asyncio
async def test_golden_dataset_summary_report(full_pipeline):
    """Smoke test ensuring all 50 scenarios run cleanly (already verified via parametrize)."""
    success = 0
    for scenario in GOLDEN_SCENARIOS:
        res = await run_full_pipeline_on_logs(scenario["raw_logs"], full_pipeline)
        if res:
            success += 1
    
    assert success == len(GOLDEN_SCENARIOS), f"Only {success}/{len(GOLDEN_SCENARIOS)} scenarios yielded results."
    print(f"\nGolden Dataset Validation Complete: {success}/{len(GOLDEN_SCENARIOS)} PASSED.")
