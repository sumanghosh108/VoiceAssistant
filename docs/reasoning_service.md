# Reasoning Service Documentation

## Overview

The Reasoning Service implements the language model (LLM) component of the real-time voice assistant pipeline. It uses Google's Gemini API to generate intelligent, streaming responses to user transcripts.

## Architecture

### Component Structure

```
ReasoningService
├── GeminiClient (API wrapper)
├── ConversationContext (per-session history)
├── CircuitBreaker (fault tolerance)
└── RetryConfig (error recovery)
```

### Event Flow

```
TranscriptEvent (final) → ReasoningService → LLMTokenEvent stream
                              ↓
                    ConversationContext
                              ↓
                        Gemini API
```

## Key Features

### 1. Streaming Token Generation

The service streams tokens from Gemini API as they are generated, enabling low-latency responses:

- **First Token Latency**: Tracks time from transcript receipt to first token emission
- **Streaming**: Emits tokens immediately as they arrive from Gemini
- **Completion Marker**: Emits final token with `is_last=True` flag

### 2. Conversation Context Management

Maintains conversation history per session:

- **Session Isolation**: Each session has independent conversation context
- **History Trimming**: Automatically keeps only recent 10 turns (20 messages)
- **Context Persistence**: Context maintained throughout session lifetime

### 3. Resilience Patterns

Implements comprehensive fault tolerance:

- **Circuit Breaker**: Prevents cascading failures to Gemini API
- **Retry with Exponential Backoff**: Retries transient failures (3 attempts)
- **Timeout Protection**: 5-second timeout on API calls
- **Error Events**: Emits ErrorEvent on failures with retry flag

### 4. Latency Tracking

Tracks key latency metrics:

- **LLM Start**: When transcript is received
- **First Token**: When first token is emitted (critical for perceived latency)
- **Generation Complete**: When all tokens have been emitted

## API Reference

### ReasoningService

#### Constructor

```python
ReasoningService(
    api_key: str,
    model: str = "gemini-pro",
    timeout: float = 5.0,
    circuit_breaker: Optional[CircuitBreaker] = None
)
```

**Parameters:**
- `api_key`: Google API key for Gemini access
- `model`: Gemini model name (default: "gemini-pro")
- `timeout`: Timeout in seconds for API calls (default: 5.0)
- `circuit_breaker`: Optional custom circuit breaker

#### Methods

##### process_transcript_stream

```python
async def process_transcript_stream(
    transcript_queue: asyncio.Queue[TranscriptEvent],
    token_queue: asyncio.Queue[LLMTokenEvent],
    latency_tracker: Optional[LatencyTracker] = None
) -> None
```

Main processing loop that consumes transcripts and emits tokens.

**Behavior:**
- Consumes TranscriptEvent objects from `transcript_queue`
- Skips partial transcripts (only processes `partial=False`)
- Skips ErrorEvent objects (passes them through)
- Generates streaming response for each final transcript
- Emits LLMTokenEvent objects to `token_queue`

##### get_context

```python
def get_context(session_id: str) -> ConversationContext
```

Get or create conversation context for a session.

**Returns:** ConversationContext instance for the session

##### update_context

```python
def update_context(
    session_id: str,
    user_message: str,
    assistant_message: str
) -> None
```

Manually update conversation history (typically handled automatically).

### GeminiClient

#### Constructor

```python
GeminiClient(
    api_key: str,
    model: str = "gemini-pro"
)
```

#### Methods

##### generate_stream

```python
async def generate_stream(
    messages: list
) -> AsyncIterator[str]
```

Generate streaming response from Gemini API.

**Parameters:**
- `messages`: List of message dicts with 'role' and 'content' keys

**Yields:** Individual tokens from the streaming response

## Usage Examples

### Basic Usage

```python
from src.reasoning_service import ReasoningService
from src.resilience import CircuitBreaker
import asyncio

# Initialize service
circuit_breaker = CircuitBreaker(name="llm")
service = ReasoningService(
    api_key="your-gemini-api-key",
    model="gemini-pro",
    timeout=5.0,
    circuit_breaker=circuit_breaker
)

# Create queues
transcript_queue = asyncio.Queue()
token_queue = asyncio.Queue()

# Start processing
await service.process_transcript_stream(
    transcript_queue,
    token_queue
)
```

### With Latency Tracking

```python
from src.latency import LatencyTracker

# Create latency tracker
tracker = LatencyTracker(session_id="session-123")

# Process with tracking
await service.process_transcript_stream(
    transcript_queue,
    token_queue,
    latency_tracker=tracker
)

# Get metrics
measurements = tracker.get_measurements()
for m in measurements:
    print(f"{m.stage}: {m.duration_ms}ms")
```

### Manual Context Management

```python
# Get context for session
context = service.get_context("session-123")

# Add messages manually
context.add_user_message("What is Python?")
context.add_assistant_message("Python is a programming language.")

# Or use update_context
service.update_context(
    "session-123",
    "What is Python?",
    "Python is a programming language."
)
```

