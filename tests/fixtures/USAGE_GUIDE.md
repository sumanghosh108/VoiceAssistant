# Test Fixtures Usage Guide

This guide explains how to use the test fixtures and mock services provided in `tests/fixtures.py` for testing the real-time voice assistant application.

## Overview

The fixtures module provides:
- **Mock API Clients**: Simulate Whisper, Gemini, and ElevenLabs APIs without making real network calls
- **Audio Data Generators**: Create test audio data (silence, sine waves, white noise)
- **Event Generators**: Create test event objects (AudioFrame, TranscriptEvent, LLMTokenEvent, etc.)
- **Factory Functions**: Convenient functions for creating mock instances

## Mock API Clients

### MockWhisperClient

Simulates the Whisper ASR API for testing the ASR service.

#### Basic Usage

```python
from tests.fixtures import MockWhisperClient

# Create mock with default response
client = MockWhisperClient()

# Use in async test
result = await client.transcribe(audio_data, sample_rate=16000)
# Returns: {"text": "Hello world", "confidence": 0.95, "is_partial": False}
```

#### Custom Responses

```python
# Configure custom response at initialization
client = MockWhisperClient(
    default_text="Custom transcription",
    default_confidence=0.85,
    default_partial=True
)

# Or configure after creation
client.configure_response("New text", confidence=0.90, partial=False)
```

#### Simulating Errors

```python
# Simulate timeout error
client = MockWhisperClient(simulate_error=TimeoutError("API timeout"))

# Or configure error after creation
client.configure_error(ValueError("Invalid audio format"))
```

#### Simulating Latency

```python
# Add 100ms delay to simulate API latency
client = MockWhisperClient(delay_seconds=0.1)
```

#### Call Tracking

```python
# Track API calls for verification
await client.transcribe(audio_data)
await client.transcribe(audio_data)

assert client.call_count == 2
assert len(client.call_history) == 2
assert client.call_history[0]["audio_bytes"] == len(audio_data)
```

#### Integration with ASR Service

```python
from src.asr_service import ASRService
from tests.fixtures import MockWhisperClient

# Create ASR service
asr_service = ASRService(api_key="test_key")

# Replace client with mock
mock_client = MockWhisperClient(default_text="Test transcription")
asr_service.client = mock_client

# Now test ASR service without real API calls
```

### MockGeminiClient

Simulates the Gemini LLM API for testing the reasoning service.

#### Basic Usage

```python
from tests.fixtures import MockGeminiClient

# Create mock with default tokens
client = MockGeminiClient()

# Use in async test
tokens = []
async for token in client.generate_stream(messages):
    tokens.append(token)
# Returns: ["Hello", " ", "world", "!"]
```

#### Custom Token Streams

```python
# Configure custom tokens
client = MockGeminiClient(default_tokens=["Custom", " ", "response", "."])

# Or configure after creation
client.configure_response(["New", " ", "tokens"])
```

#### Simulating Errors

```python
# Simulate API error
client = MockGeminiClient(simulate_error=TimeoutError("LLM timeout"))
```

#### Simulating Streaming Latency

```python
# Add delays to simulate streaming behavior
client = MockGeminiClient(
    delay_seconds=0.1,      # Initial delay before first token
    delay_per_token=0.05    # Delay between each token
)
```

#### Integration with Reasoning Service

```python
from src.reasoning_service import ReasoningService
from tests.fixtures import MockGeminiClient

# Create reasoning service
reasoning_service = ReasoningService(api_key="test_key")

# Replace client with mock
mock_client = MockGeminiClient(default_tokens=["Test", " ", "response"])
reasoning_service.client = mock_client

# Now test reasoning service without real API calls
```

### MockElevenLabsClient

Simulates the ElevenLabs TTS API for testing the TTS service.

#### Basic Usage

```python
from tests.fixtures import MockElevenLabsClient

# Create mock with default audio chunks
client = MockElevenLabsClient()

# Use in async test
chunks = []
async for chunk in client.synthesize_stream("Test text", "voice_id"):
    chunks.append(chunk)
# Returns: 3 chunks of 1024 bytes each
```

#### Custom Audio Chunks

