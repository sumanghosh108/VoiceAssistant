# Resilience Patterns

This document describes the resilience patterns implemented in the voice assistant system for fault tolerance and graceful degradation.

## Overview

The system implements three key resilience patterns:

1. **Circuit Breaker**: Prevents cascading failures by stopping calls to failing services
2. **Retry with Exponential Backoff**: Automatically retries transient failures with increasing delays
3. **Timeout Handling**: Enforces time limits on operations to prevent indefinite blocking

## Circuit Breaker

The circuit breaker pattern protects the system from cascading failures by monitoring failure rates and temporarily blocking calls to failing services.

### States

- **CLOSED**: Normal operation, all calls pass through
- **OPEN**: Service is failing, calls are rejected immediately
- **HALF_OPEN**: Testing if service has recovered

### State Transitions

```
CLOSED --[failure rate > threshold]--> OPEN
OPEN --[timeout expires]--> HALF_OPEN
HALF_OPEN --[test call succeeds]--> CLOSED
HALF_OPEN --[test call fails]--> OPEN
```

### Usage Example

```python
from src.resilience import CircuitBreaker

# Create circuit breaker for an API
whisper_circuit = CircuitBreaker(
    failure_threshold=0.5,  # Open at 50% failure rate
    window_size=10,         # Over 10 requests
    timeout_seconds=30,     # Wait 30s before testing recovery
    name="whisper_api"
)

# Use circuit breaker to protect API calls
async def transcribe_audio(audio_data):
    async def api_call():
        # Your API call here
        return await whisper_client.transcribe(audio_data)
    
    try:
        result = await whisper_circuit.call(api_call)
        return result
    except CircuitBreakerOpenError:
        # Circuit is open, service is down
        logger.error("Whisper API circuit is open")
        raise
```

### Monitoring Circuit State

```python
# Get current state and metrics
state = whisper_circuit.get_state()
print(f"State: {state['state']}")
print(f"Failures: {state['failures']}")
print(f"Successes: {state['successes']}")
```

## Retry with Exponential Backoff

The retry mechanism automatically retries failed operations with exponentially increasing delays between attempts.

### Configuration

```python
from src.resilience import RetryConfig, with_retry

# Configure retry behavior
retry_config = RetryConfig(
    max_attempts=3,              # Try up to 3 times
    initial_delay_ms=100,        # Start with 100ms delay
    max_delay_ms=5000,           # Cap at 5 seconds
    exponential_base=2.0,        # Double delay each time
    retryable_exceptions=(       # Only retry these exceptions
        TimeoutError,
        ConnectionError
    )
)
```

### Usage Example

```python
# Apply retry decorator to async functions
@with_retry(retry_config)
async def call_gemini_api(prompt):
    # This function will be retried on failure
    response = await gemini_client.generate(prompt)
    return response

# Use the function normally
try:
    result = await call_gemini_api("Hello, world!")
except Exception as e:
    # All retries exhausted
    logger.error(f"Failed after {retry_config.max_attempts} attempts: {e}")
```

### Retry Delays

With `initial_delay_ms=100` and `exponential_base=2.0`:

- Attempt 1: Immediate
- Attempt 2: After 100ms delay
- Attempt 3: After 200ms delay
- Attempt 4: After 400ms delay (if max_attempts=4)

## Timeout Handling

The timeout utility enforces time limits on operations to prevent indefinite blocking.

### Usage Example

```python
from src.resilience import with_timeout

async def transcribe_with_timeout(audio_data):
    # Wrap coroutine with timeout
    result = await with_timeout(
        whisper_client.transcribe(audio_data),
        timeout_seconds=3.0,
        operation_name="whisper_transcription"
    )
    return result

try:
    transcript = await transcribe_with_timeout(audio_data)
except TimeoutError as e:
    logger.error(f"Transcription timed out: {e}")
    # Handle timeout
```

## Combining Patterns

These patterns work well together for comprehensive fault tolerance:

```python
from src.resilience import (
    CircuitBreaker,
    RetryConfig,
    with_retry,
    with_timeout
)

# Setup
circuit = CircuitBreaker(
    failure_threshold=0.5,
    window_size=10,
    timeout_seconds=30,
    name="api"
)

retry_config = RetryConfig(
    max_attempts=3,
    initial_delay_ms=100,
    retryable_exceptions=(TimeoutError, ConnectionError)
)

# Combine all three patterns
@with_retry(retry_config)
async def resilient_api_call(data):
    async def api_operation():
        # Timeout wrapper
        result = await with_timeout(
            external_api.call(data),
            timeout_seconds=3.0,
            operation_name="external_api"
        )
        return result
    
    # Circuit breaker wrapper
    return await circuit.call(api_operation)

# Use it
try:
    result = await resilient_api_call(my_data)
except CircuitBreakerOpenError:
    # Service is down, circuit is open
    logger.error("Service unavailable")
except TimeoutError:
    # All retries timed out
    logger.error("Service too slow")
except Exception as e:
    # All retries failed
    logger.error(f"Service error: {e}")
```

## Best Practices

### Circuit Breaker

- Set `failure_threshold` based on acceptable error rates (typically 0.3-0.5)
- Use `window_size` large enough to avoid false positives (10-20 requests)
- Set `timeout_seconds` to allow service recovery time (30-60 seconds)
- Use different circuit breakers for different external services

### Retry

- Only retry transient errors (network, timeout), not permanent errors (auth, validation)
- Keep `max_attempts` low (2-3) to avoid excessive delays
- Set `max_delay_ms` to prevent very long waits
- Use exponential backoff to reduce load on failing services

### Timeout

- Set timeouts based on service SLAs and latency budgets
- Use shorter timeouts for user-facing operations
- Log timeout events for monitoring and debugging
- Always specify descriptive `operation_name` for better logs

## Monitoring

All resilience patterns emit structured logs for monitoring:

### Circuit Breaker Events

```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "INFO",
  "message": "Circuit breaker whisper_api transitioned from closed to open",
  "circuit_name": "whisper_api",
  "old_state": "closed",
  "new_state": "open",
  "failures": 6,
  "successes": 4
}
```

### Retry Events

```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "WARNING",
  "message": "Attempt 1 failed, retrying in 100ms",
  "function": "call_gemini_api",
  "attempt": 1,
  "max_attempts": 3,
  "delay_ms": 100,
  "error": "Connection timeout"
}
```

### Timeout Events

```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "ERROR",
  "message": "Operation whisper_transcription timed out after 3.0s",
  "operation": "whisper_transcription",
  "timeout_seconds": 3.0
}
```

## Configuration

Resilience settings can be configured via environment variables or YAML config:

```yaml
resilience:
  retry_max_attempts: 3
  retry_initial_delay_ms: 100
  retry_max_delay_ms: 5000
  
  circuit_breaker_failure_threshold: 0.5
  circuit_breaker_window_size: 10
  circuit_breaker_timeout_seconds: 30
```

See `docs/configuration.md` for complete configuration options.