## Event Schemas

### Input: TranscriptEvent

```python
@dataclass
class TranscriptEvent:
    session_id: str
    text: str
    partial: bool  # Must be False for processing
    confidence: float
    timestamp: datetime
    audio_duration_ms: int
```

### Output: LLMTokenEvent

```python
@dataclass
class LLMTokenEvent:
    session_id: str
    token: str
    is_first: bool  # True for first token (latency tracking)
    is_last: bool   # True for final token (completion marker)
    timestamp: datetime
    token_index: int
```

### Output: ErrorEvent

```python
@dataclass
class ErrorEvent:
    session_id: str
    component: str  # "llm"
    error_type: ErrorType  # TIMEOUT, API_ERROR, etc.
    message: str
    timestamp: datetime
    retryable: bool
```

## Configuration

### Environment Variables

```bash
# Required
GEMINI_API_KEY=your-api-key-here

# Optional
GEMINI_MODEL=gemini-pro
GEMINI_TIMEOUT=5.0
```

### Retry Configuration

Default retry settings:
- **Max Attempts**: 3
- **Initial Delay**: 100ms
- **Max Delay**: 5000ms
- **Exponential Base**: 2.0

### Circuit Breaker Configuration

Default circuit breaker settings:
- **Failure Threshold**: 50% (opens at 50% failure rate)
- **Window Size**: 10 requests
- **Timeout**: 30 seconds (time in open state)

## Error Handling

### Error Types

1. **TimeoutError**: API call exceeded timeout
   - Retryable: Yes
   - Action: Retry with exponential backoff

2. **API_ERROR**: Gemini API returned error
   - Retryable: Depends on error type
   - Action: Check error message, retry if transient

3. **NETWORK_ERROR**: Network connectivity issue
   - Retryable: Yes
   - Action: Retry with exponential backoff

4. **VALIDATION_ERROR**: Invalid input data
   - Retryable: No
   - Action: Fix input and retry

### Circuit Breaker States

1. **CLOSED**: Normal operation, requests pass through
2. **OPEN**: Too many failures, requests rejected immediately
3. **HALF_OPEN**: Testing recovery, one request allowed

## Performance Considerations

### Latency Budget

- **First Token Latency**: Target < 300ms (Requirement 3.5)
- **Total Generation**: Depends on response length
- **Context Lookup**: O(1) dictionary lookup

### Memory Usage

- **Conversation Context**: ~10 turns × 2 messages × avg message size
- **Token Buffer**: Minimal (streaming)
- **Circuit Breaker**: Constant overhead

### Concurrency

- **Session Isolation**: Each session has independent context
- **Concurrent Sessions**: No shared state between sessions
- **Thread Safety**: Context store is session-scoped (no locking needed)

## Testing

### Unit Tests

```bash
# Run all tests
pytest tests/test_reasoning_service.py -v

# Run specific test
pytest tests/test_reasoning_service.py::TestReasoningService::test_init -v
```

### Integration Tests

```bash
# Test with mock Gemini API
pytest tests/test_reasoning_service.py::TestReasoningServiceAsync -v
```

## Troubleshooting

### Common Issues

#### 1. Circuit Breaker Opens Frequently

**Symptoms**: Requests rejected with CircuitBreakerOpenError

**Solutions:**
- Check Gemini API status
- Increase failure threshold
- Increase window size
- Check network connectivity

#### 2. High First Token Latency

**Symptoms**: First token takes > 300ms

**Solutions:**
- Check Gemini API latency
- Reduce conversation context size
- Use faster Gemini model
- Check network latency

#### 3. Context Not Maintained

**Symptoms**: Assistant doesn't remember previous messages

**Solutions:**
- Verify session_id is consistent
- Check context trimming (max_turns)
- Verify update_context is called

#### 4. Tokens Not Streaming

**Symptoms**: All tokens arrive at once

**Solutions:**
- Verify Gemini API streaming is enabled
- Check async iteration in generate_stream
- Verify token_queue is being consumed

## Requirements Mapping

This implementation satisfies the following requirements:

- **3.1**: Processes final TranscriptEvent objects
- **3.2**: Requests streaming response mode from Gemini
- **3.3**: Emits LLMTokenEvent for each token
- **3.4**: Maintains conversation context per session
- **3.5**: Processes first token within 300ms (tracked)
- **3.6**: Emits completion event (is_last=True)
- **3.7**: Implements retry with exponential backoff

## Future Enhancements

1. **Streaming Optimization**: Reduce first token latency
2. **Context Compression**: Summarize old messages
3. **Multi-Model Support**: Support multiple LLM providers
4. **Caching**: Cache common responses
5. **Rate Limiting**: Implement request rate limiting
6. **Metrics**: Add Prometheus metrics export

## References

- [Gemini API Documentation](https://ai.google.dev/docs)
- [Design Document](../design.md)
- [Requirements Document](../requirements.md)
- [Circuit Breaker Pattern](./resilience_patterns.md)
