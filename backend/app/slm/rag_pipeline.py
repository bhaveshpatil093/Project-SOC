import os
import time
import logging
import asyncio
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings

logger = logging.getLogger(__name__)

class RAGPipeline:
    def __init__(self, persist_dir: str = "./data/chroma_db"):
        self.persist_dir = persist_dir
        self.model = None
        self.client = None
        self.collection = None

    async def initialize(self):
        logger.info("Initializing RAG Pipeline with all-MiniLM-L6-v2...")
        
        loop = asyncio.get_event_loop()
        def _load_model():
            return SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
            
        self.model = await loop.run_in_executor(None, _load_model)
        
        os.makedirs(self.persist_dir, exist_ok=True)
        self.client = chromadb.PersistentClient(path=self.persist_dir, settings=Settings(anonymized_telemetry=False))
        self.collection = self.client.get_or_create_collection("soc_alerts")
        
        n_docs = self.collection.count()
        logger.info(f"ChromaDB initialized: {n_docs} alerts already indexed in collection 'soc_alerts'")

    def clear_index(self):
        logger.warning(f"CAUTION: Deleting entire ChromaDB collection 'soc_alerts' at {self.persist_dir}")
        try:
            self.client.delete_collection("soc_alerts")
        except:
            pass
        self.collection = self.client.get_or_create_collection("soc_alerts")

    async def get_index_stats(self) -> dict:
        n_docs = self.collection.count() if self.collection else 0
        return {
            "total_indexed": n_docs,
            "collection_name": "soc_alerts",
            "persist_dir": self.persist_dir,
            "embedding_model": "all-MiniLM-L6-v2"
        }

    async def retrieve_by_entity(self, entity_key: str, n: int = 10) -> list[dict]:
        if not self.collection:
            return []
        
        results = self.collection.get(
            where={"entity_key": entity_key},
            limit=n
        )
        
        out = []
        if results and results.get("documents"):
            for i in range(len(results["documents"])):
                out.append({
                    "document": results["documents"][i],
                    "metadata": results["metadatas"][i]
                })
        return out

    async def retrieve_by_tactic(self, tactic: str, n: int = 5) -> list[dict]:
        if not self.collection:
            return []
            
        results = self.collection.get(
            where={"mitre_tactics": {"$contains": tactic}},
            limit=n
        )
        
        out = []
        if results and results.get("documents"):
            for i in range(len(results["documents"])):
                out.append({
                    "document": results["documents"][i],
                    "metadata": results["metadatas"][i]
                })
        return out

    def embed_text(self, text: str) -> list[float]:
        if self.model is None:
            raise RuntimeError("RAG Pipeline not yet initialized")
        return self.model.encode(text).tolist()

    async def index_alert(self, alert: dict):
        if self.collection is None:
            return
            
        host = alert.get("entity_key", "unknown").split("|")[0]
        user = alert.get("entity_key", "unknown").split("|")[-1]
        level = alert.get("threat_level", "low")
        score = alert.get("threat_score", 0) * 100
        tactics = ", ".join(alert.get("mitre_tactics", []))
        explanation = alert.get("human_explanation", "No explanation provided by XAI.")
        rules = alert.get("top_rule", "None")

        doc_text = f"Alert on {host} for {user}. Threat: {level} ({score:.0f}). MITRE: {tactics}. Explanation: {explanation}. Rules: {rules}."
        doc_id = alert.get("id") or alert.get("_id", str(hash(doc_text)))
        
        embedding = await asyncio.get_event_loop().run_in_executor(None, self.embed_text, doc_text)
        
        self.collection.upsert(
            ids=[doc_id],
            embeddings=[embedding],
            documents=[doc_text],
            metadatas=[{
                "alert_id": doc_id,
                "entity_key": alert.get("entity_key", ""),
                "threat_level": level,
                "timestamp": alert.get("timestamp", ""),
                "mitre_tactics": tactics,
                "triggered_rules": rules
            }]
        )

    async def index_batch(self, alerts: list[dict]):
        if self.collection is None or not alerts:
            return
            
        ids = []
        texts = []
        metas = []
        
        for alert in alerts:
            host = alert.get("entity_key", "unknown").split("|")[0]
            user = alert.get("entity_key", "unknown").split("|")[-1]
            level = alert.get("threat_level", "low")
            score = alert.get("threat_score", 0) * 100
            tactics = ", ".join(alert.get("mitre_tactics", []))
            explanation = alert.get("human_explanation", "No explanation provided by XAI.")
            rules = alert.get("top_rule", "None")

            doc_text = f"Alert on {host} for {user}. Threat: {level} ({score:.0f}). MITRE: {tactics}. Explanation: {explanation}. Rules: {rules}."
            doc_id = alert.get("id") or alert.get("_id", str(hash(doc_text)))
            
            ids.append(doc_id)
            texts.append(doc_text)
            metas.append({
                "alert_id": doc_id,
                "entity_key": alert.get("entity_key", ""),
                "threat_level": level,
                "timestamp": alert.get("timestamp", ""),
                "mitre_tactics": tactics,
                "triggered_rules": rules
            })
            
        embeddings = await asyncio.get_event_loop().run_in_executor(None, lambda: self.model.encode(texts).tolist())
        self.collection.upsert(ids=ids, embeddings=embeddings, documents=texts, metadatas=metas)

    async def reindex_from_elasticsearch(self, es, since_days: int = 30) -> dict:
        from app.ingestion.es_client import INDEX_NAMES
        
        start_t = time.time()
        
        query = {
            "query": {
                "bool": {
                    "must": [
                        {"range": {"timestamp": {"gte": f"now-{since_days}d"}}},
                        {"range": {"threat_score": {"gt": 0.3}}}
                    ]
                }
            },
            "size": 10000,
            "sort": [{"timestamp": {"order": "asc"}}]
        }
        
        try:
            resp = await es.search(index=INDEX_NAMES["alerts_processed"], body=query)
            hits = resp.get("hits", {}).get("hits", [])
        except Exception as e:
            logger.error(f"Error fetching alerts for reindexing: {e}")
            return {"indexed": 0, "skipped": 0, "errors": 1, "time_seconds": time.time() - start_t}
            
        total_indexed = 0
        skipped = 0
        
        chunk_size = 100
        for i in range(0, len(hits), chunk_size):
            chunk = hits[i:i+chunk_size]
            alerts = [{"id": h["_id"], **h["_source"]} for h in chunk]
            
            if alerts:
                await self.index_batch(alerts)
                total_indexed += len(alerts)
                
        return {
            "indexed": total_indexed,
            "skipped": skipped,
            "errors": 0,
            "time_seconds": round(time.time() - start_t, 2)
        }

    async def retrieve_similar(self, query: str, n_results: int = 5, filter_entity: str = None) -> list[dict]:
        if self.collection is None:
            return []
            
        query_emb = await asyncio.get_event_loop().run_in_executor(None, self.embed_text, query)
        
        where_clause = None
        if filter_entity:
            where_clause = {"entity_key": filter_entity}
            
        results = self.collection.query(
            query_embeddings=[query_emb],
            n_results=n_results,
            where=where_clause
        )
        
        out = []
        if results and results.get("documents") and len(results["documents"]) > 0:
            docs = results["documents"][0]
            metas = results["metadatas"][0]
            dists = results["distances"][0]
            
            for d, m, dist in zip(docs, metas, dists):
                out.append({"document": d, "metadata": m, "distance": dist})
                
        return out

    def build_rag_context(self, retrieved: list[dict], current_alert: dict) -> str:
        ctx_parts = ["CURRENT ALERT CONTEXT:"]
        
        score = current_alert.get('threat_score', 0) * 100
        ctx_parts.append(f"Entity: {current_alert.get('entity_key')}")
        ctx_parts.append(f"Level: {current_alert.get('threat_level')} ({score:.0f})")
        ctx_parts.append(f"Reason: {current_alert.get('human_explanation')}")
        
        if retrieved:
            ctx_parts.append("\nHISTORICAL RELATED ALERTS:")
            for r in retrieved:
                doc = r['document']
                if len("\n".join(ctx_parts)) + len(doc) > 1800:
                    break
                ctx_parts.append(f"- {doc}")
                
        return "\n".join(ctx_parts)

_rag_pipeline = RAGPipeline()

def get_rag_pipeline() -> RAGPipeline:
    return _rag_pipeline
