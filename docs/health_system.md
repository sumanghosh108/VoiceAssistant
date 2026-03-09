# System Health Tracking

## Overview

The `SystemHealth` class provides health tracking and degradation monitoring for all system components. It distinguishes between critical components (ASR, LLM, TTS) that are essential for core functionality and non-critical components (latency tracker, recorder, dashboard) that support observability and debugging.

## Components

The system tracks health for the following components:

### Critical Components
- **asr**: Automatic Speech Recognition service (Whisper)
- **llm**: Language Model service (Gemini)
- **tts**: Text-to-Speech service (ElevenLabs)

### Non-Critical Components
- **latency_tracker**: Latency measurement and metrics collection
- **recorder**: Session recording for debugging
- **dashboard**: Metrics visualization dashboard

## Usage

### Initialization

```python
from src.health import SystemHealth

health = SystemHealth()
```

All components start in a healthy state.

### Marking Components as Degraded

When a component fails or experiences issues:

```python
health.mark_degraded("asr", "Whisper API timeout")
```

This will:
- Mark the component as unhealthy
- Record the timestamp when degradation occurred
- Log a warning with the component name and reason

### Restoring Component Health

When a component recovers:

```python
health.mark_healthy("asr")
```

This will:
- Mark the component as healthy
- Remove the degradation timestamp
- Log an info message with the recovery time

### Checking Health Status

Check if critical components are healthy:

```python
if health.is_critical_healthy():
    print("Core voice assistant functionality is available")
```

Check if all components are healthy:

```python
if health.is_fully_healthy():
    print("System is fully operational")
```

Get detailed status:

```python
status = health.get_status()
# Returns:
# {
#     "healthy": bool,              # All components healthy
#     "critical_healthy": bool,     # Critical components healthy
#     "components": {               # Per-component status
#         "asr": bool,
#         "llm": bool,
#         ...
#     },
#     "degraded_since": {           # ISO timestamps for degraded components
#         "component_name": "2024-01-15T10:30:45.123456"
#     }
# }
```

## Integration with Health Check Endpoints

The `SystemHealth` class is designed to be used by the `HealthCheckServer` to provide HTTP health check endpoints:

- `/health` - Returns detailed health status for all components
- `/health/ready` - Returns 200 if critical components are healthy, 503 otherwise
- `/health/live` - Returns 200 if the process is alive

## Graceful Degradation

The system implements graceful degradation according to Requirement 16:

- When **non-critical components** fail (latency_tracker, recorder, dashboard):
  - `is_critical_healthy()` returns `True`
  - `is_fully_healthy()` returns `False`
  - Core voice assistant functionality continues
  - Observability features may be unavailable

- When **critical components** fail (asr, llm, tts):
  - `is_critical_healthy()` returns `False`
  - `is_fully_healthy()` returns `False`
  - System cannot process voice interactions
  - Health endpoints return 503 (Service Unavailable)

## Example Scenarios

### Scenario 1: Recorder Fails

```python
health.mark_degraded("recorder", "Disk full")

# System continues operating
assert health.is_critical_healthy() == True
assert health.is_fully_healthy() == False
```

### Scenario 2: ASR Service Fails

```python
health.mark_degraded("asr", "Whisper API unavailable")

# System cannot process audio
assert health.is_critical_healthy() == False
assert health.is_fully_healthy() == False
```

### Scenario 3: Component Recovery

```python
# Component fails
health.mark_degraded("llm", "Rate limit exceeded")

# Wait for recovery...
# Component recovers
health.mark_healthy("llm")

# System returns to full health
assert health.is_critical_healthy() == True
assert health.is_fully_healthy() == True
```

## Requirements Satisfied

- **16.1**: Latency tracker failures don't stop audio processing
- **16.2**: Recording failures don't stop audio processing
- **16.3**: Dashboard failures don't stop audio processing
- **16.5**: Health status events indicate degraded operation
