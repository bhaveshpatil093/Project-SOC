import importlib
import logging
import pkgutil
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Any

from app.ingestion.es_client import INDEX_NAMES
from app.migrations import versions

logger = logging.getLogger(__name__)

@dataclass
class Migration:
    version: str
    description: str
    up: Callable
    down: Callable
    created_at: datetime

class MigrationRunner:
    MIGRATION_INDEX = "soc-migrations"

    async def initialize(self, es):
        exists = await es.indices.exists(index=self.MIGRATION_INDEX)
        if not exists:
            await es.indices.create(
                index=self.MIGRATION_INDEX,
                body={
                    "mappings": {
                        "properties": {
                            "version": {"type": "keyword"},
                            "applied_at": {"type": "date"},
                            "status": {"type": "keyword"},
                            "description": {"type": "text"}
                        }
                    }
                }
            )
            logger.info("Created migrations tracking index.")

    def _load_migrations(self) -> list[Migration]:
        migs = []
        for _, module_name, _ in pkgutil.iter_modules(versions.__path__):
            mod = importlib.import_module(f"app.migrations.versions.{module_name}")
            if hasattr(mod, "up") and hasattr(mod, "down"):
                desc = getattr(mod, "__doc__", "") or module_name
                version = module_name.split("_")[0]
                migs.append(Migration(
                    version=version,
                    description=desc.strip(),
                    up=mod.up,
                    down=mod.down,
                    created_at=datetime.now(timezone.utc)
                ))
        return sorted(migs, key=lambda m: m.version)

    async def get_applied_versions(self, es) -> list[str]:
        try:
            resp = await es.search(
                index=self.MIGRATION_INDEX,
                body={"size": 1000, "query": {"match": {"status": "success"}}},
                sort="version:asc",
                ignore_unavailable=True
            )
            hits = resp.get("hits", {}).get("hits", [])
            return [h["_source"]["version"] for h in hits]
        except Exception as e:
            logger.error(f"Failed to fetch applied versions: {e}")
            return []

    async def apply_pending(self, es) -> dict[str, Any]:
        await self.initialize(es)
        all_migrations = self._load_migrations()
        applied = await self.get_applied_versions(es)
        
        pending = [m for m in all_migrations if m.version not in applied]
        results = {"applied": [], "errors": []}
        
        for m in pending:
            logger.info(f"Applying migration {m.version}: {m.description}")
            try:
                await m.up(es)
                await es.index(
                    index=self.MIGRATION_INDEX,
                    id=m.version,
                    body={
                        "version": m.version,
                        "description": m.description,
                        "status": "success",
                        "applied_at": datetime.now(timezone.utc).isoformat()
                    }
                )
                results["applied"].append(m.version)
            except Exception as e:
                logger.error(f"Migration {m.version} failed: {e}")
                results["errors"].append(f"{m.version}: {e}")
                await es.index(
                    index=self.MIGRATION_INDEX,
                    id=m.version,
                    body={
                        "version": m.version,
                        "description": m.description,
                        "status": "failed",
                        "applied_at": datetime.now(timezone.utc).isoformat()
                    }
                )
                break  # Stop on first error
                
        return results

    async def rollback(self, es, to_version: str) -> dict[str, Any]:
        all_migrations = self._load_migrations()
        applied = await self.get_applied_versions(es)
        
        to_rollback = sorted([m for m in all_migrations if m.version > to_version and m.version in applied], key=lambda m: m.version, reverse=True)
        results = {"rolled_back": [], "errors": []}
        
        for m in to_rollback:
            logger.info(f"Rolling back migration {m.version}: {m.description}")
            try:
                await m.down(es)
                await es.delete(index=self.MIGRATION_INDEX, id=m.version, ignore=[404])
                results["rolled_back"].append(m.version)
            except Exception as e:
                logger.error(f"Rollback {m.version} failed: {e}")
                results["errors"].append(f"{m.version}: {e}")
                break
                
        return results

    async def status(self, es) -> dict[str, Any]:
        await self.initialize(es)
        all_migrations = self._load_migrations()
        applied = await self.get_applied_versions(es)
        pending = [m.version for m in all_migrations if m.version not in applied]
        return {
            "applied": applied,
            "pending": pending,
            "total_defined": len(all_migrations)
        }
