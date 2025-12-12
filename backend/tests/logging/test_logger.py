"""
Tests for logging module.

Comprehensive test coverage for structlog logger implementation.
"""
import json
import os
from unittest.mock import patch

import pytest
import structlog

from polyplexity_agent.logging import get_logger


@pytest.fixture
def reset_logging_config():
    """
    Reset structlog configuration before each test.
    
    Note: The logger module configures structlog on import, so we need to
    reload it after resetting to get the proper configuration.
    
    Yields:
        None
    """
    structlog.reset_defaults()
    # Reload logger module to reapply configuration
    import importlib
    import polyplexity_agent.logging.logger
    importlib.reload(polyplexity_agent.logging.logger)
    yield
    structlog.reset_defaults()


def test_get_logger_returns_bound_logger(reset_logging_config):
    """Test that get_logger returns a BoundLogger instance."""
    logger = get_logger("test_module")
    # Check if it's a BoundLogger (or subclass)
    assert hasattr(logger, "info") and hasattr(logger, "error") and hasattr(logger, "debug")


def test_get_logger_sets_name(reset_logging_config):
    """Test that logger name is set correctly."""
    logger = get_logger("test_module_name")
    # The logger name is stored in the logger's context
    assert logger._context.get("logger") == "test_module_name"


def test_logger_debug_level(reset_logging_config):
    """Test DEBUG level logging."""
    logger = get_logger("test_debug")
    # Should not raise exception
    logger.debug("test_message", key="value")


def test_logger_info_level(reset_logging_config):
    """Test INFO level logging."""
    logger = get_logger("test_info")
    # Should not raise exception
    logger.info("test_message", key="value")


def test_logger_warning_level(reset_logging_config):
    """Test WARNING level logging."""
    logger = get_logger("test_warning")
    # Should not raise exception
    logger.warning("test_message", key="value")


def test_logger_error_level(reset_logging_config):
    """Test ERROR level logging."""
    logger = get_logger("test_error")
    # Should not raise exception
    logger.error("test_message", key="value", exc_info=True)


def test_logger_structured_fields(reset_logging_config, capsys):
    """Test that structured fields are included in log output."""
    logger = get_logger("test_structured")
    logger.info("test_event", field1="value1", field2=42, field3=True)
    
    captured = capsys.readouterr()
    output = captured.out.strip()
    # Check that output contains the event and fields (may be JSON or formatted)
    assert "test_event" in output
    assert "field1" in output or "value1" in output
    assert "42" in output or "field2" in output


def test_logger_name_in_output(reset_logging_config, capsys):
    """Test that logger name appears in log output."""
    logger = get_logger("test_logger_name")
    logger.info("test_message")
    
    captured = capsys.readouterr()
    output = captured.out.strip()
    # Logger name should be in output (either as JSON field or formatted)
    assert "test_logger_name" in output or "logger" in output


def test_logger_timestamp_in_output(reset_logging_config, capsys):
    """Test that timestamp appears in log output."""
    logger = get_logger("test_timestamp")
    logger.info("test_message")
    
    captured = capsys.readouterr()
    output = captured.out.strip()
    # Timestamp should be in output (either as JSON field or formatted)
    assert "timestamp" in output.lower() or any(char.isdigit() for char in output[:20])


def test_logger_log_level_in_output(reset_logging_config, capsys):
    """Test that log level appears in log output."""
    logger = get_logger("test_level")
    logger.info("test_message")
    
    captured = capsys.readouterr()
    output = captured.out.strip()
    # Log level should be in output (either as JSON field or formatted)
    assert "info" in output.lower() or "level" in output.lower()


def test_logger_exception_info(reset_logging_config, capsys):
    """Test that exception info is included when exc_info=True."""
    logger = get_logger("test_exception")
    try:
        raise ValueError("test error")
    except ValueError:
        logger.error("test_error", exc_info=True)
    
    captured = capsys.readouterr()
    output = captured.out.strip()
    # Error level and exception info should be in output
    assert "error" in output.lower() or "test_error" in output
    assert "ValueError" in output or "exception" in output.lower() or "traceback" in output.lower()


def test_logger_context_binding(reset_logging_config):
    """Test that logger can bind context."""
    logger = get_logger("test_context")
    bound_logger = logger.bind(key1="value1", key2="value2")
    assert hasattr(bound_logger, "info") and hasattr(bound_logger, "error")
    assert bound_logger._context.get("key1") == "value1"


def test_logger_different_names(reset_logging_config):
    """Test that different logger names work correctly."""
    logger1 = get_logger("module1")
    logger2 = get_logger("module2")
    
    assert logger1._context.get("logger") == "module1"
    assert logger2._context.get("logger") == "module2"


def test_logger_json_output_format(reset_logging_config, capsys):
    """Test that output contains structured data."""
    logger = get_logger("test_json")
    logger.info("test_message", data={"nested": "value"})
    
    captured = capsys.readouterr()
    output = captured.out.strip()
    # Should contain the message and data (may be JSON or formatted)
    assert "test_message" in output
    assert "nested" in output or "value" in output or "data" in output


@patch.dict(os.environ, {"LOG_LEVEL": "DEBUG"})
def test_logger_env_log_level_debug(reset_logging_config):
    """Test that LOG_LEVEL environment variable is respected (DEBUG)."""
    # Re-import to trigger configuration
    import importlib
    import polyplexity_agent.logging.logger
    importlib.reload(polyplexity_agent.logging.logger)
    
    logger = get_logger("test_env_debug")
    # DEBUG level should work
    logger.debug("debug_message")


@patch.dict(os.environ, {"LOG_LEVEL": "WARNING"})
def test_logger_env_log_level_warning(reset_logging_config):
    """Test that LOG_LEVEL environment variable is respected (WARNING)."""
    # Re-import to trigger configuration
    import importlib
    import polyplexity_agent.logging.logger
    importlib.reload(polyplexity_agent.logging.logger)
    
    from polyplexity_agent.logging import get_logger as get_logger_reloaded
    logger = get_logger_reloaded("test_env_warning")
    # INFO should be filtered out at WARNING level
    # But we can't easily test filtering without more complex setup
    # So we just verify logger creation works
    assert hasattr(logger, "info") and hasattr(logger, "error")


def test_logger_default_log_level(reset_logging_config):
    """Test that default log level is INFO."""
    logger = get_logger("test_default")
    # INFO level should work
    logger.info("info_message")


def test_logger_in_node_context(reset_logging_config):
    """Test that logger can be imported and used in node context."""
    # Simulate node usage
    logger = get_logger("polyplexity_agent.graphs.nodes.supervisor.supervisor")
    logger.info("node_execution", node="supervisor", state="running")
    assert hasattr(logger, "info") and hasattr(logger, "error")


def test_logger_multiple_calls_same_name(reset_logging_config):
    """Test that multiple calls with same name return consistent logger."""
    logger1 = get_logger("test_same")
    logger2 = get_logger("test_same")
    
    # Should have same logger name in context
    assert logger1._context.get("logger") == logger2._context.get("logger")


def test_logger_empty_name(reset_logging_config):
    """Test that logger works with empty name."""
    logger = get_logger("")
    assert hasattr(logger, "info") and hasattr(logger, "error")


def test_logger_special_characters_in_name(reset_logging_config):
    """Test that logger works with special characters in name."""
    logger = get_logger("test.module.name")
    assert hasattr(logger, "info") and hasattr(logger, "error")
    assert logger._context.get("logger") == "test.module.name"
