"""
Elasticsearch Client Protocol & Capability Detection
=====================================================
Defines the shared interface for Elasticsearch-compatible clients and provides
a single helper function used throughout the codebase to detect whether a client
supports native Elasticsearch index-management APIs.

This enables clean degradation: when only KibanaProxyClient is available,
index-management operations are skipped rather than crashing startup.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class IndexManagementProtocol(Protocol):
    """
    Structural protocol for the Elasticsearch indices namespace.
    Only the native AsyncElasticsearch client satisfies this protocol.
    """

    async def exists(self, *, index: str, **kwargs: Any) -> bool:
        ...

    async def create(self, *, index: str, body: dict, **kwargs: Any) -> dict:
        ...

    async def delete(self, *, index: str, **kwargs: Any) -> dict:
        ...

    async def put_mapping(self, *, index: str, body: dict, **kwargs: Any) -> dict:
        ...


@runtime_checkable
class ESClientProtocol(Protocol):
    """
    Structural protocol describing the full Elasticsearch client interface
    used across this codebase. Both KibanaProxyClient and AsyncElasticsearch
    should satisfy the methods they actually implement.
    """

    async def search(self, *, index: str, body: dict, **kwargs: Any) -> dict:
        ...

    async def index(self, *, index: str, id: str, body: dict, **kwargs: Any) -> dict:
        ...

    async def get(self, *, index: str, id: str, **kwargs: Any) -> dict:
        ...

    async def update(self, *, index: str, id: str, body: dict, **kwargs: Any) -> dict:
        ...

    async def delete(self, *, index: str, id: str, **kwargs: Any) -> dict:
        ...


def supports_index_management(client: Any) -> bool:
    """
    Returns True if the given ES client supports native index-management APIs
    (i.e., exposes an `indices` namespace with exists/create/delete/put_mapping).

    Use this single function everywhere instead of scattering `hasattr(es, "indices")`
    checks across the codebase.

    Examples:
        AsyncElasticsearch → True
        KibanaProxyClient  → False
    """
    return hasattr(client, "indices") and client.indices is not None
