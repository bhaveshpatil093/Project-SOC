import os
import shutil
from datetime import datetime

from app.logging_config import get_logger
logger = get_logger(__name__)

class BackupManager:
    def __init__(self, backup_dir: str = "/tmp/soc_backups"):
        self.backup_dir = backup_dir
        self.db_path = "backend/data/soc.db"
        self.faiss_dir = "backend/data/faiss_index"
        
    async def create_local_backup(self, snapshot_name: str = None) -> dict:
        """Create a backup of local SQLite DB and FAISS index."""
        if not snapshot_name:
            snapshot_name = f"soc_backup_{datetime.now():%Y%m%d_%H%M%S}"
            
        try:
            target_dir = os.path.join(self.backup_dir, snapshot_name)
            os.makedirs(target_dir, exist_ok=True)
            
            logger.info("Initiating local backup", snapshot=snapshot_name)
            start_time = datetime.now()
            
            # Backup DB
            if os.path.exists(self.db_path):
                shutil.copy2(self.db_path, os.path.join(target_dir, "soc.db"))
                
            # Backup FAISS
            if os.path.exists(self.faiss_dir):
                shutil.copytree(self.faiss_dir, os.path.join(target_dir, "faiss_index"), dirs_exist_ok=True)
                
            duration = (datetime.now() - start_time).total_seconds() * 1000
            
            return {
                "snapshot_name": snapshot_name,
                "start_time": start_time.isoformat(),
                "duration_ms": duration,
                "state": "SUCCESS"
            }
        except Exception as e:
            logger.error("Failed to create backup", error=str(e))
            raise e

    async def list_snapshots(self) -> list[dict]:
        """List all backups in the local directory."""
        if not os.path.exists(self.backup_dir):
            return []
            
        snapshots = []
        for d in os.listdir(self.backup_dir):
            p = os.path.join(self.backup_dir, d)
            if os.path.isdir(p):
                snapshots.append({
                    "snapshot": d,
                    "uuid": d,
                    "version": "1.0",
                    "indices": ["soc.db", "faiss_index"],
                    "state": "SUCCESS",
                    "start_time": datetime.fromtimestamp(os.path.getmtime(p)).isoformat() + "Z"
                })
        return snapshots
