# Running the Real-Time Voice Assistant

This guide explains how to start and run the real-time voice assistant application.

## Prerequisites

1. Python 3.11 or higher installed
2. All dependencies installed: `pip install -r requirements.txt`
3. API keys for:
   - OpenAI (for Whisper ASR)
   - Google (for Gemini LLM)
   - ElevenLabs (for TTS)

## Configuration

### Option 1: Environment Variables

Set the required environment variables:

```bash
export WHISPER_API_KEY="your-openai-api-key"
export GEMINI_API_KEY="your-google-api-key"
export ELEVENLABS_API_KEY="your-elevenlabs-api-key"
export ELEVENLABS_VOICE_ID="your-voice-id"
```

### Option 2: .env File

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and fill in your API keys:
   ```bash
   WHISPER_API_KEY=your-openai-api-key
   GEMINI_API_KEY=your-google-api-key
   ELEVENLABS_API_KEY=your-elevenlabs-api-key
   ELEVENLABS_VOICE_ID=your-voice-id
   ```

3. Load the environment variables:
   ```bash
   # On Linux/Mac
   source .env
   
   # On Windows (PowerShell)
   Get-Content .env | ForEach-Object { $var = $_.Split('='); [Environment]::SetEnvironmentVariable($var[0], $var[1]) }
   ```

### Option 3: YAML Configuration File

1. Create a `config.yaml` file:
   ```yaml
   whisper_api_key: your-openai-api-key
   gemini_api_key: your-google-api-key
   elevenlabs_api_key: your-elevenlabs-api-key
   elevenlabs_voice_id: your-voice-id
   
   # Optional settings
   log_level: INFO
   enable_recording: false
   websocket_port: 8000
   metrics_port: 8001
   ```

2. Set the CONFIG_FILE environment variable:
   ```bash
   export CONFIG_FILE=config.yaml
   ```

## Starting the Application

Run the main application:

```bash
python -m src.main
```

Or use the Python module syntax:

```bash
python src/main.py
```

## Verifying the Application is Running

Once started, you should see log output indicating the servers have started:

```json
{"timestamp": "2024-01-15T10:30:00.000Z", "level": "INFO", "message": "Starting Real-Time Voice Assistant", ...}
{"timestamp": "2024-01-15T10:30:00.100Z", "level": "INFO", "message": "Circuit breakers initialized", ...}
{"timestamp": "2024-01-15T10:30:00.200Z", "level": "INFO", "message": "Services initialized", ...}
{"timestamp": "2024-01-15T10:30:00.300Z", "level": "INFO", "message": "HTTP server started with metrics and health endpoints", ...}
{"timestamp": "2024-01-15T10:30:00.400Z", "level": "INFO", "message": "WebSocket server started", ...}
{"timestamp": "2024-01-15T10:30:00.500Z", "level": "INFO", "message": "Real-Time Voice Assistant started successfully", ...}
```

### Check Health Status

Verify the application is healthy:

```bash
curl http://localhost:8001/health
```

Expected response:
```json
{
  "healthy": true,
  "critical_healthy": true,
  "components": {
    "asr": true,
    "llm": true,
    "tts": true,
    "latency_tracker": true,
    "recorder": true,
    "dashboard": true
  },
  "circuit_breakers": {
    "asr": {"state": "closed", ...},
    "llm": {"state": "closed", ...},
    "tts": {"state": "closed", ...}
  }
}
```

### View Metrics Dashboard

Open your browser and navigate to:

```
http://localhost:8001/dashboard
```

This displays real-time latency metrics for all pipeline stages.

### Access Metrics API

Get JSON metrics data:

```bash
curl http://localhost:8001/metrics
```

## Connecting Clients

Clients can connect to the WebSocket server at:

```
ws://localhost:8000
```

See the [WebSocket Protocol Documentation](websocket_server.md) for details on the message format.

## Stopping the Application

Press `Ctrl+C` to gracefully shut down the application. The system will:

1. Stop accepting new connections
2. Complete in-flight requests (with timeout)
3. Save any active session recordings
4. Clean up all resources
5. Exit

Expected shutdown log output:

```json
{"timestamp": "2024-01-15T11:00:00.000Z", "level": "INFO", "message": "Received shutdown signal", ...}
{"timestamp": "2024-01-15T11:00:00.100Z", "level": "INFO", "message": "Shutting down gracefully...", ...}
{"timestamp": "2024-01-15T11:00:05.000Z", "level": "INFO", "message": "Shutdown complete", ...}
```

## Troubleshooting

### Configuration Errors

If you see an error like:
```
Configuration error: Required configuration WHISPER_API_KEY not found in environment or config file
```

Make sure you have set all required API keys in your environment or configuration file.

### Port Already in Use

If you see an error about ports already in use:
```
OSError: [Errno 48] Address already in use
```

Either:
1. Stop the process using that port
2. Change the port in your configuration:
   ```bash
   export WEBSOCKET_PORT=8080
   export METRICS_PORT=8081
   ```

### API Connection Issues

If services fail to connect to external APIs, check:
1. Your API keys are valid
2. You have network connectivity
3. The API services are not experiencing outages
4. Check circuit breaker states in the health endpoint

### High Latency

If you're experiencing high latency:
1. Check the metrics dashboard at `http://localhost:8001/dashboard`
2. Review the latency breakdown by stage
3. Check if any circuit breakers are open
4. Review the logs for timeout or retry messages

## Advanced Configuration

### Enable Session Recording

For debugging, enable session recording:

```bash
export ENABLE_RECORDING=true
export RECORDING_PATH=./recordings
```

Recordings will be saved to the specified directory and can be replayed using the replay system.

### Adjust Latency Budgets

Customize latency thresholds:

```bash
export LATENCY_BUDGET_ASR_MS=500
export LATENCY_BUDGET_LLM_MS=300
export LATENCY_BUDGET_TTS_MS=400
export LATENCY_BUDGET_E2E_MS=2000
```

### Configure Circuit Breakers

Adjust circuit breaker behavior:

```bash
export CB_FAILURE_THRESHOLD=0.5  # Open at 50% failure rate
export CB_WINDOW_SIZE=10         # Over 10 requests
export CB_TIMEOUT_SECONDS=30     # Stay open for 30 seconds
```

### Adjust Log Level

Change logging verbosity:

```bash
export LOG_LEVEL=DEBUG  # Options: DEBUG, INFO, WARNING, ERROR
```

## Production Deployment

For production deployment, see:
- [Docker Deployment Guide](../Dockerfile)
- [Kubernetes Configuration](../k8s/)
- [Monitoring and Observability](./metrics_dashboard.md)
- [Health Check Integration](./health_system.md)
