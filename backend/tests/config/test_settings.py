"""
Tests for Settings configuration class.
"""
from pathlib import Path

import pytest

from polyplexity_agent.config.settings import Settings


def test_settings_default_values():
    """
    Test that Settings class has correct default values.
    """
    settings = Settings()
    
    assert settings.model_name == "openai/gpt-oss-120b"
    assert settings.temperature == 0.0
    assert settings.thread_name_model == "llama-3.1-8b-instant"
    assert settings.thread_name_temperature == 0.3
    assert settings.max_structured_output_retries == 3
    assert settings.state_logs_dir is not None
    assert isinstance(settings.state_logs_dir, Path)


def test_settings_custom_values():
    """
    Test that Settings class accepts custom values.
    """
    custom_dir = Path("/tmp/custom_logs")
    settings = Settings(
        model_name="custom-model",
        temperature=0.5,
        max_structured_output_retries=5,
        state_logs_dir=custom_dir
    )
    
    assert settings.model_name == "custom-model"
    assert settings.temperature == 0.5
    assert settings.max_structured_output_retries == 5
    assert settings.state_logs_dir == custom_dir


def test_settings_state_logs_dir_default():
    """
    Test that state_logs_dir defaults to polyplexity_agent/state_logs.
    """
    settings = Settings()
    
    # Should be relative to polyplexity_agent directory
    assert "polyplexity_agent" in str(settings.state_logs_dir)
    assert "state_logs" in str(settings.state_logs_dir)
    assert settings.state_logs_dir.name == "state_logs"
