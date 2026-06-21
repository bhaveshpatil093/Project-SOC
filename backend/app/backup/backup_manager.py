import asyncio
import logging
from datetime import datetime
from elasticsearch import AsyncElasticsearch

logger = logging.getLogger(__name__)

class BackupManager:
    def __init__(self, es: AsyncElasticsearch, backup_dir: str = "/tmp/soc_backups"):
        self.es = es
        self.repo_name = "soc_backup"
        self.backup_dir = backup_dir
        
    async def create_snapshot_repository(self):
        """Register a filesystem snapshot repository with ES."""
        try:
            await self.es.snapshot.create_repository(
                name=self.repo_name,
                body={
                    "type": "fs",
                    "settings": {
                        "location": self.backup_dir,
                        "compress": True
                    }
                },
                verify=False
            )
            logger.info("Snapshot repository registered", repo=self.repo_name, location=self.backup_dir)
        except Exception as e:
            logger.error("Failed to register snapshot repository", error=str(e))

    async def create_snapshot(self, snapshot_name: str = None) -> dict:
        """Snapshot all soc-* indices and wait for completion."""
        if not snapshot_name:
            snapshot_name = f"soc_backup_{datetime.now():%Y%m%d_%H%M%S}"
            
        try:
            await self.create_snapshot_repository()
            
            logger.info("Initiating snapshot", snapshot=snapshot_name)
            resp = await self.es.snapshot.create(
                repository=self.repo_name,
                snapshot=snapshot_name,
                wait_for_completion=True,
                body={
                    "indices": "soc-*",
                    "ignore_unavailable": True,
                    "include_global_state": False
                }
            )
            
            snap_info = resp.get("snapshot", {})
            return {
                "snapshot_name": snapshot_name,
                "indices": snap_info.get("indices", []),
                "start_time": snap_info.get("start_time_in_millis"),
                "duration_ms": snap_info.get("duration_in_millis"),
                "state": snap_info.get("state")
            }
        except Exception as e:
            logger.error("Failed to create snapshot", error=str(e))
            raise e

    async def list_snapshots(self) -> list[dict]:
        """List all snapshots sorted by start_time descending."""
        try:
            await self.create_snapshot_repository()
            resp = await self.es.snapshot.get(repository=self.repo_name, snapshot="_all", ignore_unavailable=True)
            snapshots = resp.get("snapshots", [])
            
            sorted_snaps = sorted(
                snapshots,
                key=lambda x: x.get("start_time_in_millis", 0),
                reverse=True
            )
            
            return [{
                "snapshot_name": s["snapshot"],
                "state": s["state"],
                "indices": s.get("indices", []),
                "start_time": s.get("start_time_in_millis"),
                "end_time": s.get("end_time_in_millis"),
                "duration_ms": s.get("duration_in_millis")
            } for s in sorted_snaps]
            
        except Exception as e:
            logger.error("Failed to list snapshots", error=str(e))
            return []

    async def restore_snapshot(self, snapshot_name: str, target_indices: list[str] = None) -> dict:
        """Restore indices from a snapshot, closing them first and reopening them after."""
        indices_str = ",".join(target_indices) if target_indices else "soc-*"
        
        try:
            logger.info("Restoring snapshot", snapshot=snapshot_name, indices=indices_str)
            
            await self.es.indices.close(index=indices_str, ignore_unavailable=True)
            
            resp = await self.es.snapshot.restore(
                repository=self.repo_name,
                snapshot=snapshot_name,
                wait_for_completion=True,
                body={
                    "indices": indices_str,
                    "ignore_unavailable": True,
                    "include_global_state": False
                }
            )
            
            await self.es.indices.open(index=indices_str, ignore_unavailable=True)
            
            return {
                "snapshot_name": snapshot_name,
                "status": "success",
                "details": resp
            }
        except Exception as e:
            logger.error("Restore failed", snapshot=snapshot_name, error=str(e))
            await self.es.indices.open(index=indices_str, ignore_unavailable=True)
            raise e

    async def delete_old_snapshots(self, keep_last_n: int = 7):
        """Delete old snapshots keeping only the last N."""
        snapshots = await self.list_snapshots()
        if len(snapshots) <= keep_last_n:
            return
            
        to_delete = snapshots[keep_last_n:]
        for s in to_delete:
            snap_name = s["snapshot_name"]
            try:
                logger.info("Deleting old snapshot", snapshot=snap_name)
                await self.es.snapshot.delete(repository=self.repo_name, snapshot=snap_name)
            except Exception as e:
                logger.warning("Failed to delete snapshot", snapshot=snap_name, error=str(e))

    async def get_snapshot_size(self, snapshot_name: str) -> int:
        """Retrieve total byte size of a snapshot."""
        try:
            resp = await self.es.snapshot.status(repository=self.repo_name, snapshot=snapshot_name)
            snaps = resp.get("snapshots", [])
            if not snaps:
                return 0
            
            total_size = snaps[0].get("stats", {}).get("total", {}).get("size_in_bytes", 0)
            return total_size
        except Exception as e:
            logger.warning("Failed to get snapshot size", error=str(e))
            return 0
            
    def format_backup_report(self, snapshot: dict) -> str:
        name = snapshot.get("snapshot_name")
        state = snapshot.get("state")
        duration = snapshot.get("duration_ms", 0) / 1000.0
        return f"Backup {name} completed in {duration}s with status {state}."
