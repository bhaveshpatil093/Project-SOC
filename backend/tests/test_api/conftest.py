import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock

from app.main import app
from app.db.elasticsearch import get_es_client
from app.api.auth import require_role

# Create an async mock for Elasticsearch
@pytest_asyncio.fixture
async def mock_es():
    es = AsyncMock()
    # Provide default behaviors if needed
    es.search.return_value = {
        "hits": {
            "total": {"value": 0},
            "hits": []
        }
    }
    return es

@pytest.fixture
def mock_slm_engine():
    engine = AsyncMock()
    engine.generate.return_value = "Test response"
    engine.generate_async.return_value = "Test response"
    return engine

@pytest_asyncio.fixture
async def client(mock_es):
    """Provides a test client with ES and Auth mocked out."""
    
    # Override Elasticsearch dependency
    async def override_get_es_client():
        return mock_es
        
    # Override Auth dependency to always allow
    def override_require_role(*allowed_roles):
        async def verify_token_mock():
            return {"sub": "test_user", "roles": allowed_roles, "org": "TEST"}
        return verify_token_mock
        
    app.dependency_overrides[get_es_client] = override_get_es_client
    app.dependency_overrides[require_role] = override_require_role

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
        
    app.dependency_overrides.clear()
