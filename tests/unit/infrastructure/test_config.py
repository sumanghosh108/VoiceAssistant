"""Unit tests for configuration management."""

import os
import pytest
import tempfile
from pathlib import Path
from src.infrastructure.config import (
    APIConfig,
    ServerConfig,
    PipelineConfig,
    ResilienceConfig,
    ObservabilityConfig,
    SystemConfig,
    ConfigLoader
)


class TestConfigDataclasses:
    """Test configuration dataclasses."""
    
    def test_api_config_creation(self):
        """Test APIConfig can be created with required fields."""
        config = APIConfig(
            whisper_api_key="test-whisper-key",
            gemini_api_key="test-gemini-key",
            elevenlabs_api_key="test-elevenlabs-key",
            elevenlabs_voice_id="test-voice-id"
        )
        
        assert config.whisper_api_key == "test-whisper-key"
        assert config.gemini_api_key == "test-gemini-key"
        assert config.elevenlabs_api_key == "test-elevenlabs-key"
        assert config.elevenlabs_voice_id == "test-voice-id"
        assert config.whisper_timeout == 3.0  # default
        assert config.gemini_timeout == 5.0  # default
        assert config.elevenlabs_timeout == 3.0  # default
    
    def test_server_config_defaults(self):
        """Test ServerConfig has correct defaults."""
        config = ServerConfig()
        
        assert config.websocket_host == "0.0.0.0"
        assert config.websocket_port == 8000
        assert config.metrics_host == "0.0.0.0"
        assert config.metrics_port == 8001
    
    def test_pipeline_config_defaults(self):
        """Test PipelineConfig has correct defaults."""
        config = PipelineConfig()
        
        assert config.audio_buffer_duration_ms == 1000
        assert config.token_buffer_size == 10
        assert config.max_conversation_turns == 10
    
    def test_resilience_config_defaults(self):
        """Test ResilienceConfig has correct defaults."""
        config = ResilienceConfig()
        
        assert config.retry_max_attempts == 3
        assert config.retry_initial_delay_ms == 100
        assert config.retry_max_delay_ms == 5000
        assert config.circuit_breaker_failure_threshold == 0.5
        assert config.circuit_breaker_window_size == 10
        assert config.circuit_breaker_timeout_seconds == 30
    
    def test_observability_config_defaults(self):
        """Test ObservabilityConfig has correct defaults."""
        config = ObservabilityConfig()
        
        assert config.enable_recording is False
        assert config.recording_storage_path == "./recordings"
        assert config.log_level == "INFO"
        assert config.latency_budget_asr_ms == 500
        assert config.latency_budget_llm_first_token_ms == 300
        assert config.latency_budget_tts_ms == 400
        assert config.latency_budget_end_to_end_ms == 2000
    
    def test_system_config_composition(self):
        """Test SystemConfig combines all config sections."""
        api = APIConfig(
            whisper_api_key="key1",
            gemini_api_key="key2",
            elevenlabs_api_key="key3",
            elevenlabs_voice_id="voice1"
        )
        server = ServerConfig()
        pipeline = PipelineConfig()
        resilience = ResilienceConfig()
        observability = ObservabilityConfig()
        
        config = SystemConfig(
            api=api,
            server=server,
            pipeline=pipeline,
            resilience=resilience,
            observability=observability
        )
        
        assert config.api == api
        assert config.server == server
        assert config.pipeline == pipeline
        assert config.resilience == resilience
        assert config.observability == observability


