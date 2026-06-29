import asyncio
import json
import os
import time

from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings

from app.logging_config import get_logger

logger = get_logger(__name__)

class RAGPipeline:
    def __init__(self, persist_dir: str = "./data/faiss_index"):
        self.persist_dir = persist_dir
        self.embeddings = None
        self.faiss_store = None
        self.retriever = None

    async def initialize(self):
        logger.info("rag_pipeline_initializing", model="all-MiniLM-L6-v2")
        
        loop = asyncio.get_event_loop()
        def _init_embeddings():
            return HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
            
        self.embeddings = await loop.run_in_executor(None, _init_embeddings)
        
        os.makedirs(self.persist_dir, exist_ok=True)
        index_file = os.path.join(self.persist_dir, "index.faiss")
        
        if os.path.exists(index_file):
            logger.info("loading_existing_faiss_index", path=self.persist_dir)
            self.faiss_store = await loop.run_in_executor(
                None, 
                lambda: FAISS.load_local(self.persist_dir, self.embeddings, allow_dangerous_deserialization=True)
            )
        else:
            logger.info("creating_new_faiss_index")
            data_file = "app/slm/training_data/soc_finetune.jsonl"
            documents = []
            if os.path.exists(data_file):
                with open(data_file, 'r') as f:
                    for line in f:
                        if not line.strip(): continue
                        try:
                            record = json.loads(line)
                            text = record.get("text", "") or record.get("content", "") or json.dumps(record)
                            documents.append(Document(page_content=text, metadata={"source": data_file}))
                        except Exception:
                            pass
            
            if not documents:
                documents.append(Document(page_content="SOC Initialized. System baseline normal.", metadata={}))
                
            self.faiss_store = await loop.run_in_executor(
                None,
                lambda: FAISS.from_documents(documents, self.embeddings)
            )
            
            await loop.run_in_executor(None, lambda: self.faiss_store.save_local(self.persist_dir))
            
        self.retriever = self.faiss_store.as_retriever(search_kwargs={"k": 5})
        logger.info("rag_pipeline_initialized")

    async def get_index_stats(self) -> dict:
        return {
            "total_indexed": self.faiss_store.index.ntotal if self.faiss_store else 0,
            "collection_name": "soc_alerts",
            "persist_dir": self.persist_dir,
            "embedding_model": "all-MiniLM-L6-v2"
        }

    async def retrieve_similar(self, query: str, n_results: int = 3, filter_entity: str = None) -> list[dict]:
        if not self.retriever:
            return []
            
        docs = await asyncio.get_event_loop().run_in_executor(
            None, 
            lambda: self.retriever.invoke(query)
        )
        
        out = []
        for d in docs[:n_results]:
            out.append({
                "document": d.page_content,
                "metadata": d.metadata,
                "distance": 0.0
            })
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
