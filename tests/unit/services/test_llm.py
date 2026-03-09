"""
Unit tests for ReasoningService.

Tests the LLM service implementation including:
- Service initialization
- Conversation context management
- Error handling
"""

import asyncio
import pytest
from datetime import datetime

from src.services.llm import ReasoningService, GeminiClient
from src.core.events import TranscriptEvent, LLMTokenEvent, ErrorEvent, ErrorType
from src.core.models import ConversationContext
from src.infrastructure.resilience import CircuitBreaker


class TestGeminiClient:
    """Tests for GeminiClient wrapper."""
    
    def test_init(self):
        """Test GeminiClient initialization."""
        client = GeminiClient(api_key="test-key", model="gemini-pro")
        assert client.api_key == "test-key"
        assert client.model == "gemini-pro"
        
    def test_init_default_model(self):
        """Test GeminiClient initialization with default model."""
        client = GeminiClient(api_key="test-key")
        assert client.api_key == "test-key"
        assert client.model == "gemini-pro"


class TestReasoningService:
    """Tests for ReasoningService."""
    
    def test_init(self):
        """Test ReasoningService initialization."""
        service = ReasoningService(
            api_key="test-key",
            model="gemini-pro",
            timeout=5.0
        )
        assert service.model == "gemini-pro"
        assert service.timeout == 5.0
        assert service.circuit_breaker is not None
        assert service.circuit_breaker.name == "llm"
        assert isinstance(service.context_store, dict)
        assert len(service.context_store) == 0
        
    def test_init_with_circuit_breaker(self):
        """Test ReasoningService initialization with custom circuit breaker."""
        cb = CircuitBreaker(name="custom-llm")
        service = ReasoningService(
            api_key="test-key",
            circuit_breaker=cb
        )
        assert service.circuit_breaker is cb
        assert service.circuit_breaker.name == "custom-llm"
        
    def test_get_context_creates_new(self):
        """Test get_context creates new context for unknown session."""
        service = ReasoningService(api_key="test-key")
        
        context = service.get_context("session-1")
        
        assert isinstance(context, ConversationContext)
        assert context.max_turns == 10
        assert len(context.messages) == 0
        assert "session-1" in service.context_store
        
    def test_get_context_returns_existing(self):
        """Test get_context returns existing context for known session."""
        service = ReasoningService(api_key="test-key")
        
        # Create context and add message
        context1 = service.get_context("session-1")
        context1.add_user_message("Hello")
        
        # Get context again
        context2 = service.get_context("session-1")
        
        assert context2 is context1
        assert len(context2.messages) == 1
        assert context2.messages[0].content == "Hello"
        
    def test_update_context(self):
        """Test update_context adds messages to context."""
        service = ReasoningService(api_key="test-key")
        
        service.update_context(
            "session-1",
            "What is Python?",
            "Python is a programming language."
        )
        
        context = service.get_context("session-1")
        assert len(context.messages) == 2
        assert context.messages[0].role == "user"
        assert context.messages[0].content == "What is Python?"
        assert context.messages[1].role == "assistant"
        assert context.messages[1].content == "Python is a programming language."
        
    def test_multiple_sessions(self):
        """Test service maintains separate contexts for different sessions."""
        service = ReasoningService(api_key="test-key")
        
        # Create contexts for two sessions
        context1 = service.get_context("session-1")
        context1.add_user_message("Hello from session 1")
        
        context2 = service.get_context("session-2")
        context2.add_user_message("Hello from session 2")
        
        # Verify contexts are separate
        assert len(service.context_store) == 2
        assert context1 is not context2
        assert context1.messages[0].content == "Hello from session 1"
        assert context2.messages[0].content == "Hello from session 2"


@pytest.mark.asyncio
class TestReasoningServiceAsync:
    """Async tests for ReasoningService."""
    
    async def test_process_transcript_stream_skips_partial(self):
        """Test that process_transcript_stream skips partial transcripts."""
        service = ReasoningService(api_key="test-key")
        
        transcript_queue = asyncio.Queue()
        token_queue = asyncio.Queue()
        
        # Add partial transcript
        partial_transcript = TranscriptEvent(
            session_id="session-1",
            text="Hello",
            partial=True,
            confidence=0.8,
            timestamp=datetime.now(),
            audio_duration_ms=500
        )
        await transcript_queue.put(partial_transcript)
        
        # Start processing task
        process_task = asyncio.create_task(
            service.process_transcript_stream(transcript_queue, token_queue)
        )
        
        # Give it time to process
        await asyncio.sleep(0.1)
        
        # Cancel task
        process_task.cancel()
        try:
            await process_task
        except asyncio.CancelledError:
            pass
        
        # Verify no tokens were emitted
        assert token_queue.empty()
        
    async def test_process_transcript_stream_skips_error_events(self):
        """Test that process_transcript_stream skips error events."""
        service = ReasoningService(api_key="test-key")
        
        transcript_queue = asyncio.Queue()
        token_queue = asyncio.Queue()
        
        # Add error event
        error_event = ErrorEvent(
            session_id="session-1",
            component="asr",
            error_type=ErrorType.TIMEOUT,
            message="ASR timeout",
            timestamp=datetime.now(),
            retryable=True
        )
        await transcript_queue.put(error_event)
        
        # Start processing task
        process_task = asyncio.create_task(
            service.process_transcript_stream(transcript_queue, token_queue)
        )
        
        # Give it time to process
        await asyncio.sleep(0.1)
        
        # Cancel task
        process_task.cancel()
        try:
            await process_task
        except asyncio.CancelledError:
            pass
        
        # Verify no tokens were emitted
        assert token_queue.empty()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
