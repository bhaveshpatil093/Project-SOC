"""
Migration Runner
================
Manages versioned Elasticsearch index schema migrations.

When using KibanaProxyClient (Kibana-only environment), all index management
operations are skipped gracefully. Migrations remain intact and will execute
automatically when a native Elasticsearch client is provided in the future.
"""

from __future__ import annotations

import importlib
import pkgutil
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

from app.ingestion.es_client_protocol import supports_index_management
from app.migrations import versions
from app.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class Migration:
    version: str
    description: str
    up: Callable
    down: Callable
    created_at: datetime


class MigrationRunner:
    MIGRATION_INDEX = "soc-migrations"

    async def initialize(self, es: Any) -> None:
        """Creates the migrations tracking index if the client supports it."""
        if not supports_index_management(es):
            logger.info(
                "migrations_index_skipped",
                reason="KibanaProxyClient does not support index management",
            )
            return

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
                            "description": {"type": "text"},
                        }
                    }
                },
            )
            logger.info("migrations_index_created")

    def _load_migrations(self) -> list[Migration]:
        migs: list[Migration] = []
        for _, module_name, _ in pkgutil.iter_modules(versions.__path__):
            mod = importlib.import_module(f"app.migrations.versions.{module_name}")
            if hasattr(mod, "up") and hasattr(mod, "down"):
                desc = getattr(mod, "__doc__", "") or module_name
                version = module_name.split("_")[0]
                migs.append(
                    Migration(
                        version=version,
                        description=desc.strip(),
                        up=mod.up,
                        down=mod.down,
                        created_at=datetime.now(timezone.utc),
                    )
                )
        return sorted(migs, key=lambda m: m.version)

    async def get_applied_versions(self, es: Any) -> list[str]:
        if not supports_index_management(es):
            return []
        try:
            resp = await es.search(
                index=self.MIGRATION_INDEX,
                body={"size": 1000, "query": {"match": {"status": "success"}}},
                sort="version:asc",
                ignore_unavailable=True,
            )
            hits = resp.get("hits", {}).get("hits", [])
            return [h["_source"]["version"] for h in hits]
        except Exception as e:
            logger.error(f"Failed to fetch applied versions: {e}")
            return []

    async def apply_pending(self, es: Any) -> dict[str, Any]:
        """
        Applies pending migrations. Returns a result dict.

        When KibanaProxyClient is in use, all migrations are skipped and the
        'skipped' key explains why. No data is lost — these are administrative
        index-management operations.
        """
        if not supports_index_management(es):
            logger.info(
                "migrations_skipped",
                reason="KibanaProxyClient does not support index management — "
                       "migrations will run automatically when a native Elasticsearch client is used.",
            )
            return {
                "applied": [],
                "errors": [],
                "skipped": "KibanaProxyClient does not support index management",
            }

        await self.initialize(es)
        all_migrations = self._load_migrations()
        applied = await self.get_applied_versions(es)

        pending = [m for m in all_migrations if m.version not in applied]
        results: dict[str, Any] = {"applied": [], "errors": []}

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
                        "applied_at": datetime.now(timezone.utc).isoformat(),
                    },
                )
                results["applied"].append(m.version)
            except Exception as e:
                logger.error(f"Migration {m.version} failed: {e}")
                results["errors"].append(f"{m.version}: {e}")
                try:
                    await es.index(
                        index=self.MIGRATION_INDEX,
                        id=m.version,
                        body={
                            "version": m.version,
                            "description": m.description,
                            "status": "failed",
                            "applied_at": datetime.now(timezone.utc).isoformat(),
                        },
                    )
                except Exception:
                    pass
                break  # Stop on first error

        return results

    async def rollback(self, es: Any, to_version: str) -> dict[str, Any]:
        if not supports_index_management(es):
            logger.warning("migrations_rollback_skipped", reason="KibanaProxyClient in use")
            return {"rolled_back": [], "errors": [], "skipped": "KibanaProxyClient does not support index management"}

        all_migrations = self._load_migrations()
        applied = await self.get_applied_versions(es)

        to_rollback = sorted(
            [m for m in all_migrations if m.version > to_version and m.version in applied],
            key=lambda m: m.version,
            reverse=True,
        )
        results: dict[str, Any] = {"rolled_back": [], "errors": []}

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

    async def status(self, es: Any) -> dict[str, Any]:
        if not supports_index_management(es):
            all_migrations = self._load_migrations()
            return {
                "applied": [],
                "pending": [m.version for m in all_migrations],
                "total_defined": len(all_migrations),
                "note": "KibanaProxyClient in use — migrations are not tracked",
            }

        await self.initialize(es)
        all_migrations = self._load_migrations()
        applied = await self.get_applied_versions(es)
        pending = [m.version for m in all_migrations if m.version not in applied]
        return {
            "applied": applied,
            "pending": pending,
            "total_defined": len(all_migrations),
        }
