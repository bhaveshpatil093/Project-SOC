"""
Kibana Console Proxy Client
===========================
Provides a proxy interface to Elasticsearch via the Kibana Console API.
Since direct Elasticsearch access is disabled, all search queries route
through the Kibana proxy endpoint using HTTP Basic Auth.
"""

import json
import httpx
import urllib3
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings
from app.logging_config import get_logger

# Suppress InsecureRequestWarning for self-signed certificates in dev/staging
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = get_logger(__name__)

class KibanaProxyClient:
    """
    Singleton client for accessing Elasticsearch through the Kibana Console Proxy.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(KibanaProxyClient, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        
        self.base_url = f"{settings.KIBANA_URL}/api/console/proxy"
        self.headers = {
            "kbn-xsrf": "true",
            "Content-Type": "application/json"
        }
        self.auth = (settings.KIBANA_USER, settings.KIBANA_PASSWORD)
        
        # Configure the async HTTP client
        self.client = httpx.AsyncClient(
            verify=settings.KIBANA_VERIFY_SSL,
            timeout=30.0,
            auth=self.auth,
            headers=self.headers
        )
        self._initialized = True

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10), reraise=True)
    async def search(self, index: str, body: dict, size: int = 1000, **kwargs) -> dict:
        """
        Executes a search query via the proxy.
        Note: The Kibana proxy uses POST for all requests, passing 'method=GET' in the query params.
        """
        # Ensure size is applied to the payload
        if "size" not in body:
            body["size"] = size
            
        url = f"{self.base_url}?path={index}%2F_search&method=GET"
        
        try:
            response = await self.client.post(url, json=body)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error("kibana_proxy_search_error", index=index, error=str(e))
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10), reraise=True)
    async def msearch(self, index: str, queries: list[dict]) -> dict:
        """
        Executes a bulk multi-search query (_msearch) via the proxy.
        Body must be in NDJSON format.
        """
        url = f"{self.base_url}?path={index}%2F_msearch&method=POST"
        
        # Build NDJSON string: alternating header and query lines
        ndjson_lines = []
        for q in queries:
            ndjson_lines.append(json.dumps(q.get("header", {})))
            ndjson_lines.append(json.dumps(q.get("body", {})))
        
        ndjson_body = "\n".join(ndjson_lines) + "\n"
        
        # The proxy requires standard JSON content-type for the outer request,
        # but sometimes accepts ndjson if explicitly configured. The standard
        # Kibana proxy usually handles the payload transparently if sent as content.
        # We'll use the default headers but send the raw content.
        headers = self.headers.copy()
        headers["Content-Type"] = "application/x-ndjson"
        
        try:
            response = await self.client.post(url, content=ndjson_body, headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error("kibana_proxy_msearch_error", index=index, error=str(e))
            raise

    async def check_connection(self) -> bool:
        """
        Validates connection to the Kibana Proxy and underlying Elasticsearch cluster.
        """
        url = f"{self.base_url}?path=logs-system.syslog-*%2F_search&method=GET"
        body = {"query": {"match_all": {}}, "size": 1}
        
        try:
            response = await self.client.post(url, json=body)
            response.raise_for_status()
            logger.info("kibana_proxy_connection_success", url=settings.KIBANA_URL)
            return True
        except Exception as e:
            logger.error("kibana_proxy_connection_failed", url=settings.KIBANA_URL, error=str(e))
            return False

    async def close(self):
        """
        Closes the underlying HTTP client session.
        """
        if hasattr(self, 'client') and self.client:
            await self.client.aclose()
            logger.info("kibana_proxy_client_closed")
