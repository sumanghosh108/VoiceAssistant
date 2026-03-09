# Troubleshooting Guide

This guide helps you diagnose and resolve common issues with the Real-Time Voice Assistant system.

## Table of Contents

1. [Common Issues and Solutions](#common-issues-and-solutions)
2. [Latency Debugging](#latency-debugging)
3. [Session Replay for Debugging](#session-replay-for-debugging)
4. [Circuit Breaker Behavior](#circuit-breaker-behavior)
5. [Health Check Diagnostics](#health-check-diagnostics)
6. [Configuration Issues](#configuration-issues)
7. [API Integration Issues](#api-integration-issues)

---

## Common Issues and Solutions

### Application Won't Start

#### Symptom
Application exits immediately with "Configuration error" message.

#### Diagnosis
```bash
python src/main.py
# Output: Configuration error: Required configuration WHISPER_API_KEY not found
```

#### Solution
1. Check that all required API keys are set:
   ```bash
   echo $WHISPER_API_KEY
   echo $GEMINI_API_KEY
   echo $ELEVENLABS_API_KEY
   echo $ELEVENLABS_VOICE_ID
   ```

2. If using `.env` file, ensure it exists and contains all keys:
   ```bash
   cat .env
   ```

3. If using YAML config, verify the file path and contents:
   ```bash
   echo $CONFIG_FILE
   cat $CONFIG_FILE
   ```

See [Configuration Documentation](configuration.md) for complete setup instructions.

---

### WebSocket Connection Refused

#### Symptom
Client cannot connect to WebSocket server.

#### Diagnosis
```bash
# Check if server is listening
curl http://localhost:8001/health/live

# Check WebSocket port
netstat -an | grep 8000
```

#### Solution
1. **Port already in use**: Change `WEBSOCKET_PORT` in configuration
2. **Firewall blocking**: Allow port 8000 through firewall
3. **Wrong host binding**: Check `WEBSOCKET_HOST` setting
   - Use `0.0.0.0` to accept connections from any interface
   - Use `127.0.0.1` for localhost-only (development)

---

### Audio Not Processing

#### Symptom
Client sends audio but receives no response.

#### Diagnosis
1. Check health endpoints:
   ```bash
   curl http://localhost:8001/health
   ```

2. Check circuit breaker states:
   ```bash
   curl http://localhost:8001/health | jq '.circuit_breakers'
   ```

3. Check logs for errors:
   ```bash
   # Look for error events in structured logs
   grep '"level":"ERROR"' logs.json
   ```

#### Solution

**If ASR circuit is open:**
- Whisper API may be down or rate-limited
- Check API key validity
- Wait for circuit breaker to attempt recovery (30 seconds)

**If LLM circuit is open:**
- Gemini API may be down or rate-limited
- Check API key validity and quota
- Wait for circuit breaker recovery

**If TTS circuit is open:**
- ElevenLabs API may be down or rate-limited
- Check API key and voice ID
- Verify account has sufficient credits

---

### High Latency / Slow Responses

#### Symptom
Responses take longer than expected (>2 seconds end-to-end).

#### Diagnosis
1. Check metrics dashboard:
   ```bash
   # Open in browser
   http://localhost:8001/dashboard
   ```

2. Query metrics API:
   ```bash
   curl http://localhost:8001/metrics | jq
   ```

3. Look for latency budget violations:
   ```bash
   curl http://localhost:8001/metrics | jq '.[] | select(.violation_rate > 10)'
   ```

#### Solution
See [Latency Debugging](#latency-debugging) section below for detailed analysis.

---

### Session Recording Not Working

#### Symptom
No recordings appear in the recordings directory.

#### Diagnosis
```bash
# Check if recording is enabled
echo $ENABLE_RECORDING

# Check recordings directory
ls -la recordings/
```

#### Solution
1. Enable recording in configuration:
   ```bash
   export ENABLE_RECORDING=true
   ```

2. Ensure recordings directory is writable:
   ```bash
   mkdir -p recordings
   chmod 755 recordings
   ```

3. Check disk space:
   ```bash
   df -h recordings/
   ```

4. Check logs for recording errors:
   ```bash
   grep '"component":"recorder"' logs.json | grep ERROR
   ```

---

### Memory Usage Growing Over Time

#### Symptom
Application memory usage increases continuously.

#### Diagnosis
```bash
# Monitor memory usage
ps aux | grep python

# Check active sessions
curl http://localhost:8001/health | jq '.active_sessions'
```

#### Solution
1. **Sessions not cleaning up**: Check for WebSocket connection leaks
   - Ensure clients properly disconnect
   - Check session cleanup timeout (default 5 seconds)

2. **Metrics accumulation**: Metrics are limited to last 1000 measurements per stage
   - This is normal and bounded

3. **Conversation context**: Limited to 10 turns per session by default
   - Adjust `MAX_CONVERSATION_TURNS` if needed

---

## Latency Debugging

The metrics dashboard is your primary tool for diagnosing latency issues.

### Understanding Latency Metrics

The system tracks latency across six pipeline stages:

| Stage | Description | Budget | What It Measures |
|-------|-------------|--------|------------------|
| `asr_latency` | Speech recognition | 500ms | Audio receipt → Transcript emission |
| `llm_first_token_latency` | LLM response start | 300ms | Transcript → First LLM token |
| `llm_generation_latency` | LLM completion | N/A | First token → Last token |
| `tts_latency` | Speech synthesis | 400ms | Token receipt → Audio emission |
| `end_to_end_latency` | Total pipeline | 2000ms | Audio input → Audio output |
| `websocket_send_latency` | Network transmission | N/A | Audio ready → Client received |

### Using the Metrics Dashboard

1. **Open the dashboard**:
   ```bash
   # In your browser
   http://localhost:8001/dashboard
   ```

2. **Identify bottlenecks**:
   - Look for stages with high P95/P99 latencies
   - Red text indicates violation rate > 10%
   - Green text indicates acceptable performance

3. **Example dashboard output**:
   ```
   ASR Latency
   Mean: 285ms | P95: 450ms | P99: 490ms
   Violations: 5.0% ✓
   
   LLM First Token Latency
   Mean: 450ms | P95: 650ms | P99: 800ms
   Violations: 25.0% ⚠️  (EXCEEDS BUDGET)
   ```

### Diagnosing Specific Latency Issues

#### High ASR Latency (>500ms)

**Possible Causes:**
- Whisper API slow or overloaded
- Network latency to OpenAI servers
- Audio buffer too large

**Solutions:**
1. Check Whisper API status: https://status.openai.com
2. Reduce audio buffer size:
   ```bash
   export AUDIO_BUFFER_MS=500  # Default is 1000ms
   ```
3. Consider using Whisper's faster model (if available)
4. Check network latency:
   ```bash
   ping api.openai.com
   ```

#### High LLM First Token Latency (>300ms)

**Possible Causes:**
- Gemini API slow to respond
- Large conversation context
- Network latency to Google AI servers

**Solutions:**
1. Check Gemini API status
2. Reduce conversation context:
   ```bash
   export MAX_CONVERSATION_TURNS=5  # Default is 10
   ```
3. Use a faster Gemini model (if available):
   ```bash
   export GEMINI_MODEL="gemini-pro"  # Check for faster variants
   ```
4. Check network latency:
   ```bash
   ping generativelanguage.googleapis.com
   ```

#### High TTS Latency (>400ms)

**Possible Causes:**
- ElevenLabs API slow or overloaded
- Token buffer too large
- Network latency to ElevenLabs servers

**Solutions:**
1. Check ElevenLabs API status: https://status.elevenlabs.io
2. Reduce token buffer size:
   ```bash
   export TOKEN_BUFFER_SIZE=5  # Default is 10
   ```
3. Consider using a faster voice model
4. Check network latency:
   ```bash
   ping api.elevenlabs.io
   ```

#### High End-to-End Latency (>2000ms)

**Possible Causes:**
- Cumulative delays across all stages
- Network transmission delays
- Client-side processing delays

**Solutions:**
1. Identify the slowest stage using the dashboard
2. Focus optimization efforts on the bottleneck
3. Check WebSocket send latency for network issues
4. Verify client is processing audio quickly

### Querying Metrics Programmatically

```bash
# Get all metrics as JSON
curl http://localhost:8001/metrics

# Get specific stage statistics
curl http://localhost:8001/metrics | jq '.asr_latency'

# Find stages exceeding budget
curl http://localhost:8001/metrics | jq 'to_entries[] | select(.value.violation_rate > 10)'

# Get P99 latencies for all stages
curl http://localhost:8001/metrics | jq 'to_entries[] | {stage: .key, p99: .value.p99}'
```

### Adjusting Latency Budgets

If your use case has different latency requirements:

```bash
# Relax budgets for non-real-time applications
export LATENCY_BUDGET_ASR_MS=1000
export LATENCY_BUDGET_LLM_MS=500
export LATENCY_BUDGET_TTS_MS=800
export LATENCY_BUDGET_E2E_MS=3000

# Tighten budgets for ultra-low-latency applications
export LATENCY_BUDGET_ASR_MS=300
export LATENCY_BUDGET_LLM_MS=200
export LATENCY_BUDGET_TTS_MS=300
export LATENCY_BUDGET_E2E_MS=1000
```

---

## Session Replay for Debugging

Session replay allows you to reproduce issues by replaying recorded sessions through the pipeline.

### Enabling Session Recording

1. **Enable recording in configuration**:
   ```bash
   export ENABLE_RECORDING=true
   export RECORDING_PATH="./recordings"
   ```

2. **Restart the application**:
   ```bash
   python src/main.py
   ```

3. **Recordings are created automatically** for each session.

### Listing Available Recordings

```python
from src.replay_system import ReplaySystem
from pathlib import Path

# Initialize replay system
replay_system = ReplaySystem(
    asr_service=asr_service,
    llm_service=llm_service,
    tts_service=tts_service,
    storage_path=Path("./recordings")
)

# List all recordings
recordings = await replay_system.list_recordings()

for rec in recordings:
    print(f"Session: {rec['session_id']}")
    print(f"  Duration: {rec['duration_seconds']}s")
    print(f"  Events: {rec['event_count']}")
    print(f"  Errors: {rec['error_count']}")
    print(f"  Start: {rec['start_time']}")
```

### Replaying a Session

```python
# Replay at normal speed with comparison
result = await replay_system.replay(
    session_id="abc-123-def",
    speed=1.0,      # 1.0 = real-time
    compare=True    # Compare with recorded events
)

# Check results
print(f"Replay duration: {result['replay_duration_seconds']}s")
print(f"Recorded events: {result['recorded_event_count']}")
print(f"Replayed events: {result['replayed_event_count']}")

# Check for discrepancies
if result['discrepancies']:
    print(f"Found {len(result['discrepancies'])} discrepancies:")
    for disc in result['discrepancies']:
        print(f"  Type: {disc['type']}")
        print(f"  Details: {disc}")
else:
    print("✓ Replay matches recording perfectly")
```

### Common Replay Use Cases

#### Reproducing Intermittent Bugs

When a bug occurs sporadically:

```python
# Record the problematic session (automatic)
# Then replay multiple times to check consistency

for i in range(10):
    result = await replay_system.replay(
        session_id="problematic-session",
        speed=2.0,  # 2x speed for faster iteration
        compare=True
    )
    
    if result['discrepancies']:
        print(f"Run {i}: Found discrepancies - bug reproduced!")
        break
```

#### Debugging Transcription Issues

When ASR produces incorrect transcripts:

```python
# Replay the session
result = await replay_system.replay(
    session_id="bad-transcript-session",
    speed=1.0,
    compare=True
)

# Check for transcript mismatches
transcript_issues = [
    d for d in result['discrepancies']
    if d['type'] == 'transcript_mismatch'
]

for issue in transcript_issues:
    print(f"Expected: {issue['recorded']}")
    print(f"Got: {issue['replayed']}")
```

#### Performance Regression Testing

Before and after code changes:

```python
# Record sessions with old code
# Deploy new code
# Replay and compare

result = await replay_system.replay(
    session_id="baseline-session",
    speed=1.0,
    compare=True
)

if result['discrepancies']:
    print("⚠️ Behavior changed - review discrepancies")
    for disc in result['discrepancies']:
        print(f"  {disc['type']}: {disc}")
else:
    print("✓ Behavior unchanged")
```

#### Fast-Forward Debugging

Replay at high speed to quickly reach the problematic part:

```python
# Replay at 10x speed to skip to the issue
result = await replay_system.replay(
    session_id="long-session",
    speed=10.0,
    compare=False  # Skip comparison for speed
)
```

### Understanding Discrepancy Types

#### Count Mismatch
Different number of events between recording and replay.

```python
{
    "type": "count_mismatch",
    "event_type": "transcript",
    "recorded_count": 5,
    "replayed_count": 4
}
```

**Possible Causes:**
- Non-deterministic API behavior
- Timeout differences
- Circuit breaker state differences

#### Transcript Mismatch
ASR produced different text.

```python
{
    "type": "transcript_mismatch",
    "recorded": "Hello world",
    "replayed": "Hello there"
}
```

**Possible Causes:**
- Whisper API non-determinism
- Different model versions
- Audio encoding differences

#### Token Sequence Mismatch
LLM generated different tokens.

```python
{
    "type": "token_sequence_mismatch",
    "recorded": "Hello world",
    "replayed": "Hello there"
}
```

**Possible Causes:**
- Gemini API non-determinism (temperature > 0)
- Different model versions
- Context differences

### Replay Limitations

**Non-Deterministic APIs:**
- External APIs (Whisper, Gemini, ElevenLabs) may produce different results
- Use discrepancy analysis to identify significant differences
- Minor variations are expected

**Network Conditions:**
- Replay uses recorded audio but makes real API calls
- Network latency may differ from original session
- Timeouts may trigger differently

**State Dependencies:**
- Circuit breaker states may differ
- System load may differ
- External service availability may differ

---

## Circuit Breaker Behavior

Circuit breakers protect the system from cascading failures by monitoring API health and temporarily blocking calls to failing services.

### Circuit Breaker States

```
┌─────────┐
│ CLOSED  │  Normal operation - all calls pass through
└────┬────┘
     │ Failure rate > 50% over 10 requests
     ▼
┌─────────┐
│  OPEN   │  Service failing - calls rejected immediately
└────┬────┘
     │ After 30 seconds
     ▼
┌─────────┐
│HALF_OPEN│  Testing recovery - allow one test request
└────┬────┘
     │ Test succeeds          │ Test fails
     ▼                        ▼
┌─────────┐              ┌─────────┐
│ CLOSED  │              │  OPEN   │
└─────────┘              └─────────┘
```

### Checking Circuit Breaker Status

```bash
# Check all circuit breaker states
curl http://localhost:8001/health | jq '.circuit_breakers'

# Example output:
{
  "asr": {
    "state": "closed",
    "failures": 2,
    "successes": 18,
    "failure_rate": 0.1
  },
  "llm": {
    "state": "open",
    "failures": 6,
    "successes": 4,
    "failure_rate": 0.6,
    "opened_at": "2024-01-15T10:30:45.123Z"
  },
  "tts": {
    "state": "half_open",
    "failures": 5,
    "successes": 5,
    "failure_rate": 0.5
  }
}
```

### Understanding Circuit States

#### CLOSED (Normal Operation)

**Meaning:** Service is healthy, all requests pass through.

**Behavior:**
- All API calls are attempted
- Failures are tracked but don't block requests
- If failure rate exceeds 50% over 10 requests, transitions to OPEN

**Action Required:** None - system operating normally.

#### OPEN (Service Failing)

**Meaning:** Service is experiencing high failure rate, calls are blocked.

**Behavior:**
- All API calls are rejected immediately without attempting
- Clients receive error responses
- After 30 seconds, transitions to HALF_OPEN to test recovery

**Symptoms:**
- Audio not being transcribed (ASR circuit open)
- No LLM responses (LLM circuit open)
- No synthesized audio (TTS circuit open)

**Action Required:**
1. Check external service status
2. Verify API keys and quotas
3. Check network connectivity
4. Wait for automatic recovery attempt (30 seconds)

#### HALF_OPEN (Testing Recovery)

**Meaning:** Circuit is testing if service has recovered.

**Behavior:**
- One test request is allowed through
- If test succeeds: transitions to CLOSED (recovered)
- If test fails: transitions back to OPEN for another 30 seconds

**Action Required:** Wait for test result (usually <5 seconds).

### Common Circuit Breaker Scenarios

#### Scenario 1: API Rate Limiting

**Symptoms:**
```bash
curl http://localhost:8001/health | jq '.circuit_breakers.asr'
{
  "state": "open",
  "failures": 8,
  "successes": 2,
  "failure_rate": 0.8
}
```

**Diagnosis:**
- Check logs for rate limit errors:
  ```bash
  grep '"error_type":"api_error"' logs.json | grep rate
  ```

**Solution:**
1. Wait for circuit to attempt recovery (30 seconds)
2. Reduce request rate if possible
3. Upgrade API plan for higher limits
4. Adjust circuit breaker threshold if rate limits are expected:
   ```bash
   export CB_FAILURE_THRESHOLD=0.7  # Allow 70% failure rate
   ```

#### Scenario 2: Network Outage

**Symptoms:**
- All circuits open simultaneously
- Health endpoint shows all services degraded

**Diagnosis:**
```bash
# Check network connectivity
ping api.openai.com
ping generativelanguage.googleapis.com
ping api.elevenlabs.io
```

**Solution:**
1. Verify network connectivity
2. Check firewall rules
3. Wait for network recovery
4. Circuits will automatically recover when network is restored

#### Scenario 3: Invalid API Key

**Symptoms:**
- Circuit opens immediately on startup
- All requests fail with authentication errors

**Diagnosis:**
```bash
# Check logs for auth errors
grep '"error_type":"api_error"' logs.json | grep -i auth
```

**Solution:**
1. Verify API keys are correct:
   ```bash
   echo $WHISPER_API_KEY
   echo $GEMINI_API_KEY
   echo $ELEVENLABS_API_KEY
   ```
2. Check API key validity on provider dashboards
3. Update configuration with correct keys
4. Restart application

### Manually Resetting Circuit Breakers

Circuit breakers reset automatically, but you can force a reset by restarting the application:

```bash
# Graceful restart
pkill -SIGTERM python
python src/main.py
```

### Adjusting Circuit Breaker Settings

If your use case requires different thresholds:

```bash
# More lenient (allow more failures before opening)
export CB_FAILURE_THRESHOLD=0.7  # 70% failure rate
export CB_WINDOW_SIZE=20         # Over 20 requests
export CB_TIMEOUT_SECONDS=60     # Wait 60s before testing

# More strict (open faster on failures)
export CB_FAILURE_THRESHOLD=0.3  # 30% failure rate
export CB_WINDOW_SIZE=5          # Over 5 requests
export CB_TIMEOUT_SECONDS=15     # Wait 15s before testing
```

### Monitoring Circuit Breaker Events

Circuit breaker state transitions are logged:

```bash
# Watch for circuit breaker events
tail -f logs.json | grep circuit_breaker

# Example log entry:
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "WARNING",
  "message": "Circuit breaker asr transitioned from closed to open",
  "component": "circuit_breaker",
  "circuit_name": "asr",
  "old_state": "closed",
  "new_state": "open",
  "failures": 6,
  "successes": 4,
  "failure_rate": 0.6
}
```

---

## Health Check Diagnostics

The system provides three health check endpoints for monitoring.

### Health Endpoints

#### `/health` - Detailed Status

Returns comprehensive health information:

```bash
curl http://localhost:8001/health | jq
```

Response:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:45.123Z",
  "system_health": {
    "healthy": true,
    "critical_healthy": true,
    "components": {
      "asr": true,
      "llm": true,
      "tts": true,
      "latency_tracker": true,
      "recorder": true,
      "dashboard": true
    }
  },
  "circuit_breakers": {
    "asr": {"state": "closed", "failures": 0, "successes": 10},
    "llm": {"state": "closed", "failures": 1, "successes": 9},
    "tts": {"state": "closed", "failures": 0, "successes": 10}
  }
}
```

#### `/health/ready` - Readiness Probe

Returns 200 if system is ready to accept connections, 503 otherwise:

```bash
curl -i http://localhost:8001/health/ready
```

**Returns 200 when:**
- All critical components (ASR, LLM, TTS) are healthy
- All circuit breakers are CLOSED or HALF_OPEN

**Returns 503 when:**
- Any critical component is degraded
- Any circuit breaker is OPEN

**Use for:** Kubernetes readiness probes, load balancer health checks

#### `/health/live` - Liveness Probe

Returns 200 if the process is alive:

```bash
curl -i http://localhost:8001/health/live
```

Always returns 200 unless the process is completely unresponsive.

**Use for:** Kubernetes liveness probes, process monitoring

### Interpreting Health Status

#### Fully Healthy

```json
{
  "status": "healthy",
  "system_health": {
    "healthy": true,
    "critical_healthy": true
  }
}
```

**Meaning:** All components operational, system ready for production traffic.

#### Degraded (Non-Critical)

```json
{
  "status": "degraded",
  "system_health": {
    "healthy": false,
    "critical_healthy": true,
    "components": {
      "recorder": false
    },
    "degraded_since": {
      "recorder": "2024-01-15T10:30:45.123Z"
    }
  }
}
```

**Meaning:** Core functionality works, but observability features degraded.

**Action:** Investigate non-critical component failure, but system can continue operating.

#### Degraded (Critical)

```json
{
  "status": "unhealthy",
  "system_health": {
    "healthy": false,
    "critical_healthy": false,
    "components": {
      "asr": false
    }
  },
  "circuit_breakers": {
    "asr": {"state": "open"}
  }
}
```

**Meaning:** Core functionality impaired, system cannot process requests.

**Action:** Immediate investigation required. Check circuit breaker status and external service health.

---

## Configuration Issues

### Missing Required Configuration

**Error:**
```
Configuration error: Required configuration WHISPER_API_KEY not found
```

**Solution:**
1. Set environment variable:
   ```bash
   export WHISPER_API_KEY="your-key-here"
   ```

2. Or add to `.env` file:
   ```bash
   echo "WHISPER_API_KEY=your-key-here" >> .env
   ```

3. Or add to YAML config file:
   ```yaml
   whisper_api_key: "your-key-here"
   ```

### Configuration File Not Found

**Error:**
```
Configuration error: Config file not found: config/production.yaml
```

**Solution:**
1. Check file path:
   ```bash
   ls -la config/production.yaml
   ```

2. Use absolute path:
   ```bash
   export CONFIG_FILE=/full/path/to/config.yaml
   ```

3. Or use a different config file:
   ```bash
   export CONFIG_FILE=config/development.yaml
   ```

### Invalid Configuration Values

**Error:**
```
Configuration error: Invalid value for WEBSOCKET_PORT: 'abc'
```

**Solution:**
1. Check value type (should be integer):
   ```bash
   export WEBSOCKET_PORT=8000
   ```

2. In YAML, don't use quotes for numbers:
   ```yaml
   websocket_port: 8000  # Correct
   websocket_port: "8000"  # Wrong
   ```

---

## API Integration Issues

### Whisper API Errors

**Symptom:** ASR not producing transcripts

**Diagnosis:**
```bash
# Check ASR circuit breaker
curl http://localhost:8001/health | jq '.circuit_breakers.asr'

# Check logs
grep '"component":"asr"' logs.json | grep ERROR
```

**Common Issues:**

1. **Invalid API Key:**
   - Verify key at https://platform.openai.com/api-keys
   - Update `WHISPER_API_KEY`

2. **Rate Limiting:**
   - Upgrade OpenAI plan
   - Reduce request rate
   - Increase `AUDIO_BUFFER_MS` to send fewer requests

3. **Timeout:**
   - Increase `WHISPER_TIMEOUT` (default 3s)
   - Check network latency

### Gemini API Errors

**Symptom:** No LLM responses

**Diagnosis:**
```bash
# Check LLM circuit breaker
curl http://localhost:8001/health | jq '.circuit_breakers.llm'

# Check logs
grep '"component":"llm"' logs.json | grep ERROR
```

**Common Issues:**

1. **Invalid API Key:**
   - Verify key at https://makersuite.google.com/app/apikey
   - Update `GEMINI_API_KEY`

2. **Model Not Available:**
   - Check model name: `GEMINI_MODEL`
   - Try `gemini-pro` (default)

3. **Quota Exceeded:**
   - Check quota at Google AI Studio
   - Wait for quota reset
   - Upgrade plan

### ElevenLabs API Errors

**Symptom:** No synthesized audio

**Diagnosis:**
```bash
# Check TTS circuit breaker
curl http://localhost:8001/health | jq '.circuit_breakers.tts'

# Check logs
grep '"component":"tts"' logs.json | grep ERROR
```

**Common Issues:**

1. **Invalid API Key or Voice ID:**
   - Verify at https://elevenlabs.io/app/settings
   - Update `ELEVENLABS_API_KEY` and `ELEVENLABS_VOICE_ID`

2. **Insufficient Credits:**
   - Check account balance
   - Add credits or upgrade plan

3. **Voice ID Not Found:**
   - List available voices in ElevenLabs dashboard
   - Update `ELEVENLABS_VOICE_ID`

---

## Getting Help

If you're still experiencing issues after following this guide:

1. **Check logs** for detailed error messages:
   ```bash
   tail -f logs.json | jq
   ```

2. **Enable debug logging**:
   ```bash
   export LOG_LEVEL=DEBUG
   python src/main.py
   ```

3. **Record a problematic session** for analysis:
   ```bash
   export ENABLE_RECORDING=true
   python src/main.py
   ```

4. **Check system resources**:
   ```bash
   # CPU and memory
   top
   
   # Disk space
   df -h
   
   # Network connectivity
   ping api.openai.com
   ```

5. **Review related documentation**:
   - [Configuration Guide](configuration.md)
   - [Metrics Dashboard](metrics_dashboard.md)
   - [Replay System](replay_system.md)
   - [Resilience Patterns](resilience_patterns.md)
   - [Health System](health_system.md)

---

**Requirements Satisfied:** 20.7
