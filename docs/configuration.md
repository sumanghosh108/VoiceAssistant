# Configuration Management

The Real-Time Voice Assistant uses a flexible configuration system that supports multiple sources with clear precedence rules.

## Configuration Sources

Configuration can be provided through three sources, in order of precedence:

1. **Environment Variables** (highest priority)
2. **YAML Configuration File** (medium priority)
3. **Default Values** (lowest priority)

## Quick Start

### Using Environment Variables

The simplest way to configure the system is through environment variables:

```bash
# Copy the example file
cp .env.example .env

# Edit .env and add your API keys
nano .env

# Run the application (it will automatically load .env)
python main.py
```

### Using a YAML Configuration File

For more complex deployments, you can use a YAML configuration file:

```bash
# Create a config file
cp config/example.yaml config/production.yaml

# Edit the config file
nano config/production.yaml

# Set the CONFIG_FILE environment variable
export CONFIG_FILE=config/production.yaml

# Run the application
python main.py
```

### Combining Both

Environment variables override YAML values, allowing you to:
- Store common settings in YAML
- Override specific values with environment variables
- Keep secrets in environment variables only

```bash
# Set API keys in environment (for security)
export WHISPER_API_KEY="your-key"
export GEMINI_API_KEY="your-key"
export ELEVENLABS_API_KEY="your-key"
export ELEVENLABS_VOICE_ID="your-voice-id"

# Use YAML for other settings
export CONFIG_FILE=config/production.yaml

# Run the application
python main.py
```

## Configuration Sections

### API Configuration (Required)

These settings configure external API services:

| Variable | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `WHISPER_API_KEY` | string | Yes | - | OpenAI API key for Whisper ASR |
| `WHISPER_TIMEOUT` | float | No | 3.0 | Whisper API timeout in seconds |
| `GEMINI_API_KEY` | string | Yes | - | Google AI API key for Gemini LLM |
| `GEMINI_MODEL` | string | No | "gemini-pro" | Gemini model name |
| `GEMINI_TIMEOUT` | float | No | 5.0 | Gemini API timeout in seconds |
| `ELEVENLABS_API_KEY` | string | Yes | - | ElevenLabs API key for TTS |
| `ELEVENLABS_VOICE_ID` | string | Yes | - | ElevenLabs voice ID |
| `ELEVENLABS_TIMEOUT` | float | No | 3.0 | ElevenLabs API timeout in seconds |

### Server Configuration (Optional)

These settings configure the WebSocket and metrics servers:

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `WEBSOCKET_HOST` | string | "0.0.0.0" | WebSocket server host |
| `WEBSOCKET_PORT` | int | 8000 | WebSocket server port |
| `METRICS_HOST` | string | "0.0.0.0" | Metrics/health server host |
| `METRICS_PORT` | int | 8001 | Metrics/health server port |

### Pipeline Configuration (Optional)

These settings control the event pipeline behavior:

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `AUDIO_BUFFER_MS` | int | 1000 | Audio buffer duration in milliseconds |
| `TOKEN_BUFFER_SIZE` | int | 10 | Number of tokens to buffer before TTS |
| `MAX_CONVERSATION_TURNS` | int | 10 | Maximum conversation turns to keep in context |

### Resilience Configuration (Optional)

These settings configure retry and circuit breaker behavior:

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `RETRY_MAX_ATTEMPTS` | int | 3 | Maximum retry attempts for failed API calls |
| `RETRY_INITIAL_DELAY_MS` | int | 100 | Initial retry delay in milliseconds |
| `RETRY_MAX_DELAY_MS` | int | 5000 | Maximum retry delay in milliseconds |
| `CB_FAILURE_THRESHOLD` | float | 0.5 | Circuit breaker failure threshold (50%) |
| `CB_WINDOW_SIZE` | int | 10 | Circuit breaker window size in requests |
| `CB_TIMEOUT_SECONDS` | int | 30 | Circuit breaker timeout before half-open |

### Observability Configuration (Optional)

These settings configure logging, recording, and latency budgets:

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `ENABLE_RECORDING` | bool | false | Enable session recording for debugging |
| `RECORDING_PATH` | string | "./recordings" | Path to store session recordings |
| `LOG_LEVEL` | string | "INFO" | Log level (DEBUG, INFO, WARNING, ERROR) |
| `LATENCY_BUDGET_ASR_MS` | float | 500 | ASR latency budget in milliseconds |
| `LATENCY_BUDGET_LLM_MS` | float | 300 | LLM first token latency budget in milliseconds |
| `LATENCY_BUDGET_TTS_MS` | float | 400 | TTS latency budget in milliseconds |
| `LATENCY_BUDGET_E2E_MS` | float | 2000 | End-to-end latency budget in milliseconds |

## Programmatic Usage

### Loading Configuration

```python
from src.config import ConfigLoader

# Load configuration from environment and/or YAML file
config = ConfigLoader.load()

# Access configuration values
print(f"WebSocket port: {config.server.websocket_port}")
print(f"Log level: {config.observability.log_level}")
print(f"Retry attempts: {config.resilience.retry_max_attempts}")
```

### Handling Missing Required Fields

```python
from src.config import ConfigLoader

try:
    config = ConfigLoader.load()
except ValueError as e:
    print(f"Configuration error: {e}")
    # Example output: "Required configuration WHISPER_API_KEY not found in environment or config file"
```

### Creating Configuration Programmatically

