"""Configuration management for the real-time voice assistant system.

This module provides configuration dataclasses and a ConfigLoader that reads
from environment variables and YAML configuration files.
"""

from dataclasses import dataclass
from typing import Optional
import os
import yaml
from pathlib import Path


@dataclass
class APIConfig:
    """Configuration for external API services."""
    
    # Required fields (no defaults)
    gemini_api_key: str
    elevenlabs_api_key: str
    elevenlabs_voice_id: str
    
    # Optional fields (with defaults)
    whisper_api_key: Optional[str] = None  # Now optional - used for Wav2Vec2 model name
    whisper_timeout: float = 3.0
    gemini_model: str = "meta-llama/llama-3.2-3b-instruct:free"
    gemini_timeout: float = 5.0
    elevenlabs_timeout: float = 3.0


@dataclass
class ServerConfig:
    """Configuration for server components."""
    
    websocket_host: str = "0.0.0.0"
    websocket_port: int = 8000
    metrics_host: str = "0.0.0.0"
    metrics_port: int = 8001


@dataclass
class PipelineConfig:
    """Configuration for pipeline behavior."""
    
    audio_buffer_duration_ms: int = 1000
    token_buffer_size: int = 10
    max_conversation_turns: int = 10


@dataclass
class ResilienceConfig:
    """Configuration for resilience patterns."""
    
    retry_max_attempts: int = 3
    retry_initial_delay_ms: int = 100
    retry_max_delay_ms: int = 5000
    
    circuit_breaker_failure_threshold: float = 0.5
    circuit_breaker_window_size: int = 10
    circuit_breaker_timeout_seconds: int = 30


@dataclass
class ObservabilityConfig:
    """Configuration for observability features."""
    
    enable_recording: bool = False
    recording_storage_path: str = "./recordings"
    log_level: str = "INFO"
    
    latency_budget_asr_ms: float = 500
    latency_budget_llm_first_token_ms: float = 300
    latency_budget_tts_ms: float = 400
    latency_budget_end_to_end_ms: float = 2000


@dataclass
class SystemConfig:
    """Complete system configuration combining all config sections."""
    
    api: APIConfig
    server: ServerConfig
    pipeline: PipelineConfig
    resilience: ResilienceConfig
    observability: ObservabilityConfig


