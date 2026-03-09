# Session Recording System

## Overview

The SessionRecorder class captures all events during a voice assistant session for later replay and debugging. It records audio frames, transcripts, LLM tokens, TTS audio, and errors, storing them in a compressed format on disk.

## Usage

### Basic Usage

```python
from src.session_recorder import SessionRecorder
from pathlib import Path

# Create a recorder for a session
recorder = SessionRecorder(
    session_id="session-123",
    storage_path=Path("./recordings")
)

# Record events as they occur
recorder.record_audio(audio_frame)
recorder.record_transcript(transcript_event)
recorder.record_token(token_event)
recorder.record_tts(tts_event)
recorder.record_error(error_event)

# Save to disk when session ends
await recorder.save()
```

### Integration with Session Management

```python
from src.session import Session
from src.session_recorder import SessionRecorder

# Enable recording for a session
session = Session(
    session_id="session-123",
    # ... other parameters
    recorder=SessionRecorder("session-123") if enable_recording else None
)

# In your event handlers, record events if recorder is present
if session.recorder:
    session.recorder.record_audio(audio_frame)
```

## Storage Format

The SessionRecorder creates a directory for each session with three files:

### 1. metadata.json

Contains session information:

```json
{
  "session_id": "session-123",
  "start_time": "2024-01-01T12:00:00.000000",
  "end_time": "2024-01-01T12:05:30.500000",
  "duration_seconds": 330.5,
  "event_count": 1250,
  "audio_frame_count": 330,
  "error_count": 2
}
```

### 2. events.json.gz

Compressed event data with timestamps:

```json
[
  {
    "event_type": "audio",
    "timestamp": "2024-01-01T12:00:00.100000",
    "data": {
      "sequence_number": 1,
      "data_length": 2000,
      "sample_rate": 16000,
      "channels": 1
    }
  },
  {
    "event_type": "transcript",
    "timestamp": "2024-01-01T12:00:01.200000",
    "data": {
      "text": "Hello world",
      "partial": false,
      "confidence": 0.95,
      "audio_duration_ms": 1000
    }
  }
]
```

### 3. audio.json.gz

Compressed audio frames with hex-encoded data:

```json
{
  "frames": [
    {
      "sequence_number": 1,
      "timestamp": "2024-01-01T12:00:00.100000",
      "data": "00010001...",
      "sample_rate": 16000,
      "channels": 1
    }
  ]
}
```

## Event Types

The SessionRecorder supports five event types:

### Audio Events

Records raw audio frames received from the client:

```python
recorder.record_audio(AudioFrame(
    session_id="session-123",
    data=b"\x00\x01" * 1000,
    timestamp=datetime.now(),
    sequence_number=1,
    sample_rate=16000,
    channels=1
))
```

### Transcript Events

Records speech recognition results:

```python
recorder.record_transcript(TranscriptEvent(
    session_id="session-123",
    text="Hello world",
    partial=False,
    confidence=0.95,
    timestamp=datetime.now(),
    audio_duration_ms=1000
))
```

### Token Events

Records LLM streaming tokens:

```python
recorder.record_token(LLMTokenEvent(
    session_id="session-123",
    token="Hello",
    is_first=True,
    is_last=False,
    timestamp=datetime.now(),
    token_index=0
))
```

### TTS Events

Records synthesized audio metadata (not the audio data itself):

```python
recorder.record_tts(TTSAudioEvent(
    session_id="session-123",
    audio_data=b"\x00\x01" * 500,
    timestamp=datetime.now(),
    sequence_number=1,
    is_final=False
))
```

### Error Events

Records errors that occur during processing:

```python
recorder.record_error(ErrorEvent(
    session_id="session-123",
    component="asr",
    error_type=ErrorType.TIMEOUT,
    message="Whisper API timeout",
    timestamp=datetime.now(),
    retryable=True
))
```

## Performance Considerations

- Events are stored in memory during the session and written to disk only on `save()`
- Audio data is hex-encoded for JSON compatibility (2x size overhead)
- Files are gzip-compressed to reduce disk usage
- For long sessions, memory usage grows linearly with event count

## Debugging with Recordings

Recordings can be used for:

1. **Post-mortem analysis**: Investigate issues that occurred during a session
2. **Replay testing**: Re-run sessions through the pipeline to reproduce bugs
3. **Performance analysis**: Analyze latency patterns across events
4. **Quality assurance**: Review transcription and synthesis quality

## Configuration

Recording can be enabled/disabled per session:

```python
# In your configuration
enable_recording = config.observability.enable_recording

# When creating sessions
recorder = SessionRecorder(session_id) if enable_recording else None
```

## Requirements Satisfied

This implementation satisfies the following requirements:

- **13.1**: Persists all AudioFrame objects for each session
- **13.2**: Persists all events emitted during the session
- **13.3**: Stores recordings with session identifier and timestamp
- **13.4**: Includes metadata (duration, event count, error count)
