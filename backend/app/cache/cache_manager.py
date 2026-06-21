import time
from collections.abc import Callable
from functools import wraps
from typing import Any


class CacheEntry:
    def __init__(self, value, ttl_seconds: int):
        self.value = value
        self.expires_at = time.time() + ttl_seconds
        self.hit_count = 0

    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at

class InMemoryCache:
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._store: dict[str, CacheEntry] = {}
        self.hits = 0
        self.misses = 0

    async def get(self, key: str) -> Any | None:
        if key in self._store:
            entry = self._store[key]
            if not entry.is_expired:
                entry.hit_count += 1
                self.hits += 1
                return entry.value
            del self._store[key]
        self.misses += 1
        return None

    async def set(self, key: str, value: Any, ttl_seconds: int = 300):
        if len(self._store) >= self.max_size:
            await self.clear_expired()
            if len(self._store) >= self.max_size:
                # Remove an arbitrary element
                self._store.pop(next(iter(self._store)))
        self._store[key] = CacheEntry(value, ttl_seconds)

    async def delete(self, key: str):
        self._store.pop(key, None)

    async def clear_expired(self):
        expired_keys = [k for k, v in self._store.items() if v.is_expired]
        for k in expired_keys:
            del self._store[k]

    def get_stats(self) -> dict:
        total_reqs = self.hits + self.misses
        hit_rate = self.hits / total_reqs if total_reqs > 0 else 0.0
        return {
            "size": len(self._store),
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(hit_rate, 4)
        }

cache = InMemoryCache()

def cache_result(ttl_seconds: int = 300, key_fn: Callable = None):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if key_fn:
                cache_key = key_fn(*args, **kwargs)
            else:
                cache_key = f"{func.__name__}:{args}:{kwargs}"

            cached = await cache.get(cache_key)
            if cached is not None:
                return cached

            result = await func(*args, **kwargs)
            await cache.set(cache_key, result, ttl_seconds)
            return result
        return wrapper
    return decorator
