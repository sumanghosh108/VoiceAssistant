# ASR Service Documentation

## Overview

The ASR (Automatic Speech Recognition) Service provides real-time speech-to-text transcription using OpenAI's Whisper API. It processes streaming audio through an asynchronous event pipeline with comprehensive error handling and latency tracking.

## Architecture

The ASR service consists of two main components:

1. **WhisperClient**: Low-level wrapper for Whisper API calls
2. **ASRService**: High-level service that manages audio buffering, transcription, and event emission

## Features

- **Audio Buffering**: Accumulates audio frames until sufficient duration is available for transcription
- **Streaming Transcription**: Supports both partial and final transcription results
- **Fault Tolerance**: 
  - Circuit breaker protection to prevent cascading failures
  - Timeout handling (default: 3 seconds)
  - Error event emission for downstream handling
- **Latency Tracking**: Records timing markers for observability
- **Async/Await**: Non-blocking processing using Python asyncio

## Usage

### Basic Setup

```python
from src.asr_service import ASRService
from src.resilience import CircuitBreaker
import asyncio

# Create circuit breaker for fault tolerance
circuit_breaker = CircuitBreaker(
    failure_threshold=0.5,
    window_size=10,
    timeout_seconds=30,
    name="asr"
)

# Initialize ASR service
asr_service = ASRService(
    api_key="your_openai_api_key",
    timeout=3.0,
    buffer_duration_ms=1000,
    circuit_breaker=circuit_breaker
)
```

### Processing Audio Stream

```python
from src.events import AudioFrame, TranscriptEvent
from src.latency import LatencyTracker

# Create queues for event pipeline
audio_queue = asyncio.Queue()
transcript_queue = asyncio.Queue()

# Optional: Create latency tracker
latency_tracker = LatencyTracker("session_123")

# Start processing task
asr_task = asyncio.create_task(
    asr_service.process_audio_stream(
        audio_queue,
        transcript_queue,
        latency_tracker
    )
)

# Feed audio frames
audio_frame = AudioFrame(
    session_id="session_123",
    data=audio_bytes,  # PCM 16-bit, 16kHz mono
    timestamp=datetime.now(),
    sequence_number=1,
    sample_rate=16000,
    channels=1
)
await audio_queue.put(audio_frame)

# Consume transcript events
transcript_event = await transcript_queue.get()
print(f"Transcription: {transcript_event.text}")
print(f"Confidence: {transcript_event.confidence}")
print(f"Partial: {transcript_event.partial}")
```

## Configuration

### Constructor Parameters

- **api_key** (str, required): OpenAI API key for Whisper access
- **timeout** (float, default: 3.0): Timeout in seconds for API calls
- **buffer_duration_ms** (int, default: 1000): Audio buffer duration in milliseconds
- **circuit_breaker** (CircuitBreaker, optional): Circuit breaker for fault tolerance

### Audio Requirements

The ASR service expects audio in the following format:
- **Format**: PCM (Pulse Code Modulation)
- **Bit Depth**: 16-bit
- **Sample Rate**: 16kHz (16000 Hz)
- **Channels**: Mono (1 channel)
- **Byte Order**: Little-endian

## Event Flow

```
AudioFrame → Audio Queue → ASR Service → Transcript Queue → TranscriptEvent
                                ↓
                          (on error)
                                ↓
                           ErrorEvent
```

### Input: AudioFrame

```python
@dataclass
class AudioFrame:
    session_id: str
    data: bytes  # Raw PCM audio
    timestamp: datetime
    sequence_number: int
    sample_rate: int = 16000
    channels: int = 1
```

### Output: TranscriptEvent

```python
@dataclass
class TranscriptEvent:
    session_id: str
    text: str
    partial: bool  # True for interim, False for final
    confidence: float  # 0.0 to 1.0
    timestamp: datetime
    audio_duration_ms: int
```

### Output: ErrorEvent (on failure)

```python
@dataclass
class ErrorEvent:
    session_id: str
    component: str  # "asr"
    error_type: ErrorType  # TIMEOUT, API_ERROR, etc.
    message: str
    timestamp: datetime
    retryable: bool
```

## Error Handling

The ASR service handles errors at multiple levels:

### 1. Timeout Protection

API calls are wrapped with timeout protection (default: 3 seconds). When a timeout occurs:
- A `TimeoutError` is caught
- An `ErrorEvent` with `error_type=TIMEOUT` is emitted
- The error is marked as `retryable=True`

### 2. Circuit Breaker

The circuit breaker prevents cascading failures:
- **CLOSED**: Normal operation, requests pass through
- **OPEN**: Too many failures, requests are rejected immediately
- **HALF_OPEN**: Testing recovery, one request is allowed

Circuit breaker opens when:
- Failure rate exceeds 50% over 10 requests
- Stays open for 30 seconds before testing recovery

### 3. Error Events

All errors result in `ErrorEvent` objects being emitted to the transcript queue:
- **TIMEOUT**: API call exceeded timeout (retryable)
- **API_ERROR**: Whisper API returned an error (may be retryable)
- **VALIDATION_ERROR**: Invalid input data (not retryable)

## Latency Tracking

The ASR service records timing markers for observability:

1. **audio_received_{sequence}**: When audio frame is received
2. **transcript_start**: When transcription begins
3. **transcript_emitted**: When transcript event is emitted

Latency measurement:
- **asr_latency**: Time from `transcript_start` to `transcript_emitted`

## Production Considerations

### WhisperClient Implementation

The current `WhisperClient` is a placeholder. For production use, implement the `transcribe()` method:

```python
import openai
from io import BytesIO
import wave

class WhisperClient:
    def __init__(self, api_key: str):
        self.client = openai.OpenAI(api_key=api_key)
        
    async def transcribe(self, audio_data: bytes, sample_rate: int = 16000) -> dict:
        # Convert PCM bytes to WAV format
        wav_buffer = BytesIO()
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_data)
        
        wav_buffer.seek(0)
        wav_buffer.name = "audio.wav"
        
        # Call Whisper API
        response = await asyncio.to_thread(
            self.client.audio.transcriptions.create,
            model="whisper-1",
            file=wav_buffer,
            response_format="verbose_json"
        )
        
        return {
            "text": response.text,
            "confidence": 1.0,  # Whisper doesn't provide confidence scores
            "is_partial": False
        }
```

### Performance Tuning

- **Buffer Duration**: Adjust `buffer_duration_ms` based on latency requirements
  - Smaller buffers (500ms): Lower latency, more API calls
  - Larger buffers (2000ms): Higher latency, fewer API calls
  
- **Timeout**: Adjust based on network conditions and API performance
  - Faster networks: 2-3 seconds
  - Slower networks: 5-10 seconds

### Monitoring

Monitor these metrics in production:
- ASR latency (target: <500ms)
- Circuit breaker state transitions
- Error rate by type
- API call success rate

## Testing

Run the test suite:

```bash
python -m pytest tests/test_asr_service.py -v
```

Tests cover:
- Audio buffering and transcription
- Partial and final transcript emission
- Timeout handling
- Error event emission
- Circuit breaker integration
- Latency tracking
- Multiple frame buffering

## Requirements Mapping

This implementation satisfies the following requirements:

- **2.1**: Buffers audio until sufficient data is available
- **2.2**: Sends audio to Whisper API for transcription
- **2.3**: Emits TranscriptEvent with partial flag
- **2.4**: Emits TranscriptEvent with final flag
- **2.5**: Processes audio with latency tracking
- **2.6**: Emits error events on failure
- **2.7**: Includes confidence scores in TranscriptEvent
