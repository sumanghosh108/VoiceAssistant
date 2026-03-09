"""
Real-Time Voice Assistant

A production-ready real-time voice assistant system with streaming audio processing,
integrating Whisper ASR, Gemini LLM, and ElevenLabs TTS services.

Architecture:
- Core: Domain models and events
- Utils: Common utilities (logging, helpers)
- Infrastructure: Configuration, resilience patterns
- Services: External API integrations (ASR, LLM, TTS)
- Observability: Health checks, metrics, latency tracking
- Session: Session lifecycle management
- API: WebSocket and HTTP endpoints
"""

__version__ = "1.0.0"

# Core exports
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

# Service exports
from src.services.asr import ASRService
from src.services.llm import ReasoningService
from src.services.tts import TTSService

# Infrastructure exports
from src.infrastructure.config import (
    SystemConfig,
    ConfigLoader
)
from src.utils.logger import logger, ProductionLogger
from src.infrastructure.resilience import (
    CircuitBreaker,
    CircuitState,
    RetryConfig,
    with_retry,
    with_timeout
)

# Observability exports
from src.observability.health import SystemHealth
from src.observability.latency import (
    LatencyTracker,
    LatencyMonitor,
    LatencyBudget
)
from src.observability.metrics import MetricsAggregator

# Session exports
from src.session.manager import SessionManager
from src.session.recorder import SessionRecorder
from src.session.replay import ReplaySystem

# API exports
from src.api.websocket import WebSocketServer
from src.api.health_server import HealthCheckServer
from src.observability.metrics import MetricsDashboard

__all__ = [
    # Version
    "__version__",
    
    # Core
    "AudioFrame",
    "TranscriptEvent",
    "LLMTokenEvent",
    "TTSAudioEvent",
    "ErrorEvent",
    "ErrorType",
    "AudioBuffer",
    "TokenBuffer",
    "ConversationContext",
    "Session",
    
    # Services
    "ASRService",
    "ReasoningService",
    "TTSService",
    
    # Infrastructure
    "SystemConfig",
    "ConfigLoader",
    "logger",
    "ProductionLogger",
    "CircuitBreaker",
    "CircuitState",
    "RetryConfig",
    "with_retry",
    "with_timeout",
    
    # Observability
    "SystemHealth",
    "LatencyTracker",
    "LatencyMonitor",
    "LatencyBudget",
    "MetricsAggregator",
    
    # Session
    "SessionManager",
    "SessionRecorder",
    "ReplaySystem",
    
    # API
    "WebSocketServer",
    "HealthCheckServer",
    "MetricsDashboard",
]