class TestConfigLoader:
    """Test ConfigLoader functionality."""
    
    def setup_method(self):
        """Clear environment variables before each test."""
        env_vars = [
            "WHISPER_API_KEY", "GEMINI_API_KEY", "ELEVENLABS_API_KEY", "ELEVENLABS_VOICE_ID",
            "CONFIG_FILE", "WHISPER_TIMEOUT", "GEMINI_MODEL", "GEMINI_TIMEOUT",
            "ELEVENLABS_TIMEOUT", "WEBSOCKET_HOST", "WEBSOCKET_PORT", "METRICS_HOST",
            "METRICS_PORT", "AUDIO_BUFFER_MS", "TOKEN_BUFFER_SIZE", "MAX_CONVERSATION_TURNS",
            "RETRY_MAX_ATTEMPTS", "RETRY_INITIAL_DELAY_MS", "RETRY_MAX_DELAY_MS",
            "CB_FAILURE_THRESHOLD", "CB_WINDOW_SIZE", "CB_TIMEOUT_SECONDS",
            "ENABLE_RECORDING", "RECORDING_PATH", "LOG_LEVEL",
            "LATENCY_BUDGET_ASR_MS", "LATENCY_BUDGET_LLM_MS", "LATENCY_BUDGET_TTS_MS",
            "LATENCY_BUDGET_E2E_MS"
        ]
        for var in env_vars:
            os.environ.pop(var, None)
    
    def test_load_from_environment_variables(self):
        """Test loading configuration from environment variables."""
        os.environ["WHISPER_API_KEY"] = "env-whisper-key"
        os.environ["GEMINI_API_KEY"] = "env-gemini-key"
        os.environ["ELEVENLABS_API_KEY"] = "env-elevenlabs-key"
        os.environ["ELEVENLABS_VOICE_ID"] = "env-voice-id"
        os.environ["WEBSOCKET_PORT"] = "9000"
        os.environ["LOG_LEVEL"] = "DEBUG"
        
        config = ConfigLoader.load()
        
        assert config.api.whisper_api_key == "env-whisper-key"
        assert config.api.gemini_api_key == "env-gemini-key"
        assert config.api.elevenlabs_api_key == "env-elevenlabs-key"
        assert config.api.elevenlabs_voice_id == "env-voice-id"
        assert config.server.websocket_port == 9000
        assert config.observability.log_level == "DEBUG"
    
    def test_load_from_yaml_file(self):
        """Test loading configuration from YAML file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
whisper_api_key: yaml-whisper-key
gemini_api_key: yaml-gemini-key
elevenlabs_api_key: yaml-elevenlabs-key
elevenlabs_voice_id: yaml-voice-id
websocket_port: 9001
log_level: WARNING
""")
            config_file = f.name
        
        try:
            os.environ["CONFIG_FILE"] = config_file
            config = ConfigLoader.load()
            
            assert config.api.whisper_api_key == "yaml-whisper-key"
            assert config.api.gemini_api_key == "yaml-gemini-key"
            assert config.api.elevenlabs_api_key == "yaml-elevenlabs-key"
            assert config.api.elevenlabs_voice_id == "yaml-voice-id"
            assert config.server.websocket_port == 9001
            assert config.observability.log_level == "WARNING"
        finally:
            Path(config_file).unlink()
    
    def test_environment_overrides_yaml(self):
        """Test that environment variables take precedence over YAML."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
whisper_api_key: yaml-whisper-key
gemini_api_key: yaml-gemini-key
elevenlabs_api_key: yaml-elevenlabs-key
elevenlabs_voice_id: yaml-voice-id
websocket_port: 9001
""")
            config_file = f.name
        
        try:
            os.environ["CONFIG_FILE"] = config_file
            os.environ["WEBSOCKET_PORT"] = "9002"
            
            config = ConfigLoader.load()
            
            assert config.server.websocket_port == 9002  # env overrides yaml
        finally:
            Path(config_file).unlink()
    
    def test_missing_required_api_key_raises_error(self):
        """Test that missing required API keys raise ValueError."""
        with pytest.raises(ValueError, match="WHISPER_API_KEY"):
            ConfigLoader.load()
    
    def test_missing_gemini_api_key_raises_error(self):
        """Test that missing Gemini API key raises ValueError."""
        os.environ["WHISPER_API_KEY"] = "test-key"
        
        with pytest.raises(ValueError, match="GEMINI_API_KEY"):
            ConfigLoader.load()
    
    def test_missing_elevenlabs_api_key_raises_error(self):
        """Test that missing ElevenLabs API key raises ValueError."""
        os.environ["WHISPER_API_KEY"] = "test-key"
        os.environ["GEMINI_API_KEY"] = "test-key"
        
        with pytest.raises(ValueError, match="ELEVENLABS_API_KEY"):
            ConfigLoader.load()
    
    def test_missing_elevenlabs_voice_id_raises_error(self):
        """Test that missing ElevenLabs voice ID raises ValueError."""
        os.environ["WHISPER_API_KEY"] = "test-key"
        os.environ["GEMINI_API_KEY"] = "test-key"
        os.environ["ELEVENLABS_API_KEY"] = "test-key"
        
        with pytest.raises(ValueError, match="ELEVENLABS_VOICE_ID"):
            ConfigLoader.load()
    
    def test_default_values_applied(self):
        """Test that default values are applied for optional fields."""
        os.environ["WHISPER_API_KEY"] = "test-key"
        os.environ["GEMINI_API_KEY"] = "test-key"
        os.environ["ELEVENLABS_API_KEY"] = "test-key"
        os.environ["ELEVENLABS_VOICE_ID"] = "test-voice"
        
        config = ConfigLoader.load()
        
        # Check defaults
        assert config.api.whisper_timeout == 3.0
        assert config.api.gemini_model == "gemini-pro"
        assert config.server.websocket_host == "0.0.0.0"
        assert config.pipeline.audio_buffer_duration_ms == 1000
        assert config.resilience.retry_max_attempts == 3
        assert config.observability.enable_recording is False
    
    def test_type_conversion_int(self):
        """Test integer type conversion."""
        os.environ["WHISPER_API_KEY"] = "test-key"
        os.environ["GEMINI_API_KEY"] = "test-key"
        os.environ["ELEVENLABS_API_KEY"] = "test-key"
        os.environ["ELEVENLABS_VOICE_ID"] = "test-voice"
        os.environ["WEBSOCKET_PORT"] = "9999"
        
        config = ConfigLoader.load()
        
        assert isinstance(config.server.websocket_port, int)
        assert config.server.websocket_port == 9999
    
    def test_type_conversion_float(self):
        """Test float type conversion."""
        os.environ["WHISPER_API_KEY"] = "test-key"
        os.environ["GEMINI_API_KEY"] = "test-key"
        os.environ["ELEVENLABS_API_KEY"] = "test-key"
        os.environ["ELEVENLABS_VOICE_ID"] = "test-voice"
        os.environ["WHISPER_TIMEOUT"] = "5.5"
        
        config = ConfigLoader.load()
        
        assert isinstance(config.api.whisper_timeout, float)
        assert config.api.whisper_timeout == 5.5
    
    def test_type_conversion_bool_true(self):
        """Test boolean type conversion for true values."""
        os.environ["WHISPER_API_KEY"] = "test-key"
        os.environ["GEMINI_API_KEY"] = "test-key"
        os.environ["ELEVENLABS_API_KEY"] = "test-key"
        os.environ["ELEVENLABS_VOICE_ID"] = "test-voice"
        
        for true_value in ["true", "True", "TRUE", "1", "yes", "Yes", "YES"]:
            os.environ["ENABLE_RECORDING"] = true_value
            config = ConfigLoader.load()
            assert config.observability.enable_recording is True, f"Failed for value: {true_value}"
    
    def test_type_conversion_bool_false(self):
        """Test boolean type conversion for false values."""
        os.environ["WHISPER_API_KEY"] = "test-key"
        os.environ["GEMINI_API_KEY"] = "test-key"
        os.environ["ELEVENLABS_API_KEY"] = "test-key"
        os.environ["ELEVENLABS_VOICE_ID"] = "test-voice"
        
        for false_value in ["false", "False", "FALSE", "0", "no", "No", "NO"]:
            os.environ["ENABLE_RECORDING"] = false_value
            config = ConfigLoader.load()
            assert config.observability.enable_recording is False, f"Failed for value: {false_value}"
    
    def test_yaml_boolean_values(self):
        """Test that YAML boolean values are handled correctly."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
whisper_api_key: test-key
gemini_api_key: test-key
elevenlabs_api_key: test-key
elevenlabs_voice_id: test-voice
enable_recording: true
""")
            config_file = f.name
        
        try:
            os.environ["CONFIG_FILE"] = config_file
            config = ConfigLoader.load()
            
            assert config.observability.enable_recording is True
        finally:
            Path(config_file).unlink()
