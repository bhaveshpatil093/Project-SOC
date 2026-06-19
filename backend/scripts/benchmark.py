import os
import sys
import time
import asyncio
import logging

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.ingestion.es_client import get_es_client, close_es_client
from app.ingestion.log_fetcher import fetch_all_sources
from app.ingestion.normalizer import normalize_batch
from app.features.feature_merger import run_feature_pipeline
from app.models.model_manager import get_model_manager
from app.slm.agent import SOCAgent

# Silence unnecessary logs during benchmark
logging.getLogger("app").setLevel(logging.ERROR)

async def run_benchmark():
    print("=" * 60)
    print(" SOC Pipeline Performance Benchmark ".center(60, "="))
    print("=" * 60)
    
    es = await get_es_client()
    
    # Check ES connection
    if not await es.ping():
        print("Error: Could not connect to Elasticsearch.")
        return

    # 1. Ingestion Cycle (Fetch + Normalize)
    print("\n[1/4] Measuring Ingestion Cycle...")
    start_time = time.time()
    
    raw_results = await fetch_all_sources(es, since_minutes=60)  # Fetch last hour for load
    total_fetched = sum(len(docs) for docs in raw_results.values())
    
    for log_type, raw_docs in raw_results.items():
        _ = normalize_batch(raw_docs, log_type)
        
    ingestion_time = time.time() - start_time
    print(f"  - Logs Fetched:      {total_fetched}")
    print(f"  - Time Elapsed:      {ingestion_time:.4f} seconds")
    print(f"  - Throughput:        {total_fetched / max(0.001, ingestion_time):.1f} logs/sec")

    # 2. Feature Pipeline
    print("\n[2/4] Measuring Feature Pipeline...")
    start_time = time.time()
    feature_df, normalized_df = await run_feature_pipeline(es, since_minutes=60)
    feature_time = time.time() - start_time
    
    entities = len(feature_df)
    print(f"  - Entities Extracted: {entities}")
    print(f"  - Time Elapsed:       {feature_time:.4f} seconds")
    print(f"  - Throughput:         {entities / max(0.001, feature_time):.1f} entities/sec")

    # 3. ML Scoring
    print("\n[3/4] Measuring ML Scoring (Batched)...")
    mm = get_model_manager()
    await mm.initialize()
    
    start_time = time.time()
    results = await mm.score_all_entities(feature_df, normalized_df)
    scoring_time = time.time() - start_time
    
    scored = len(results)
    print(f"  - Entities Scored:    {scored}")
    print(f"  - Time Elapsed:       {scoring_time:.4f} seconds")
    print(f"  - Average per Entity: {(scoring_time / max(1, scored)) * 1000:.2f} ms")

    # 4. SLM Inference
    print("\n[4/4] Measuring SLM Inference...")
    agent = SOCAgent()
    
    if scored > 0:
        # Just use the highest scored entity as a mock alert
        top_res = max(results, key=lambda x: x.threat_score)
        mock_alert = {
            "entity_key": top_res.entity_key,
            "threat_score": top_res.threat_score,
            "threat_level": top_res.threat_level,
            "mitre_tactics": top_res.mitre_tactics,
            "triggered_rules": top_res.triggered_rules,
            "network_anomaly_score": top_res.network_anomaly_score,
            "process_anomaly_score": top_res.process_anomaly_score
        }
        
        start_time = time.time()
        _ = await agent.investigate(
            alert=mock_alert,
            question="Summarize this alert and recommend immediate actions."
        )
        slm_time = time.time() - start_time
        print(f"  - Inference Time:     {slm_time:.4f} seconds")
    else:
        slm_time = 0
        print("  - Skipped: No entities to score.")

    # Summary
    print("\n" + "=" * 60)
    print(" Benchmark Summary ".center(60, "="))
    print("=" * 60)
    full_cycle_time = ingestion_time + feature_time + scoring_time
    print(f"Ingestion (Fetch+Norm):   {ingestion_time:8.4f}s")
    print(f"Feature Pipeline:         {feature_time:8.4f}s")
    print(f"ML Batched Scoring:       {scoring_time:8.4f}s")
    print("-" * 60)
    print(f"Total Pipeline Cycle:     {full_cycle_time:8.4f}s")
    print(f"SLM Ad-hoc Query:         {slm_time:8.4f}s")
    print("=" * 60)
    
    await close_es_client()

if __name__ == "__main__":
    asyncio.run(run_benchmark())
