import asyncio
import argparse
import os
import sqlite3
import sys
import time
from datetime import datetime, timedelta

from app.ingestion.es_client import get_es_client, INDEX_NAMES
from app.config import settings
from app.slm.conversation_manager import get_conversation_manager
from app.slm.rag_pipeline import get_rag_pipeline
from app.cache.cache_manager import cache
from app.logging_config import get_logger

logger = get_logger(__name__)

class CleanupManager:
    async def cleanup_test_indices(self, es, dry_run: bool = True) -> dict:
        result = {"found": 0, "deleted": 0}
        try:
            indices = await es.cat.indices(format="json")
            for idx in indices:
                name = idx.get("index", "")
                if name.startswith("test-soc-") or name.endswith("-test"):
                    result["found"] += 1
                    if not dry_run:
                        await es.indices.delete(index=name, ignore_unavailable=True)
                        result["deleted"] += 1
        except Exception as e:
            logger.error(f"Error cleaning test indices: {e}")
        return result

    async def cleanup_old_conversations(self, dry_run: bool = True) -> dict:
        cm = get_conversation_manager()
        # count before
        count_before = len(cm._store)
        result = {"found": 0, "deleted": 0}
        
        # we can't easily dry-run without duplicating logic, but we can check lengths
        now = datetime.now()
        expired_count = sum(1 for c in cm._store.values() if now - c.last_updated > timedelta(hours=cm.ttl_hours))
        
        result["found"] = expired_count
        if not dry_run:
            cm.cleanup_expired()
            count_after = len(cm._store)
            result["deleted"] = count_before - count_after
        return result

    async def cleanup_orphaned_model_files(self, dry_run: bool = True) -> dict:
        result = {"found": 0, "deleted": 0}
        # To do this safely, we need MLflow runs
        from mlflow.tracking import MlflowClient
        import mlflow
        mlflow.set_tracking_uri(settings.MLFLOW_TRACKING_URI)
        client = MlflowClient()
        
        active_artifacts = set()
        try:
            exps = client.search_experiments()
            for exp in exps:
                runs = client.search_runs(exp.experiment_id)
                for run in runs:
                    artifacts = client.list_artifacts(run.info.run_id)
                    for a in artifacts:
                        active_artifacts.add(a.path)
        except Exception as e:
            logger.error(f"Failed to query mlflow runs: {e}")
            return result
        
        model_dir = settings.MODEL_DIR
        if not os.path.exists(model_dir):
            return result
            
        for file in os.listdir(model_dir):
            if file.endswith(".pkl") or file.endswith(".pt") or file.endswith(".joblib"):
                # if not tracked by MLflow or main paths
                if file not in ["isolation_forest.pkl", "autoencoder.pt", "lstm_model.pt"]:
                    if file not in active_artifacts:
                        result["found"] += 1
                        if not dry_run:
                            os.remove(os.path.join(model_dir, file))
                            result["deleted"] += 1
        return result

    async def cleanup_stale_chromadb_entries(self, es, dry_run: bool = True) -> dict:
        result = {"found": 0, "deleted": 0}
        rag = get_rag_pipeline()
        if not rag.collection:
            return result
            
        try:
            chroma_data = rag.collection.get(include=["metadatas"])
            ids_to_remove = []
            
            if chroma_data and "ids" in chroma_data and "metadatas" in chroma_data:
                for idx, doc_id in enumerate(chroma_data["ids"]):
                    # check if alert exists in ES
                    meta = chroma_data["metadatas"][idx]
                    alert_id = meta.get("alert_id")
                    if alert_id:
                        exists = await es.exists(index=INDEX_NAMES["alerts_processed"], id=alert_id)
                        if not exists:
                            ids_to_remove.append(doc_id)
                            
            result["found"] = len(ids_to_remove)
            if not dry_run and ids_to_remove:
                rag.collection.delete(ids=ids_to_remove)
                result["deleted"] = len(ids_to_remove)
        except Exception as e:
            logger.error(f"Error cleaning chromadb: {e}")
            
        return result

    async def cleanup_expired_cache_entries(self, dry_run: bool = True) -> dict:
        result = {"found": 0, "deleted": 0}
        # In-memory cache manager has clear_expired() which removes expired keys
        now = time.time()
        expired = [k for k, v in cache._store.items() if now > v.expires_at]
        result["found"] = len(expired)
        
        if not dry_run:
            await cache.clear_expired()
            result["deleted"] = len(expired)
        return result

    async def cleanup_old_audit_logs(self, es, retain_days: int = 90, dry_run: bool = True) -> dict:
        result = {"found": 0, "deleted": 0}
        try:
            query = {
                "query": {
                    "range": {
                        "timestamp": {
                            "lt": f"now-{retain_days}d"
                        }
                    }
                }
            }
            count_res = await es.count(index="soc-audit-logs", body=query, ignore_unavailable=True)
            result["found"] = count_res.get("count", 0)
            
            if not dry_run and result["found"] > 0:
                del_res = await es.delete_by_query(index="soc-audit-logs", body=query, ignore_unavailable=True)
                result["deleted"] = del_res.get("deleted", 0)
        except Exception as e:
            logger.error(f"Error cleaning audit logs: {e}")
        return result

    async def cleanup_old_score_history(self, es, retain_days: int = 30, dry_run: bool = True) -> dict:
        result = {"found": 0, "deleted": 0}
        try:
            query = {
                "query": {
                    "range": {
                        "timestamp": {
                            "lt": f"now-{retain_days}d"
                        }
                    }
                }
            }
            count_res = await es.count(index="soc-score-history", body=query, ignore_unavailable=True)
            result["found"] = count_res.get("count", 0)
            
            if not dry_run and result["found"] > 0:
                del_res = await es.delete_by_query(index="soc-score-history", body=query, ignore_unavailable=True)
                result["deleted"] = del_res.get("deleted", 0)
        except Exception as e:
            logger.error(f"Error cleaning score history: {e}")
        return result

    async def cleanup_resolved_incidents(self, es, retain_days: int = 180, dry_run: bool = True) -> dict:
        result = {"found": 0, "deleted": 0}
        try:
            query = {
                "query": {
                    "bool": {
                        "must": [
                            {"term": {"status": "resolved"}},
                            {"range": {"updated_at": {"lt": f"now-{retain_days}d"}}}
                        ],
                        "must_not": [
                            {"term": {"status": "archived"}}
                        ]
                    }
                }
            }
            count_res = await es.count(index="soc-incidents", body=query, ignore_unavailable=True)
            result["found"] = count_res.get("count", 0)
            
            if not dry_run and result["found"] > 0:
                update_script = {
                    "script": {
                        "source": "ctx._source.status = 'archived'",
                        "lang": "painless"
                    },
                    "query": query["query"]
                }
                update_res = await es.update_by_query(index="soc-incidents", body=update_script, ignore_unavailable=True)
                result["deleted"] = update_res.get("updated", 0)
        except Exception as e:
            logger.error(f"Error archiving incidents: {e}")
        return result

    async def vacuum_mlflow_db(self, dry_run: bool = True) -> dict:
        result = {"found": 1, "deleted": 0}
        if not dry_run:
            db_path = settings.MLFLOW_DB_PATH.replace("sqlite:///", "")
            if os.path.exists(db_path):
                try:
                    conn = sqlite3.connect(db_path)
                    conn.execute("VACUUM")
                    conn.close()
                    result["deleted"] = 1
                except Exception as e:
                    logger.error(f"Error vacuuming MLflow DB: {e}")
        return result

    async def run_full_cleanup(self, dry_run: bool = True, execute_only: list = None) -> dict:
        es = await get_es_client()
        report = {}
        
        ops = {
            "test_indices": lambda: self.cleanup_test_indices(es, dry_run),
            "conversations": lambda: self.cleanup_old_conversations(dry_run),
            "model_files": lambda: self.cleanup_orphaned_model_files(dry_run),
            "chromadb_entries": lambda: self.cleanup_stale_chromadb_entries(es, dry_run),
            "cache": lambda: self.cleanup_expired_cache_entries(dry_run),
            "audit_logs": lambda: self.cleanup_old_audit_logs(es, dry_run=dry_run),
            "score_history": lambda: self.cleanup_old_score_history(es, dry_run=dry_run),
            "resolved_incidents": lambda: self.cleanup_resolved_incidents(es, dry_run=dry_run),
            "mlflow_vacuum": lambda: self.vacuum_mlflow_db(dry_run)
        }
        
        for name, func in ops.items():
            if execute_only and name not in execute_only:
                continue
            try:
                res = await func()
                report[name] = res
            except Exception as e:
                logger.error(f"Operation {name} failed: {e}")
                report[name] = {"found": 0, "deleted": 0, "error": str(e)}
                
        return report