```python
# Configure custom chunks
custom_chunks = [b'chunk1', b'chunk2', b'chunk3']
client = MockElevenLabsClient(default_chunks=custom_chunks)

# Or configure after creation
client.configure_response([b'new1', b'new2'])
```

#### Simulating Errors

```python
# Simulate API error
client = MockElevenLabsClient(simulate_error=TimeoutError("TTS timeout"))
```

#### Simulating Streaming Latency

```python
# Add delays to simulate streaming behavior
client = MockElevenLabsClient(
    delay_seconds=0.1,      # Initial delay before first chunk
    delay_per_chunk=0.05    # Delay between each chunk
)
```

#### Integration with TTS Service

```python
from src.tts_service import TTSService
from tests.fixtures import MockElevenLabsClient

# Create TTS service
tts_service = TTSService(api_key="test_key", voice_id="test_voice")

# Replace client with mock
mock_client = MockElevenLabsClient(default_chunks=[b'audio1', b'audio2'])
tts_service.client = mock_client

# Now test TTS service without real API calls
```

## Audio Data Generators

### Generate Silence

```python
from tests.fixtures import generate_silence

# Generate 1 second of silence at 16kHz
audio = generate_silence(duration_ms=1000, sample_rate=16000)
# Returns: 32000 bytes of zeros (16000 samples * 2 bytes per sample)
```

### Generate Sine Wave

```python
from tests.fixtures import generate_sine_wave

# Generate 1 second of 440Hz sine wave (A4 note)
audio = generate_sine_wave(
    duration_ms=1000,
    frequency=440.0,
    sample_rate=16000,
    amplitude=0.5
)
```

### Generate White Noise

```python
from tests.fixtures import generate_white_noise

# Generate 1 second of white noise
audio = generate_white_noise(
    duration_ms=1000,
    sample_rate=16000,
    amplitude=0.3
)
```

### Generate Audio Frames

```python
from tests.fixtures import generate_audio_frames

# Generate 1 second of audio split into 100ms frames
frames = generate_audio_frames(
    session_id="test_session",
    duration_ms=1000,
    frame_duration_ms=100,
    audio_type="silence",  # or "sine" or "noise"
    sample_rate=16000
)
# Returns: List of 10 AudioFrame objects
```

## Event Generators

### Create Transcript Event

```python
from tests.fixtures import create_transcript_event

# Create a transcript event
event = create_transcript_event(
    session_id="test_session",
    text="Hello world",
    partial=False,
    confidence=0.95,
    audio_duration_ms=1000
)
```

### Create LLM Token Events

```python
from tests.fixtures import create_llm_token_events

# Create a sequence of token events
events = create_llm_token_events(
    session_id="test_session",
    tokens=["Hello", " ", "world", "!"]
)
# Returns: List of 4 LLMTokenEvent objects with is_first and is_last flags set
```

### Create TTS Audio Events

```python
from tests.fixtures import create_tts_audio_events

# Create a sequence of audio events
events = create_tts_audio_events(
    session_id="test_session",
    num_chunks=3,
    chunk_size=1024
)
# Returns: List of 3 TTSAudioEvent objects with sequence numbers
```

### Create Error Event

```python
from tests.fixtures import create_error_event
from src.events import ErrorType

# Create an error event
event = create_error_event(
    session_id="test_session",
    component="asr",
    error_type=ErrorType.TIMEOUT,
    message="API timeout",
    retryable=True
)
```

## Complete Test Examples

### Testing ASR Service

```python
import asyncio
import pytest
from tests.fixtures import MockWhisperClient, generate_audio_frames
from src.asr_service import ASRService

@pytest.mark.asyncio
async def test_asr_service_transcription():
    # Create ASR service with mock client
    asr_service = ASRService(api_key="test_key")
    mock_client = MockWhisperClient(default_text="Test transcription")
    asr_service.client = mock_client
    
    # Create test audio frames
    frames = generate_audio_frames(
        session_id="test_session",
        duration_ms=1000,
        audio_type="sine"
    )
    
    # Create queues
    audio_queue = asyncio.Queue()
    transcript_queue = asyncio.Queue()
    
    # Add frames to queue
    for frame in frames:
        await audio_queue.put(frame)
    
    # Process audio
    task = asyncio.create_task(
        asr_service.process_audio_stream(audio_queue, transcript_queue)
    )
    
    # Wait for processing
    await asyncio.sleep(0.2)
    
    # Verify transcription
    assert not transcript_queue.empty()
    event = await transcript_queue.get()
    assert event.text == "Test transcription"
    
    # Cleanup
    task.cancel()
```