class ConfigLoader:
    """Loads and validates configuration from environment variables and files.
    
    Configuration is loaded with the following precedence:
    1. Environment variables (highest priority)
    2. YAML configuration file (if CONFIG_FILE env var is set)
    3. Default values (lowest priority)
    
    Required fields (API keys) must be provided via environment or config file.
    """
    
    @staticmethod
    def load() -> SystemConfig:
        """Load configuration from environment variables and config file.
        
        Returns:
            SystemConfig: Complete validated system configuration
            
        Raises:
            ValueError: If required configuration values are missing
        """
        # Check for config file
        config_file = os.getenv("CONFIG_FILE")
        file_config = {}
        
        if config_file and Path(config_file).exists():
            with open(config_file) as f:
                file_config = yaml.safe_load(f) or {}
        
        # API configuration (required fields)
        api_config = APIConfig(
            whisper_api_key=ConfigLoader._get_str("WHISPER_API_KEY", file_config, None),  # Optional - Wav2Vec2 model name
            whisper_timeout=ConfigLoader._get_float("WHISPER_TIMEOUT", file_config, 3.0),
            
            gemini_api_key=ConfigLoader._require_env("GEMINI_API_KEY", file_config),
            gemini_model=ConfigLoader._get_str("GEMINI_MODEL", file_config, "meta-llama/llama-3.2-3b-instruct:free"),
            gemini_timeout=ConfigLoader._get_float("GEMINI_TIMEOUT", file_config, 5.0),
            
            elevenlabs_api_key=ConfigLoader._require_env("ELEVENLABS_API_KEY", file_config),
            elevenlabs_voice_id=ConfigLoader._require_env("ELEVENLABS_VOICE_ID", file_config),
            elevenlabs_timeout=ConfigLoader._get_float("ELEVENLABS_TIMEOUT", file_config, 3.0)
        )
        
        # Server configuration
        server_config = ServerConfig(
            websocket_host=ConfigLoader._get_str("WEBSOCKET_HOST", file_config, "0.0.0.0"),
            websocket_port=ConfigLoader._get_int("WEBSOCKET_PORT", file_config, 8000),
            metrics_host=ConfigLoader._get_str("METRICS_HOST", file_config, "0.0.0.0"),
            metrics_port=ConfigLoader._get_int("METRICS_PORT", file_config, 8001)
        )
        
        # Pipeline configuration
        pipeline_config = PipelineConfig(
            audio_buffer_duration_ms=ConfigLoader._get_int("AUDIO_BUFFER_MS", file_config, 1000),
            token_buffer_size=ConfigLoader._get_int("TOKEN_BUFFER_SIZE", file_config, 10),
            max_conversation_turns=ConfigLoader._get_int("MAX_CONVERSATION_TURNS", file_config, 10)
        )
        
        # Resilience configuration
        resilience_config = ResilienceConfig(
            retry_max_attempts=ConfigLoader._get_int("RETRY_MAX_ATTEMPTS", file_config, 3),
            retry_initial_delay_ms=ConfigLoader._get_int("RETRY_INITIAL_DELAY_MS", file_config, 100),
            retry_max_delay_ms=ConfigLoader._get_int("RETRY_MAX_DELAY_MS", file_config, 5000),
            
            circuit_breaker_failure_threshold=ConfigLoader._get_float("CB_FAILURE_THRESHOLD", file_config, 0.5),
            circuit_breaker_window_size=ConfigLoader._get_int("CB_WINDOW_SIZE", file_config, 10),
            circuit_breaker_timeout_seconds=ConfigLoader._get_int("CB_TIMEOUT_SECONDS", file_config, 30)
        )
        
        # Observability configuration
        observability_config = ObservabilityConfig(
            enable_recording=ConfigLoader._get_bool("ENABLE_RECORDING", file_config, False),
            recording_storage_path=ConfigLoader._get_str("RECORDING_PATH", file_config, "./recordings"),
            log_level=ConfigLoader._get_str("LOG_LEVEL", file_config, "INFO"),
            
            latency_budget_asr_ms=ConfigLoader._get_float("LATENCY_BUDGET_ASR_MS", file_config, 500),
            latency_budget_llm_first_token_ms=ConfigLoader._get_float("LATENCY_BUDGET_LLM_MS", file_config, 300),
            latency_budget_tts_ms=ConfigLoader._get_float("LATENCY_BUDGET_TTS_MS", file_config, 400),
            latency_budget_end_to_end_ms=ConfigLoader._get_float("LATENCY_BUDGET_E2E_MS", file_config, 2000)
        )
        
        return SystemConfig(
            api=api_config,
            server=server_config,
            pipeline=pipeline_config,
            resilience=resilience_config,
            observability=observability_config
        )
    
    @staticmethod
    def _require_env(key: str, file_config: dict) -> str:
        """Get required configuration value from environment or file.
        
        Args:
            key: Environment variable name (uppercase)
            file_config: Dictionary loaded from YAML file
            
        Returns:
            str: Configuration value
            
        Raises:
            ValueError: If the required value is not found
        """
        value = os.getenv(key) or file_config.get(key.lower())
        if not value:
            raise ValueError(f"Required configuration {key} not found in environment or config file")
        return value
    
    @staticmethod
    def _get_str(key: str, file_config: dict, default: str) -> str:
        """Get string configuration value with default.
        
        Args:
            key: Environment variable name (uppercase)
            file_config: Dictionary loaded from YAML file
            default: Default value if not found
            
        Returns:
            str: Configuration value or default
        """
        return os.getenv(key) or file_config.get(key.lower(), default)
    
    @staticmethod
    def _get_int(key: str, file_config: dict, default: int) -> int:
        """Get integer configuration value with default.
        
        Args:
            key: Environment variable name (uppercase)
            file_config: Dictionary loaded from YAML file
            default: Default value if not found
            
        Returns:
            int: Configuration value or default
        """
        value = os.getenv(key) or file_config.get(key.lower())
        return int(value) if value is not None else default
    
    @staticmethod
    def _get_float(key: str, file_config: dict, default: float) -> float:
        """Get float configuration value with default.
        
        Args:
            key: Environment variable name (uppercase)
            file_config: Dictionary loaded from YAML file
            default: Default value if not found
            
        Returns:
            float: Configuration value or default
        """
        value = os.getenv(key) or file_config.get(key.lower())
        return float(value) if value is not None else default
    
    @staticmethod
    def _get_bool(key: str, file_config: dict, default: bool) -> bool:
        """Get boolean configuration value with default.
        
        Args:
            key: Environment variable name (uppercase)
            file_config: Dictionary loaded from YAML file
            default: Default value if not found
            
        Returns:
            bool: Configuration value or default
        """
        value = os.getenv(key) or file_config.get(key.lower())
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        return str(value).lower() in ("true", "1", "yes")
