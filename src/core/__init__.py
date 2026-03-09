"""
Core domain models and events for the real-time voice assistant.

This package contains the fundamental data structures and event schemas
used throughout the application.
"""

from src.core.events import (
    AudioFrame,
    TranscriptEvent,
    LLMTokenEvent,
    TTSAudioEvent,
    ErrorEvent,
    ErrorType
)
from src.core.models import (
    AudioBuffer,
    TokenBuffer,
    ConversationContext,
    Session
)

__all__ = [
    # Events
    "AudioFrame",
    "TranscriptEvent",
    "LLMTokenEvent",
    "TTSAudioEvent",
    "ErrorEvent",
    "ErrorType",
    # Models
    "AudioBuffer",
    "TokenBuffer",
    "ConversationContext",
    "Session",
]
