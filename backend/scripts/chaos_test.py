import argparse
import asyncio
import logging
import random
import time
import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("chaos_test")

class ChaosInjector:
    def __init__(self, target_url: str):
        self.target_url = target_url.rstrip("/")
        self.client = httpx.AsyncClient(base_url=self.target_url, timeout=10.0)

    async def check_health(self) -> bool:
        """Check if the system is currently healthy."""
        try:
            resp = await self.client.get("/health/ready")
            return resp.status_code == 200
        except Exception:
            return False

    async def inject_failure(self):
        """Inject a random failure."""
        failures = [
            self.spike_cpu,
            self.simulate_network_delay,
            self.simulate_es_disconnect
        ]
        chosen = random.choice(failures)
        logger.warning(f"Injecting failure: {chosen.__name__}")
        await chosen()

    async def spike_cpu(self):
        """Simulate a CPU spike by hitting an expensive endpoint concurrently."""
        # For example, asking the SLM multiple complex queries simultaneously
        async def hit():
            try:
                await self.client.post("/api/slm/chat", json={"message": "Analyze all logs for the last month"}, timeout=2.0)
            except Exception:
                pass
        
        await asyncio.gather(*(hit() for _ in range(20)))

    async def simulate_network_delay(self):
        """Simulate network delay by holding connections open."""
        pass # In a real test, might use toxiproxy or iptables
        logger.info("Simulating network delay... (Placeholder)")
        await asyncio.sleep(5)

    async def simulate_es_disconnect(self):
        """Simulate Elasticsearch disconnection."""
        pass # In a real test, might kill ES container or drop port
        logger.info("Simulating ES disconnect... (Placeholder)")
        await asyncio.sleep(5)

    async def wait_for_recovery(self, timeout_sec: int = 30) -> bool:
        """Wait for the system to recover."""
        start = time.time()
        while time.time() - start < timeout_sec:
            if await self.check_health():
                return True
            await asyncio.sleep(2)
        return False

async def run_chaos_test(target: str, duration: int):
    logger.info(f"Starting chaos test against {target} for {duration} seconds.")
    injector = ChaosInjector(target)
    
    start_time = time.time()
    
    # Initial health check
    if not await injector.check_health():
        logger.error("Target is not healthy. Aborting.")
        return
        
    logger.info("Target is healthy. Commencing chaos...")
    
    while time.time() - start_time < duration:
        await injector.inject_failure()
        
        logger.info("Waiting for recovery...")
        recovered = await injector.wait_for_recovery(timeout_sec=60)
        
        if recovered:
            logger.info("System recovered successfully.")
        else:
            logger.error("System FAILED to recover within SLA!")
            # Fail fast on non-recovery
            return
            
        await asyncio.sleep(random.randint(5, 15))
        
    logger.info("Chaos test completed successfully.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run chaos engineering tests.")
    parser.add_argument("--target", type=str, required=True, help="Target URL (e.g., http://localhost:8000)")
    parser.add_argument("--duration", type=int, default=300, help="Duration in seconds")
    args = parser.parse_args()
    
    asyncio.run(run_chaos_test(args.target, args.duration))
