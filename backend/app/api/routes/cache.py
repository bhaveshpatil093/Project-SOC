from fastapi import APIRouter, Depends
from app.auth.jwt import require_role
from app.cache.cache_manager import cache

router = APIRouter()

@router.get("/stats", dependencies=[Depends(require_role("admin", "analyst"))])
async def get_cache_stats():
    """Returns hit/miss stats for the in-memory cache layer."""
    return cache.get_stats()
