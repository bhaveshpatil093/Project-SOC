import contextvars
import logging

import structlog

CORRELATION_ID_CTX = contextvars.ContextVar("correlation_id", default=None)




def configure_logging(log_level: str = "INFO", json_output: bool = True):
    # Configure stdlib logging bridge
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, log_level.upper(), logging.INFO),
    )

    def add_correlation_id(logger, method_name, event_dict):
        corr_id = CORRELATION_ID_CTX.get()
        if corr_id:
            event_dict["correlation_id"] = corr_id
        return event_dict

    processors = [
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        add_correlation_id,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    if json_output:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

def get_logger(name: str) -> structlog.BoundLogger:
    return structlog.get_logger(name)



