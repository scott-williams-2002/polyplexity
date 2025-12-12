"""
Structured logging module using structlog.

Provides machine-friendly JSON logging output for the application.
"""
import logging
import os
from typing import Any

import structlog


def _configure_logging() -> None:
    """
    Configure structlog for machine-friendly JSON output.
    
    Sets up processors for structured logging with JSON renderer.
    Log level is configured from LOG_LEVEL environment variable (default: INFO).
    """
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, log_level, logging.INFO),
    )
    
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level, logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


# Configure logging on module import
_configure_logging()


def get_logger(name: str) -> structlog.BoundLogger:
    """
    Get a logger instance for the given name.
    
    Args:
        name: Logger name, typically module name (e.g., "polyplexity_agent.graphs.nodes.supervisor")
        
    Returns:
        Configured structlog BoundLogger instance with logger name bound
    """
    return structlog.get_logger(name).bind(logger=name)
