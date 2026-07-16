"""
Kibana Console Proxy Client
===========================
Provides a proxy interface to Elasticsearch via the Kibana Console API.
Since direct Elasticsearch access is disabled, all search queries route
through the Kibana proxy endpoint using HTTP Basic Auth.

Write-path methods (index, get, update, delete, mget) are implemented as
graceful stubs that log a warning and return sensible defaults. This allows
startup components that call these methods to degrade cleanly instead of
crashing with AttributeError.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import urllib3
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)
import logging as stdlib_logging

from app.config import settings
from app.logging_config import get_logger

# Suppress InsecureRequestWarning for self-signed certificates in dev/staging
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = get_logger(__name__)

# Signals to capability-detection helpers that this client cannot manage indices.
SUPPORTS_INDEX_MANAGEMENT: bool = False


def _validate_url_scheme(url: str) -> None:
    """Warn loudly if an HTTPS URL is configured against a plain-HTTP Kibana server."""
    if url.startswith("https://"):
        logger.warning(
            "kibana_url_https_detected",
            url=url,
            hint=(
                "Kibana is configured with HTTPS but may be running on HTTP. "
                "If you see SSL errors (WRONG_VERSION_NUMBER), change KIBANA_URL "
                "to http:// in your .env.development file."
            ),
        )


class KibanaProxyClient:
    """
    Singleton client for accessing Elasticsearch through the Kibana Console Proxy.

    Capabilities:
        ✓ search()           — full search queries via Kibana proxy
        ✓ msearch()          — bulk multi-search via Kibana proxy
        ✓ check_connection() — connectivity probe via /_cluster/health
        ✗ index/get/update/delete/mget — not supported; stubs log a warning and no-op

    Index management (es.indices.*) is NOT supported. Use supports_index_management()
    from app.ingestion.es_client_protocol to detect this before calling index APIs.
    """

    SUPPORTS_INDEX_MANAGEMENT: bool = False

    _instance: "KibanaProxyClient | None" = None

    def __new__(cls) -> "KibanaProxyClient":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return

        _validate_url_scheme(settings.KIBANA_URL)

        self.base_url = f"{settings.KIBANA_URL}/api/console/proxy"
        self.headers = {
            "kbn-xsrf": "true",
            "Content-Type": "application/json",
        }
        self.auth = (settings.KIBANA_USER, settings.KIBANA_PASSWORD)

        self.client = httpx.AsyncClient(
            verify=settings.KIBANA_VERIFY_SSL,
            timeout=httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=5.0),
            auth=self.auth,
            headers=self.headers,
        )
        self._initialized = True
        logger.info(
            "kibana_proxy_client_initialized",
            base_url=self.base_url,
            verify_ssl=settings.KIBANA_VERIFY_SSL,
        )

    # -------------------------------------------------------------------------
    # Search APIs (fully functional via Kibana proxy)
    # -------------------------------------------------------------------------

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(httpx.HTTPError),
        before_sleep=before_sleep_log(stdlib_logging.getLogger(__name__), stdlib_logging.WARNING),
        reraise=True,
    )
    async def search(self, index: str, body: dict, size: int = 1000, **kwargs: Any) -> dict:
        """
        Executes a search query via the Kibana Console proxy.
        Extra kwargs (e.g. ignore_unavailable, sort) are accepted but ignored —
        they apply to the native ES client API only.
        """
        if "size" not in body:
            body["size"] = size

        # URL-encode the index pattern
        import urllib.parse
        encoded_index = urllib.parse.quote(index, safe="")
        url = f"{self.base_url}?path={encoded_index}%2F_search&method=GET"

        try:
            response = await self.client.post(url, json=body)
            response.raise_for_status()
            data = response.json()
            logger.debug(
                "kibana_proxy_search_ok",
                index=index,
                hits=data.get("hits", {}).get("total", {}).get("value", "?"),
            )
            return data
        except httpx.HTTPStatusError as e:
            logger.error(
                "kibana_proxy_search_http_error",
                index=index,
                status=e.response.status_code,
                body=e.response.text[:500],
            )
            raise
        except httpx.RequestError as e:
            logger.error("kibana_proxy_search_connection_error", index=index, error=str(e))
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(httpx.HTTPError),
        reraise=True,
    )
    async def msearch(self, index: str, queries: list[dict]) -> dict:
        """
        Executes a bulk multi-search query (_msearch) via the Kibana proxy.
        Body is serialized as NDJSON.
        """
        import urllib.parse
        encoded_index = urllib.parse.quote(index, safe="")
        url = f"{self.base_url}?path={encoded_index}%2F_msearch&method=POST"

        ndjson_lines: list[str] = []
        for q in queries:
            ndjson_lines.append(json.dumps(q.get("header", {})))
            ndjson_lines.append(json.dumps(q.get("body", {})))

        ndjson_body = "\n".join(ndjson_lines) + "\n"
        headers = {**self.headers, "Content-Type": "application/x-ndjson"}

        try:
            response = await self.client.post(url, content=ndjson_body, headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error("kibana_proxy_msearch_error", index=index, error=str(e))
            raise

    # -------------------------------------------------------------------------
    # Write-path stubs (graceful no-ops — Kibana proxy does not support writes)
    # -------------------------------------------------------------------------

    async def index(self, *, index: str, id: str = None, body: dict, **kwargs: Any) -> dict:
        """Stub: write-indexing is not supported via Kibana proxy."""
        logger.debug(
            "kibana_proxy_write_skipped",
            operation="index",
            index=index,
            doc_id=id,
            reason="KibanaProxyClient does not support write operations",
        )
        return {"result": "noop", "_index": index, "_id": id}

    async def get(self, *, index: str, id: str, **kwargs: Any) -> dict:
        """Stub: document get-by-id is not supported via Kibana proxy."""
        logger.debug(
            "kibana_proxy_write_skipped",
            operation="get",
            index=index,
            doc_id=id,
            reason="KibanaProxyClient does not support direct document retrieval",
        )
        return {"found": False, "_index": index, "_id": id}

    async def mget(self, *, index: str, body: dict, **kwargs: Any) -> dict:
        """Stub: mget is not supported via Kibana proxy."""
        logger.debug(
            "kibana_proxy_write_skipped",
            operation="mget",
            index=index,
            reason="KibanaProxyClient does not support mget",
        )
        ids = body.get("ids", [])
        return {"docs": [{"_id": i, "_index": index, "found": False} for i in ids]}

    async def update(self, *, index: str, id: str, body: dict, **kwargs: Any) -> dict:
        """Stub: document update is not supported via Kibana proxy."""
        logger.debug(
            "kibana_proxy_write_skipped",
            operation="update",
            index=index,
            doc_id=id,
            reason="KibanaProxyClient does not support write operations",
        )
        return {"result": "noop", "_index": index, "_id": id}

    async def delete(self, *, index: str, id: str, **kwargs: Any) -> dict:
        """Stub: document delete is not supported via Kibana proxy."""
        logger.debug(
            "kibana_proxy_write_skipped",
            operation="delete",
            index=index,
            doc_id=id,
            reason="KibanaProxyClient does not support write operations",
        )
        return {"result": "noop", "_index": index, "_id": id}

    # -------------------------------------------------------------------------
    # Connectivity
    # -------------------------------------------------------------------------

    async def check_connection(self) -> bool:
        """
        Validates the connection to Kibana and the underlying Elasticsearch cluster.

        Uses /_cluster/health as a reliable, always-available probe endpoint.
        Falls back to a simple syslog search if cluster health fails.
        Prints a clear ✓/✗ startup banner.
        """
        # Primary probe: cluster health via Kibana proxy
        primary_url = f"{self.base_url}?path=_cluster%2Fhealth&method=GET"
        try:
            response = await self.client.get(primary_url)
            response.raise_for_status()
            data = response.json()
            cluster_status = data.get("status", "unknown")
            logger.info(
                "✓ Kibana connection established",
                kibana_url=settings.KIBANA_URL,
                cluster_status=cluster_status,
                cluster_name=data.get("cluster_name", "unknown"),
            )
            print(
                f"\n{'='*60}\n"
                f"✓  KIBANA CONNECTED\n"
                f"   URL:     {settings.KIBANA_URL}\n"
                f"   Cluster: {data.get('cluster_name', 'unknown')} "
                f"[{cluster_status.upper()}]\n"
                f"{'='*60}\n"
            )
            return True
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                # Kibana proxy path may differ — try fallback
                pass
            else:
                logger.error(
                    "✗ Kibana connection failed (HTTP error)",
                    url=settings.KIBANA_URL,
                    status=e.response.status_code,
                    body=e.response.text[:300],
                )
                self._print_failure_banner(str(e))
                return False
        except Exception as e:
            logger.error("✗ Kibana connection failed", url=settings.KIBANA_URL, error=str(e))
            self._print_failure_banner(str(e))
            return False

        # Fallback probe: search syslog index
        fallback_url = f"{self.base_url}?path=logs-system.syslog-*%2F_search&method=GET"
        body = {"query": {"match_all": {}}, "size": 1}
        try:
            response = await self.client.post(fallback_url, json=body)
            response.raise_for_status()
            logger.info("✓ Kibana connected (via fallback syslog probe)", url=settings.KIBANA_URL)
            print(
                f"\n{'='*60}\n"
                f"✓  KIBANA CONNECTED (fallback probe)\n"
                f"   URL: {settings.KIBANA_URL}\n"
                f"{'='*60}\n"
            )
            return True
        except Exception as e:
            logger.error("✗ Kibana connection failed (all probes)", url=settings.KIBANA_URL, error=str(e))
            self._print_failure_banner(str(e))
            return False

    def _print_failure_banner(self, error: str) -> None:
        print(
            f"\n{'='*60}\n"
            f"✗  KIBANA CONNECTION FAILED\n"
            f"   URL:   {settings.KIBANA_URL}\n"
            f"   Error: {error[:100]}\n"
            f"   Hint:  Check KIBANA_URL in .env.development\n"
            f"          Make sure it uses http:// not https://\n"
            f"{'='*60}\n"
        )

    async def close(self) -> None:
        """Closes the underlying HTTP client session and resets the singleton."""
        if hasattr(self, "client") and self.client:
            await self.client.aclose()
            logger.info("kibana_proxy_client_closed")
        # Reset singleton so a fresh instance can be created if needed (e.g. tests)
        KibanaProxyClient._instance = None
