# Replay System

## Overview

The ReplaySystem provides debugging capabilities by loading recorded sessions from disk and replaying them through the complete pipeline (ASR → LLM → TTS). It can compare replayed events with recorded events to detect discrepancies in behavior.

## Features

- **List Recordings**: Enumerate all available session recordings
- **Load Recordings**: Read metadata, events, and audio frames from disk
- **Replay Sessions**: Inject audio frames at recorded timestamps through the pipeline
- **Speed Adjustment**: Control replay speed (real-time, faster, or slower)
- **Event Comparison**: Compare replayed events with recorded events
- **Discrepancy Detection**: Identify differences in behavior between recordings and replays

## Usage

### Initialize ReplaySystem

```python
from src.replay_system import ReplaySystem
from src.asr_service import ASRService
from src.reasoning_service import ReasoningService
from src.tts_service import TTSService
from pathlib import Path

# Initialize services
asr_service = ASRService(api_key="...")
llm_service = ReasoningService(api_key="...")
tts_service = TTSService(api_key="...", voice_id="...")

# Create replay system
replay_system = ReplaySystem(
    asr_service=asr_service,
    llm_service=llm_service,
    tts_service=tts_service,
    storage_path=Path("./recordings")
)
```

### List Available Recordings

```python
# Get all recordings sorted by start time (most recent first)
recordings = await replay_system.list_recordings()

for recording in recordings:
    print(f"Session: {recording['session_id']}")
    print(f"Duration: {recording['duration_seconds']}s")
    print(f"Events: {recording['event_count']}")
    print(f"Errors: {recording['error_count']}")
```

### Load a Recording

```python
# Load specific recording
session_id = "test-session-123"
metadata, events, audio_frames = await replay_system.load_recording(session_id)

print(f"Loaded {len(events)} events and {len(audio_frames)} audio frames")
```

### Replay a Session

```python
# Replay at normal speed with comparison
result = await replay_system.replay(
    session_id="test-session-123",
    speed=1.0,  # 1.0 = real-time, 2.0 = 2x faster, 0.5 = half speed
    compare=True  # Compare replayed events with recorded events
)

print(f"Replay duration: {result['replay_duration_seconds']}s")
print(f"Recorded events: {result['recorded_event_count']}")
print(f"Replayed events: {result['replayed_event_count']}")

# Check for discrepancies
if result['discrepancies']:
    print(f"Found {len(result['discrepancies'])} discrepancies:")
    for disc in result['discrepancies']:
        print(f"  - {disc['type']}: {disc}")
else:
    print("No discrepancies - replay matches recording perfectly!")
```

### Replay at Different Speeds

```python
# Replay at 2x speed for faster debugging
result = await replay_system.replay(
    session_id="test-session-123",
    speed=2.0,
    compare=False
)

# Replay at half speed for detailed analysis
result = await replay_system.replay(
    session_id="test-session-123",
    speed=0.5,
    compare=True
)
```

## Discrepancy Types

The replay system can detect several types of discrepancies:

### Count Mismatch

Occurs when the number of events differs between recording and replay.

```python
{
    "type": "count_mismatch",
    "event_type": "transcript",
    "recorded_count": 5,
    "replayed_count": 4
}
```

### Transcript Mismatch

Occurs when the final transcript text differs.

```python
{
    "type": "transcript_mismatch",
    "recorded": "Hello world",
    "replayed": "Hello there"
}
```

### Token Sequence Mismatch

Occurs when the LLM token sequence differs.

```python
{
    "type": "token_sequence_mismatch",
    "recorded": "Hello world",
    "replayed": "Hello there"
}
```

## Storage Format

Recordings are stored in the following structure:

```
recordings/
  └── {session_id}/
      ├── metadata.json       # Session metadata
      ├── events.json.gz      # Compressed event data
      └── audio.json.gz       # Compressed audio frames
```

### metadata.json

```json
{
  "session_id": "test-session-123",
  "start_time": "2024-01-01T10:00:00",
  "end_time": "2024-01-01T10:00:10",
  "duration_seconds": 10.0,
  "event_count": 15,
  "audio_frame_count": 10,
  "error_count": 0
}
```

### events.json.gz

Compressed JSON array of events:

```json
[
  {
    "event_type": "audio",
    "timestamp": "2024-01-01T10:00:00",
    "data": {
      "sequence_number": 0,
      "data_length": 1000,
      "sample_rate": 16000,
      "channels": 1
    }
  },
  {
    "event_type": "transcript",
    "timestamp": "2024-01-01T10:00:01",
    "data": {
      "text": "Hello world",
      "partial": false,
      "confidence": 0.95,
      "audio_duration_ms": 1000
    }
  }
]
```

### audio.json.gz

Compressed JSON with audio frames:

```json
{
  "frames": [
    {
      "sequence_number": 0,
      "timestamp": "2024-01-01T10:00:00",
      "data": "68656c6c6f",  // hex-encoded audio bytes
      "sample_rate": 16000,
      "channels": 1
    }
  ]
}
```

## Use Cases

### Debugging Non-Deterministic Issues

When a bug occurs intermittently, record the session and replay it multiple times to reproduce the issue:

```python
# Record the problematic session
# (recording happens automatically if enabled in SessionRecorder)

# Replay multiple times to check consistency
for i in range(10):
    result = await replay_system.replay(session_id, compare=True)
    if result['discrepancies']:
        print(f"Run {i}: Found discrepancies!")
```

### Performance Analysis

Replay sessions at different speeds to analyze performance:

```python
# Replay at 10x speed to quickly process many sessions
result = await replay_system.replay(session_id, speed=10.0, compare=False)
```

### Regression Testing

Compare behavior before and after code changes:

```python
# Record sessions with old code
# Deploy new code
# Replay sessions and check for discrepancies

result = await replay_system.replay(session_id, compare=True)
if result['discrepancies']:
    print("Behavior changed - review discrepancies")
```

## Requirements Satisfied

- **14.1**: Load recorded Audio_Frame objects from storage
- **14.2**: Inject Audio_Frame objects into Event_Pipeline at recorded timestamps
- **14.3**: Process session through complete pipeline
- **14.4**: Compare replayed events with recorded events
- **14.5**: Report discrepancies between replayed and recorded behavior
- **14.6**: Allow replay speed adjustment (real-time, faster, slower)

## Implementation Notes

- Audio frames are injected with timing adjusted by the speed parameter
- The replay creates a new session ID prefixed with "replay_" to avoid conflicts
- Event collection runs in parallel with pipeline processing
- A timeout of 30 seconds is used to prevent indefinite waiting
- Partial transcripts are ignored in comparison (only final transcripts are compared)
- All timestamps are preserved in ISO format for portability