### Testing Reasoning Service

```python
import asyncio
import pytest
from tests.fixtures import MockGeminiClient, create_transcript_event
from src.reasoning_service import ReasoningService

@pytest.mark.asyncio
async def test_reasoning_service_token_streaming():
    # Create reasoning service with mock client
    reasoning_service = ReasoningService(api_key="test_key")
    mock_client = MockGeminiClient(default_tokens=["Test", " ", "response"])
    reasoning_service.client = mock_client
    
    # Create test transcript
    transcript = create_transcript_event(
        session_id="test_session",
        text="Hello",
        partial=False
    )
    
    # Create queues
    transcript_queue = asyncio.Queue()
    token_queue = asyncio.Queue()
    
    # Add transcript to queue
    await transcript_queue.put(transcript)
    
    # Process transcript
    task = asyncio.create_task(
        reasoning_service.process_transcript_stream(
            transcript_queue,
            token_queue
        )
    )
    
    # Wait for processing
    await asyncio.sleep(0.2)
    
    # Verify tokens
    tokens = []
    while not token_queue.empty():
        event = await token_queue.get()
        tokens.append(event.token)
    
    assert tokens == ["Test", " ", "response", ""]  # Empty token for completion
    
    # Cleanup
    task.cancel()
```

### Testing TTS Service

```python
import asyncio
import pytest
from tests.fixtures import MockElevenLabsClient, create_llm_token_events
from src.tts_service import TTSService

@pytest.mark.asyncio
async def test_tts_service_audio_synthesis():
    # Create TTS service with mock client
    tts_service = TTSService(
        api_key="test_key",
        voice_id="test_voice",
        phrase_buffer_tokens=3
    )
    mock_client = MockElevenLabsClient(default_chunks=[b'audio1', b'audio2'])
    tts_service.client = mock_client
    
    # Create test token events
    token_events = create_llm_token_events(
        session_id="test_session",
        tokens=["Hello", " ", "world", "."]
    )
    
    # Create queues
    token_queue = asyncio.Queue()
    audio_queue = asyncio.Queue()
    
    # Add tokens to queue
    for event in token_events:
        await token_queue.put(event)
    
    # Process tokens
    task = asyncio.create_task(
        tts_service.process_token_stream(token_queue, audio_queue)
    )
    
    # Wait for processing
    await asyncio.sleep(0.2)
    
    # Verify audio chunks
    chunks = []
    while not audio_queue.empty():
        event = await audio_queue.get()
        if event.audio_data:  # Skip empty final marker
            chunks.append(event.audio_data)
    
    assert len(chunks) > 0
    
    # Cleanup
    task.cancel()
```

## Best Practices

1. **Reset Mocks Between Tests**: Use `client.reset()` to clear call history between tests
2. **Configure Errors Explicitly**: Use `configure_error()` to test error handling paths
3. **Simulate Realistic Latency**: Add delays to test timeout handling and latency tracking
4. **Track API Calls**: Use `call_count` and `call_history` to verify correct API usage
5. **Use Event Generators**: Use helper functions to create consistent test events
6. **Test with Different Audio Types**: Use sine waves and noise to test with non-silent audio

## Factory Functions

For convenience, factory functions are provided:

```python
from tests.fixtures import (
    create_mock_whisper_client,
    create_mock_gemini_client,
    create_mock_elevenlabs_client
)

# Create mocks with custom configuration
whisper = create_mock_whisper_client(default_text="Custom")
gemini = create_mock_gemini_client(default_tokens=["Test"])
elevenlabs = create_mock_elevenlabs_client(default_chunks=[b'audio'])
```

## Running Tests

Run all fixture tests:
```bash
pytest tests/test_fixtures.py -v
```

Run specific test:
```bash
pytest tests/test_fixtures.py::test_mock_whisper_client_default_response -v
```

Run with coverage:
```bash
pytest tests/test_fixtures.py --cov=tests.fixtures --cov-report=html
```
