"""Session recording system for debugging and replay.

Records all events during a session including audio frames, transcripts,
LLM tokens, TTS audio, and errors. Persists data to disk in compressed
format for later replay and analysis.
"""

import json
import gzip
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass
from datetime import datetime

from src.core.events import AudioFrame, TranscriptEvent, LLMTokenEvent, TTSAudioEvent, ErrorEvent
from src.utils.logger import logger


@dataclass
class RecordedEvent:
    """Wrapper for recorded events with metadata.
    
    Provides a unified structure for storing different event types
    with their timestamps and serialized data.
    """
    event_type: str  # "audio", "transcript", "token", "tts", "error"
    timestamp: datetime
    data: Dict[str, Any]


class SessionRecorder:
    """Records all events for a session for later replay.
    
    Captures audio frames, transcripts, LLM tokens, TTS audio, and errors
    during a session. Stores events in memory and persists to disk on save().
    
    Storage format:
    - metadata.json: Session information (duration, event counts, etc.)
    - events.json.gz: Compressed event data with timestamps
    - audio.json.gz: Compressed audio frames (hex-encoded)
    """
    
    def __init__(self, session_id: str, storage_path: Path = Path("./recordings")):
        """Initialize session recorder.
        
        Args:
            session_id: Unique identifier for the session
            storage_path: Base directory for storing recordings
        """
        self.session_id = session_id
        self.storage_path = storage_path / session_id
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.events: List[RecordedEvent] = []
        self.audio_frames: List[AudioFrame] = []
        self.start_time = datetime.now()
        
        logger.info(
            f"Initialized session recorder for {session_id}",
            extra={
                "session_id": session_id,
                "storage_path": str(self.storage_path)
            }
        )
    
    def record_audio(self, frame: AudioFrame) -> None:
        """Record audio frame.
        
        Stores the complete audio frame and creates a summary event
        with metadata (sequence number, data length, sample rate).
        
        Args:
            frame: AudioFrame to record
        """
        self.audio_frames.append(frame)
        self.events.append(RecordedEvent(
            event_type="audio",
            timestamp=frame.timestamp,
            data={
                "sequence_number": frame.sequence_number,
                "data_length": len(frame.data),
                "sample_rate": frame.sample_rate,
                "channels": frame.channels
            }
        ))
    
    def record_transcript(self, event: TranscriptEvent) -> None:
        """Record transcript event.
        
        Stores transcription results including text, confidence,
        and whether it's a partial or final result.
        
        Args:
            event: TranscriptEvent to record
        """
        self.events.append(RecordedEvent(
            event_type="transcript",
            timestamp=event.timestamp,
            data={
                "text": event.text,
                "partial": event.partial,
                "confidence": event.confidence,
                "audio_duration_ms": event.audio_duration_ms
            }
        ))
    
    def record_token(self, event: LLMTokenEvent) -> None:
        """Record LLM token event.
        
        Stores individual tokens from the LLM streaming response
        with position and boundary markers.
        
        Args:
            event: LLMTokenEvent to record
        """
        self.events.append(RecordedEvent(
            event_type="token",
            timestamp=event.timestamp,
            data={
                "token": event.token,
                "is_first": event.is_first,
                "is_last": event.is_last,
                "token_index": event.token_index
            }
        ))
    
    def record_tts(self, event: TTSAudioEvent) -> None:
        """Record TTS audio event.
        
        Stores metadata about synthesized audio chunks.
        Note: Audio data itself is not stored in events to save space,
        only length and sequence information.
        
        Args:
            event: TTSAudioEvent to record
        """
        self.events.append(RecordedEvent(
            event_type="tts",
            timestamp=event.timestamp,
            data={
                "sequence_number": event.sequence_number,
                "audio_length": len(event.audio_data),
                "is_final": event.is_final
            }
        ))
    
    def record_error(self, event: ErrorEvent) -> None:
        """Record error event.
        
        Stores error information including component, error type,
        message, and whether the error is retryable.
        
        Args:
            event: ErrorEvent to record
        """
        self.events.append(RecordedEvent(
            event_type="error",
            timestamp=event.timestamp,
            data={
                "component": event.component,
                "error_type": event.error_type.value,
                "message": event.message,
                "retryable": event.retryable
            }
        ))
    
    async def save(self) -> None:
        """Save recording to disk.
        
        Persists three files:
        1. metadata.json: Session info (duration, counts, timestamps)
        2. events.json.gz: Compressed event data
        3. audio.json.gz: Compressed audio frames (hex-encoded)
        
        All timestamps are stored in ISO format for portability.
        """
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()
        
        # Save metadata
        metadata = {
            "session_id": self.session_id,
            "start_time": self.start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": duration,
            "event_count": len(self.events),
            "audio_frame_count": len(self.audio_frames),
            "error_count": sum(1 for e in self.events if e.event_type == "error")
        }
        
        with open(self.storage_path / "metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)
        
        # Save events
        events_data = [
            {
                "event_type": e.event_type,
                "timestamp": e.timestamp.isoformat(),
                "data": e.data
            }
            for e in self.events
        ]
        
        with gzip.open(self.storage_path / "events.json.gz", "wt") as f:
            json.dump(events_data, f)
        
        # Save audio frames
        audio_data = {
            "frames": [
                {
                    "sequence_number": frame.sequence_number,
                    "timestamp": frame.timestamp.isoformat(),
                    "data": frame.data.hex(),  # Convert bytes to hex string
                    "sample_rate": frame.sample_rate,
                    "channels": frame.channels
                }
                for frame in self.audio_frames
            ]
        }
        
        with gzip.open(self.storage_path / "audio.json.gz", "wt") as f:
            json.dump(audio_data, f)
        
        logger.info(
            f"Saved recording for session {self.session_id}",
            extra={
                "session_id": self.session_id,
                "duration_seconds": duration,
                "event_count": len(self.events),
                "audio_frame_count": len(self.audio_frames),
                "error_count": metadata["error_count"],
                "storage_path": str(self.storage_path)
            }
        )
