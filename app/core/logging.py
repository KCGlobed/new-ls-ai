"""
Structured logging setup using structlog.
Call setup_logging() ONCE at application startup in main.py.

All modules get a logger like this:
    import structlog
    logger = structlog.get_logger(__name__)
"""
import logging
import sys
import structlog


def setup_logging(log_level: str = "INFO") -> None:
    structlog.configure(
        processors=[
            # Merges any context variables bound via structlog.contextvars.bind_contextvars()
            # (e.g. request_id, user_id set by middleware)
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,   # Full traceback in JSON on errors
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),     # Output as compact JSON lines
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(log_level.upper())
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )
