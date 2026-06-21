import os

with open("backend/app/main.py", "r") as f:
    content = f.read()

import_stmt = "from app.logging_config import configure_logging, get_logger, enable_es_logging\n"
content = content.replace("from app.logging_config import configure_logging, get_logger\n", import_stmt)

call_stmt = """    # Initialize ES connection
    await get_es_client()
    enable_es_logging(get_es_client)
    
    # Initialize Log Viewer mappings
    from app.monitoring.log_viewer import log_viewer_instance
    try:
        es = await get_es_client()
        await log_viewer_instance.initialize(es)
    except Exception as e:
        logger.warning(f"Failed to initialize log viewer index: {e}")
"""
content = content.replace("    # Initialize ES connection\n    await get_es_client()", call_stmt)

with open("backend/app/main.py", "w") as f:
    f.write(content)