```python
from src.config import (
    APIConfig, ServerConfig, PipelineConfig,
    ResilienceConfig, ObservabilityConfig, SystemConfig
)

# Create configuration objects directly
api_config = APIConfig(
    whisper_api_key="your-key",
    gemini_api_key="your-key",
    elevenlabs_api_key="your-key",
    elevenlabs_voice_id="your-voice-id"
)

server_config = ServerConfig(
    websocket_port=9000
)

# Combine into system config
config = SystemConfig(
    api=api_config,
    server=server_config,
    pipeline=PipelineConfig(),
    resilience=ResilienceConfig(),
    observability=ObservabilityConfig()
)
```

## YAML Configuration Format

Example YAML configuration file:

```yaml
# API Configuration
whisper_api_key: "your-whisper-key"
gemini_api_key: "your-gemini-key"
elevenlabs_api_key: "your-elevenlabs-key"
elevenlabs_voice_id: "your-voice-id"

whisper_timeout: 3.0
gemini_model: "gemini-pro"
gemini_timeout: 5.0
elevenlabs_timeout: 3.0

# Server Configuration
websocket_host: "0.0.0.0"
websocket_port: 8000
metrics_host: "0.0.0.0"
metrics_port: 8001

# Pipeline Configuration
audio_buffer_ms: 1000
token_buffer_size: 10
max_conversation_turns: 10

# Resilience Configuration
retry_max_attempts: 3
retry_initial_delay_ms: 100
retry_max_delay_ms: 5000
cb_failure_threshold: 0.5
cb_window_size: 10
cb_timeout_seconds: 30

# Observability Configuration
enable_recording: false
recording_path: "./recordings"
log_level: "INFO"
latency_budget_asr_ms: 500
latency_budget_llm_ms: 300
latency_budget_tts_ms: 400
latency_budget_e2e_ms: 2000
```

## Best Practices

### Security

1. **Never commit API keys to version control**
   - Use `.env` files (already in `.gitignore`)
   - Use environment variables in production
   - Use secrets management in cloud deployments

2. **Use YAML for non-sensitive settings**
   - Store timeouts, ports, and other non-secret values in YAML
   - Keep API keys in environment variables only

### Environment-Specific Configuration

The system includes pre-configured YAML files optimized for different environments:

```
config/
  ├── example.yaml       # Generic example with all options
  ├── development.yaml   # Local development with verbose logging
  ├── testing.yaml       # Automated testing with fast timeouts
  ├── staging.yaml       # Pre-production testing environment
  └── production.yaml    # Production deployment
```

#### Development Environment

Optimized for local development with:
- Verbose DEBUG logging for troubleshooting
- Session recording enabled for debugging
- Relaxed timeouts (10-15s) for debugging with breakpoints
- Smaller buffers for faster iteration
- Lenient circuit breaker settings
- Localhost-only binding for security

```bash
export CONFIG_FILE=config/development.yaml
python src/main.py
```

#### Testing Environment

Optimized for automated testing with:
- Fast timeouts (1-2s) for quick test execution
- Minimal buffers and retry attempts
- Relaxed latency budgets to avoid flaky tests
- Recording enabled for test debugging
- Lenient circuit breaker to test failure scenarios

```bash
export CONFIG_FILE=config/testing.yaml
pytest
```

#### Staging Environment

Mirrors production with enhanced observability:
- Production-like timeouts and settings
- DEBUG logging for pre-production validation
- Recording enabled for issue investigation
- Same latency budgets as production
- Useful for load testing and integration testing

```bash
export CONFIG_FILE=config/staging.yaml
python src/main.py
```

#### Production Environment

Optimized for reliability and performance:
- INFO logging to reduce overhead
- Recording disabled for performance
- Strict timeouts and latency budgets
- Production-tuned circuit breaker
- Binds to all interfaces (0.0.0.0)

```bash
export CONFIG_FILE=config/production.yaml
python src/main.py
```

#### Environment Comparison

| Setting | Development | Testing | Staging | Production |
|---------|-------------|---------|---------|------------|
| **Log Level** | DEBUG | DEBUG | DEBUG | INFO |
| **Recording** | Enabled | Enabled | Enabled | Disabled |
| **Whisper Timeout** | 10s | 1s | 3s | 3s |
| **Gemini Timeout** | 15s | 2s | 5s | 5s |
| **Retry Attempts** | 5 | 1 | 3 | 3 |
| **Circuit Breaker Threshold** | 80% | 90% | 50% | 50% |
| **Audio Buffer** | 500ms | 100ms | 1000ms | 1000ms |
| **Latency Budget (E2E)** | 4000ms | 10000ms | 2000ms | 2000ms |
| **Host Binding** | 127.0.0.1 | 127.0.0.1 | 0.0.0.0 | 0.0.0.0 |

### Validation

The configuration system validates all required fields at startup:

- Missing required API keys will raise `ValueError` with a specific message
- Invalid types will be caught during type conversion
- The application will exit with a clear error message if configuration is invalid

This fail-fast approach ensures configuration issues are caught immediately rather than during runtime.

## Troubleshooting

### "Required configuration X not found"

This error means a required API key is missing. Check:
1. Is the environment variable set? (`echo $WHISPER_API_KEY`)
2. Is it in your `.env` file?
3. Is it in your YAML config file (if using `CONFIG_FILE`)?

### Type conversion errors

If you see errors about invalid types:
- Check that numeric values don't have quotes in YAML
- Check that boolean values use `true`/`false` (not `True`/`False`) in YAML
- Environment variables are always strings and will be converted automatically

### Configuration not loading from YAML

Check:
1. Is `CONFIG_FILE` environment variable set?
2. Does the file exist at that path?
3. Is the YAML syntax valid? (use a YAML validator)
4. Are the keys lowercase in the YAML file?

## Testing

The configuration system includes comprehensive unit tests:

```bash
# Run configuration tests
pytest tests/test_config.py -v

# Test specific functionality
pytest tests/test_config.py::TestConfigLoader::test_load_from_environment_variables -v
```
