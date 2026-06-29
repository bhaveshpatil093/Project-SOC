import hashlib
import time
from collections import OrderedDict

import numpy as np
from sentence_transformers import SentenceTransformer

from app.logging_config import get_logger
logger = get_logger(__name__)

class ExactMatchCache:
    def __init__(self, maxsize: int = 200, ttl_seconds: int = 3600):
        self.maxsize = maxsize
        self.ttl_seconds = ttl_seconds
        self._cache = OrderedDict()
        self.hits = 0
        self.misses = 0

    def make_key(self, question: str, alert_id: str | None) -> str:
        s = f"{question.lower().strip()}|{alert_id or 'NONE'}"
        return hashlib.md5(s.encode("utf-8")).hexdigest()

    def get(self, cache_key: str) -> str | None:
        if cache_key in self._cache:
            item = self._cache[cache_key]
            if time.time() - item["timestamp"] > self.ttl_seconds:
                del self._cache[cache_key]
                self.misses += 1
                return None

            self._cache.move_to_end(cache_key)
            self.hits += 1
            return item["response"]

        self.misses += 1
        return None

    def set(self, cache_key: str, response: str):
        if cache_key in self._cache:
            self._cache.move_to_end(cache_key)
        self._cache[cache_key] = {"response": response, "timestamp": time.time()}

        if len(self._cache) > self.maxsize:
            self._cache.popitem(last=False)

    def get_stats(self) -> dict:
        return {
            "hits": self.hits,
            "misses": self.misses,
            "size": len(self._cache)
        }

    def clear(self):
        self._cache.clear()
        self.hits = 0
        self.misses = 0

class SemanticCache:
    def __init__(self, similarity_threshold: float = 0.92, maxsize: int = 500):
        self.similarity_threshold = similarity_threshold
        self.maxsize = maxsize
        self._model = None
        self._records = []
        self.hits = 0
        self.misses = 0
        self._similarities = []

    def _get_model(self):
        if self._model is None:
            self._model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        return self._model

    def find_similar(self, question: str, alert_id: str | None) -> str | None:
        if not self._records:
            self.misses += 1
            return None

        model = self._get_model()
        q_emb = model.encode(question)

        # Filter by alert_id
        candidates = [r for r in self._records if r["alert_id"] == alert_id]
        if not candidates:
            self.misses += 1
            return None

        cand_embs = np.array([c["embedding"] for c in candidates])

        # Compute cosine similarities
        norms1 = np.linalg.norm(q_emb)
        norms2 = np.linalg.norm(cand_embs, axis=1)

        if norms1 == 0:
            self.misses += 1
            return None

        sims = np.dot(cand_embs, q_emb) / (norms1 * norms2)
        best_idx = np.argmax(sims)
        best_sim = float(sims[best_idx])

        if best_sim >= self.similarity_threshold:
            self.hits += 1
            self._similarities.append(best_sim)
            # LRU refresh
            hit_rec = candidates[best_idx]
            self._records.remove(hit_rec)
            self._records.append(hit_rec)
            return hit_rec["response"]

        self.misses += 1
        return None

    def store(self, question: str, response: str, alert_id: str | None):
        model = self._get_model()
        emb = model.encode(question)

        rec = {
            "embedding": emb,
            "question": question,
            "response": response,
            "alert_id": alert_id,
            "timestamp": time.time()
        }

        self._records.append(rec)
        if len(self._records) > self.maxsize:
            self._records.pop(0)

    def get_stats(self) -> dict:
        avg_sim = sum(self._similarities) / len(self._similarities) if self._similarities else 0.0
        return {
            "hits": self.hits,
            "misses": self.misses,
            "size": len(self._records),
            "avg_similarity": round(avg_sim, 3)
        }

    def clear(self):
        self._records = []
        self.hits = 0
        self.misses = 0
        self._similarities = []

class SLMCache:
    def __init__(self):
        self.exact = ExactMatchCache()
        self.semantic = SemanticCache()

    def get(self, question: str, alert_id: str | None) -> tuple[str | None, str]:
        # 1. Exact Match
        k = self.exact.make_key(question, alert_id)
        res = self.exact.get(k)
        if res is not None:
            return res, "exact"

        # 2. Semantic Match
        res = self.semantic.find_similar(question, alert_id)
        if res is not None:
            return res, "semantic"

        return None, "miss"

    def set(self, question: str, response: str, alert_id: str | None):
        k = self.exact.make_key(question, alert_id)
        self.exact.set(k, response)
        self.semantic.store(question, response, alert_id)

    def get_combined_stats(self) -> dict:
        e_stats = self.exact.get_stats()
        s_stats = self.semantic.get_stats()

        total_hits = e_stats["hits"] + s_stats["hits"]
        total_misses = e_stats["misses"] + s_stats["misses"]
        total_requests = total_hits + total_misses
        hit_rate = (total_hits / total_requests * 100.0) if total_requests > 0 else 0.0

        return {
            "exact_hits": e_stats["hits"],
            "semantic_hits": s_stats["hits"],
            "misses": total_misses,
            "hit_rate_percent": round(hit_rate, 2),
            "exact_size": e_stats["size"],
            "semantic_size": s_stats["size"],
            "avg_semantic_similarity": s_stats["avg_similarity"]
        }

    def clear(self):
        self.exact.clear()
        self.semantic.clear()

_slm_cache = SLMCache()

def get_slm_cache() -> SLMCache:
    return _slm_cache
