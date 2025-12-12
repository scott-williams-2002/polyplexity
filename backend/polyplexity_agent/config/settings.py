"""
Application settings configuration.

Manages model configuration, state logs directory, and other application settings.
Uses Pydantic BaseSettings for future environment variable support.
"""
from pathlib import Path
from typing import Optional

from pydantic import ConfigDict, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings configuration.
    
    Contains model configuration, state logs directory, and retry settings.
    Default values are hardcoded but can be overridden via environment variables
    in the future.
    """
    
    # Model configuration
    model_name: str = "openai/gpt-oss-120b"
    temperature: float = 0.0
    thread_name_model: str = "llama-3.1-8b-instant"
    thread_name_temperature: float = 0.3
    max_structured_output_retries: int = 3
    
    # State logs configuration
    state_logs_dir: Optional[Path] = None
    
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore extra environment variables not defined in this class
    )
    
    @field_validator("state_logs_dir", mode="before")
    @classmethod
    def set_default_state_logs_dir(cls, v):
        """
        Set default state_logs_dir if not provided.
        
        Args:
            v: The value provided (or None)
            
        Returns:
            Path object for state logs directory
        """
        if v is None:
            # Default to polyplexity_agent/state_logs relative to this file
            config_dir = Path(__file__).parent.parent
            return config_dir / "state_logs"
        return v
