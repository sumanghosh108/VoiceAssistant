"""Event schemas for the real-time voice assistant pipeline.

All events are Python dataclasses with timestamp metadata for latency tracking.
These events flow through the asynchronous event pipeline connecting components.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


@dataclass
class AudioFrame:
    """Raw audio data chunk with metadata.
    
    Represents a fixed-size chunk of audio data received from the client
    via WebSocket. Contains timestamp and sequence information for ordering
    and latency tracking.
    """
    session_id: str
    data: bytes  # Raw audio bytes (PCM 16-bit, 16kHz mono)
    timestamp: datetime
    sequence_number: int
    sample_rate: int = 16000
    channels: int = 1


@dataclass
class TranscriptEvent:
    """Speech recognition result from ASR service.
    
    Contains transcribed text from audio input. The partial flag indicates
    whether this is an interim result (True) or final transcription (False).
    """
    session_id: str
    text: str
    partial: bool  # True for interim results, False for final
    confidence: float  # 0.0 to 1.0
    timestamp: datetime
    audio_duration_ms: int  # Duration of audio that was transcribed


@dataclass
class LLMTokenEvent:
    """Streaming token from language model.
    
    Represents a single token emitted by the LLM during streaming response
    generation. The is_first flag is used for first-token latency tracking.
    """
    session_id: str
    token: str
    is_first: bool  # True for first token in response
    is_last: bool  # True for final token
    timestamp: datetime
    token_index: int  # Position in response sequence


@dataclass
class TTSAudioEvent:
    """Synthesized audio chunk from TTS service.
    
    Contains a chunk of synthesized audio data ready to be sent to the client.
    The is_final flag indicates the last chunk of a response.
    """
    session_id: str
    audio_data: bytes  # PCM audio bytes
    timestamp: datetime
    sequence_number: int
    is_final: bool  # True for last chunk of response


class ErrorType(Enum):
    """Classification of error types for error handling and retry logic."""
    TIMEOUT = "timeout"
    API_ERROR = "api_error"
    NETWORK_ERROR = "network_error"
    VALIDATION_ERROR = "validation_error"


@dataclass
class ErrorEvent:
    """Error notification event.
    
    Emitted when a component encounters an error. The retryable flag
    indicates whether the operation should be retried.
    """
    session_id: str
    component: str  # "asr", "llm", "tts", "websocket"
    error_type: ErrorType
    message: str
    timestamp: datetime
    retryable: bool
