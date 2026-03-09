"""
Core data models for the real-time voice assistant.

This module contains buffer classes and session data structures used
throughout the application pipeline.
"""

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Any

from src.core.events import AudioFrame, LLMTokenEvent


class AudioBuffer:
    """Buffers audio frames until ready for processing.
    
    Accumulates incoming AudioFrame objects until sufficient audio duration
    is available for transcription. Uses sample count to determine readiness.
    """
    
    def __init__(self, duration_ms: int, sample_rate: int = 16000):
        """Initialize audio buffer.
        
        Args:
            duration_ms: Target buffer duration in milliseconds
            sample_rate: Audio sample rate in Hz (default: 16000)
        """
        self.duration_ms = duration_ms
        self.sample_rate = sample_rate
        self.frames: List[AudioFrame] = []
        self.total_samples = 0
        self.target_samples = (sample_rate * duration_ms) // 1000
        
    def append(self, frame: AudioFrame) -> None:
        """Add audio frame to buffer."""
        self.frames.append(frame)
        # Assuming 16-bit PCM: 2 bytes per sample
        self.total_samples += len(frame.data) // 2
        
    def is_ready(self) -> bool:
        """Check if buffer has enough audio for processing."""
        return self.total_samples >= self.target_samples
        
    def get_audio_bytes(self) -> bytes:
        """Concatenate all frames into single byte array."""
        return b''.join(frame.data for frame in self.frames)
        
    def clear(self) -> None:
        """Clear buffer for next batch."""
        self.frames.clear()
        self.total_samples = 0


class TokenBuffer:
    """Buffers LLM tokens until phrase boundary.
    
    Accumulates streaming tokens from the LLM until either a complete phrase
    is detected (sentence boundary) or the maximum token count is reached.
    """
    
    def __init__(self, max_tokens: int = 10):
        """Initialize token buffer."""
        self.max_tokens = max_tokens
        self.tokens: List[LLMTokenEvent] = []
        
    def append(self, token: LLMTokenEvent) -> None:
        """Add token to buffer."""
        self.tokens.append(token)
        
    def is_phrase_complete(self) -> bool:
        """Check if buffer contains complete phrase."""
        if len(self.tokens) >= self.max_tokens:
            return True
            
        if self.tokens:
            last_token = self.tokens[-1].token
            return any(punct in last_token for punct in ['.', '!', '?', '\n'])
            
        return False
        
    def get_text(self) -> str:
        """Concatenate tokens into text."""
        return ''.join(token.token for token in self.tokens)
        
    def clear(self) -> None:
        """Clear buffer for next phrase."""
        self.tokens.clear()


@dataclass
class Message:
    """Single message in conversation history."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime


class ConversationContext:
    """Maintains conversation history for a session."""
    
    def __init__(self, max_turns: int = 10):
        """Initialize conversation context."""
        self.max_turns = max_turns
        self.messages: List[Message] = []
        
    def add_user_message(self, content: str) -> None:
        """Add user message to history."""
        self.messages.append(Message(
            role="user",
            content=content,
            timestamp=datetime.now()
        ))
        self._trim_history()
        
    def add_assistant_message(self, content: str) -> None:
        """Add assistant message to history."""
        self.messages.append(Message(
            role="assistant",
            content=content,
            timestamp=datetime.now()
        ))
        self._trim_history()
        
    def get_messages_for_api(self) -> List[dict]:
        """Format messages for API."""
        return [
            {"role": msg.role, "content": msg.content}
            for msg in self.messages
        ]
        
    def _trim_history(self) -> None:
        """Keep only recent messages within max_turns."""
        if len(self.messages) > self.max_turns * 2:
            self.messages = self.messages[-(self.max_turns * 2):]


@dataclass
class Session:
    """Represents a single voice interaction session.
    
    Encapsulates all state and resources for a single user connection,
    including event queues for the pipeline, references to processing tasks,
    and observability components.
    """
    session_id: str
    created_at: datetime
    websocket: Any  # WebSocket connection object
    
    # Event queues for pipeline stages
    audio_queue: asyncio.Queue
    transcript_queue: asyncio.Queue
    token_queue: asyncio.Queue
    tts_queue: asyncio.Queue
    
    # Processing task references
    asr_task: Optional[asyncio.Task] = None
    llm_task: Optional[asyncio.Task] = None
    tts_task: Optional[asyncio.Task] = None
    
    # Observability components
    latency_tracker: Any = field(default=None)
    recorder: Optional[Any] = None
