import os

with open("backend/app/logging_config.py", "r") as f:
    content = f.read()

handler_code = """
import asyncio
from datetime import datetime

class ElasticsearchLogHandler(logging.Handler):
    def __init__(self, es_client_getter, index="soc-application-logs"):
        super().__init__()
        self.es_client_getter = es_client_getter
        self.index = index
        self._buffer = []
        self._task = None

    def emit(self, record):
        try:
            msg = self.format(record)
            log_entry = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "level": record.levelname,
                "logger_name": record.name,
                "message": msg,
                "correlation_id": CORRELATION_ID_CTX.get(),
                "module": record.module,
                "funcName": record.funcName,
                "lineno": record.lineno
            }
            self._buffer.append(log_entry)
            
            if not self._task or self._task.done():
                try:
                    loop = asyncio.get_running_loop()
                    self._task = loop.create_task(self._flush_buffer())
                except RuntimeError:
                    # No running loop
                    pass
        except Exception:
            self.handleError(record)

    async def _flush_buffer(self):
        await asyncio.sleep(5.0)
        if not self._buffer:
            return
            
        logs_to_write = self._buffer[:]
        self._buffer.clear()
        
        try:
            es = await self.es_client_getter()
            if es:
                actions = [{"_index": self.index, "_source": log} for log in logs_to_write]
                from elasticsearch.helpers import async_bulk
                await async_bulk(es, actions, stats_only=True, raise_on_error=False, raise_on_exception=False)
        except Exception:
            pass # Silently drop logs if ES is down to avoid recursion loops
"""

if "class ElasticsearchLogHandler" not in content:
    # Insert after CORRELATION_ID_CTX
    content = content.replace('CORRELATION_ID_CTX = contextvars.ContextVar("correlation_id", default=None)', 'CORRELATION_ID_CTX = contextvars.ContextVar("correlation_id", default=None)\n' + handler_code)

    # Need to add this handler to the root logger in configure_logging
    # but we need es_client_getter. We can pass it or import it inside.
    # It's better to add the handler dynamically in main.py, or pass es_client_getter to configure_logging.
    # Wait, the prompt says Update logging_config.py to also write logs to ES.
    
    # We can add a function `enable_es_logging(es_client_getter)` to attach the handler.
    enable_fn = """
def enable_es_logging(es_client_getter):
    root_logger = logging.getLogger()
    # Check if already added
    if any(isinstance(h, ElasticsearchLogHandler) for h in root_logger.handlers):
        return
    es_handler = ElasticsearchLogHandler(es_client_getter)
    # Use same formatter if any
    if root_logger.handlers:
        es_handler.setFormatter(root_logger.handlers[0].formatter)
    root_logger.addHandler(es_handler)
"""
    content += "\n" + enable_fn

with open("backend/app/logging_config.py", "w") as f:
    f.write(content)