async def main():
    parser = argparse.ArgumentParser(description="ISRO SOC Platform Cleanup Utility")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Report only, no changes")
    parser.add_argument("--execute", action="store_true", help="Actually perform cleanup")
    parser.add_argument("--only", type=str, help="Run single cleanup operation (e.g., test_indices)")
    parser.add_argument("--confirm", action="store_true", help="Skip confirmation prompt")
    
    args = parser.parse_args()
    
    # Check if user specified --execute
    if args.execute:
        args.dry_run = False
        
    if not args.dry_run and not args.confirm and not args.only:
        confirm = input("Are you sure you want to run full cleanup with destructive changes? (y/N): ")
        if confirm.lower() != 'y':
            print("Aborting.")
            sys.exit(0)
            
    manager = CleanupManager()
    
    execute_only = None
    if args.only:
        execute_only = [args.only]
        
    report = await manager.run_full_cleanup(dry_run=args.dry_run, execute_only=execute_only)
    
    print("\nISRO SOC Platform — Cleanup Report " + ("(DRY RUN)" if args.dry_run else "(EXECUTED)"))
    print("=" * 45)
    
    # Map operation to descriptive label
    labels = {
        "test_indices": "Test indices found:",
        "conversations": "Expired conversations:",
        "model_files": "Orphaned model files:",
        "chromadb_entries": "Stale ChromaDB entries:",
        "cache": "Expired cache entries:",
        "audit_logs": "Old audit logs (>90d):",
        "score_history": "Old score history (>30d):",
        "resolved_incidents": "Resolved incidents (>180d):",
        "mlflow_vacuum": "MLflow DB Vacuum:"
    }
    
    for op, stats in report.items():
        found = stats.get("found", 0)
        deleted = stats.get("deleted", 0)
        label = labels.get(op, f"{op}:")
        
        if op == "mlflow_vacuum":
            action = "would vacuum" if args.dry_run else "vacuumed"
            print(f"✓ {label:<28} {found:<4} ({action})")
        elif op == "resolved_incidents":
            action = "would archive" if args.dry_run else "archived"
            print(f"✓ {label:<28} {found:<4} ({action})")
        elif op == "model_files":
            action = "manual review needed" if args.dry_run else "deleted"
            print(f"✓ {label:<28} {found:<4} ({action})")
        elif op == "score_history":
            action = "would trim" if args.dry_run else "trimmed"
            print(f"✓ {label:<28} {found:<4} ({action})")
        else:
            action = "would delete" if args.dry_run else "deleted"
            print(f"✓ {label:<28} {found:<4} ({action})")
            
    if args.dry_run:
        print("\nRun with --execute to apply these changes.")

if __name__ == "__main__":
    # Remove PYTHONPATH from args if run with python -m etc.
    asyncio.run(main())
