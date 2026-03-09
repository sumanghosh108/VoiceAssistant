"""
Unit tests for session management.

Tests cover:
- Session dataclass creation and attributes
- SessionManager initialization
- Session creation with pipeline tasks
- Session cleanup with timeout enforcement
- Recording integration
- Multiple concurrent sessions
"""

import asyncio
import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from src.core.models import Session, SessionManager
from src.core.events import AudioFrame, TranscriptEvent, LLMTokenEvent, TTSAudioEvent
from src.observability.latency import LatencyTracker


class TestSession:
    """Tests for Session dataclass."""
    
    def test_session_creation(self):
        """Test Session dataclass can be created with required fields."""
        session_id = "test-session-123"
        created_at = datetime.now()
        websocket = Mock()
        
        audio_queue = asyncio.Queue()
        transcript_queue = asyncio.Queue()
        token_queue = asyncio.Queue()
        tts_queue = asyncio.Queue()
        
        latency_tracker = LatencyTracker(session_id)
        
        session = Session(
            session_id=session_id,
            created_at=created_at,
            websocket=websocket,
            audio_queue=audio_queue,
            transcript_queue=transcript_queue,
            token_queue=token_queue,
            tts_queue=tts_queue,
            latency_tracker=latency_tracker
        )
        
        assert session.session_id == session_id
        assert session.created_at == created_at
        assert session.websocket == websocket
        assert session.audio_queue == audio_queue
        assert session.transcript_queue == transcript_queue
        assert session.token_queue == token_queue
        assert session.tts_queue == tts_queue
        assert session.latency_tracker == latency_tracker
        assert session.asr_task is None
        assert session.llm_task is None
        assert session.tts_task is None
        assert session.recorder is None
        
    @pytest.mark.asyncio
    async def test_session_with_tasks(self):
        """Test Session can hold task references."""
        session_id = "test-session-123"
        
        session = Session(
            session_id=session_id,
            created_at=datetime.now(),
            websocket=Mock(),
            audio_queue=asyncio.Queue(),
            transcript_queue=asyncio.Queue(),
            token_queue=asyncio.Queue(),
            tts_queue=asyncio.Queue(),
            latency_tracker=LatencyTracker(session_id)
        )
        
        # Create mock tasks
        asr_task = asyncio.create_task(asyncio.sleep(0))
        llm_task = asyncio.create_task(asyncio.sleep(0))
        tts_task = asyncio.create_task(asyncio.sleep(0))
        
        session.asr_task = asr_task
        session.llm_task = llm_task
        session.tts_task = tts_task
        
        assert session.asr_task == asr_task
        assert session.llm_task == llm_task
        assert session.tts_task == tts_task
        
        # Cleanup tasks
        await asyncio.gather(asr_task, llm_task, tts_task)


class TestSessionManager:
    """Tests for SessionManager class."""
    
    def test_session_manager_initialization(self):
        """Test SessionManager can be initialized with services."""
        asr_service = Mock()
        llm_service = Mock()
        tts_service = Mock()
        
        manager = SessionManager(
            asr_service=asr_service,
            llm_service=llm_service,
            tts_service=tts_service,
            enable_recording=False
        )
        
        assert manager.asr_service == asr_service
        assert manager.llm_service == llm_service
        assert manager.tts_service == tts_service
        assert manager.enable_recording is False
        assert manager.sessions == {}
        assert manager.get_active_session_count() == 0
        
    def test_session_manager_with_recording(self):
        """Test SessionManager initialization with recording enabled."""
        manager = SessionManager(
            asr_service=Mock(),
            llm_service=Mock(),
            tts_service=Mock(),
            enable_recording=True,
            recording_storage_path="/tmp/recordings"
        )
        
        assert manager.enable_recording is True
        assert manager.recording_storage_path == "/tmp/recordings"
        
    @pytest.mark.asyncio
    async def test_create_session(self):
        """Test session creation initializes all components."""
        # Create mock services with async methods
        asr_service = Mock()
        asr_service.process_audio_stream = AsyncMock()
        
        llm_service = Mock()
        llm_service.process_transcript_stream = AsyncMock()
        
        tts_service = Mock()
        tts_service.process_token_stream = AsyncMock()
        
        manager = SessionManager(
            asr_service=asr_service,
            llm_service=llm_service,
            tts_service=tts_service,
            enable_recording=False
        )
        
        websocket = Mock()
        
        # Create session
        session = await manager.create_session(websocket)
        
        # Verify session attributes
        assert session.session_id is not None
        assert len(session.session_id) > 0
        assert session.websocket == websocket
        assert isinstance(session.created_at, datetime)
        
        # Verify queues are created
        assert isinstance(session.audio_queue, asyncio.Queue)
        assert isinstance(session.transcript_queue, asyncio.Queue)
        assert isinstance(session.token_queue, asyncio.Queue)
        assert isinstance(session.tts_queue, asyncio.Queue)
        
        # Verify queue sizes
        assert session.audio_queue.maxsize == 100
        assert session.transcript_queue.maxsize == 50
        assert session.token_queue.maxsize == 200
        assert session.tts_queue.maxsize == 100
        
        # Verify latency tracker
        assert isinstance(session.latency_tracker, LatencyTracker)
        assert session.latency_tracker.session_id == session.session_id
        
        # Verify tasks are created and started
        assert session.asr_task is not None
        assert session.llm_task is not None
        assert session.tts_task is not None
        assert not session.asr_task.done()
        assert not session.llm_task.done()
        assert not session.tts_task.done()
        
        # Verify session is stored
        assert session.session_id in manager.sessions
        assert manager.get_session(session.session_id) == session
        assert manager.get_active_session_count() == 1
        
        # Cleanup
        await manager.cleanup_session(session.session_id)
        
    @pytest.mark.asyncio
    async def test_create_session_starts_pipeline_tasks(self):
        """Test that create_session starts all pipeline tasks with correct arguments."""
        # Create mock services
        asr_service = Mock()
        asr_service.process_audio_stream = AsyncMock()
        
        llm_service = Mock()
        llm_service.process_transcript_stream = AsyncMock()
        
        tts_service = Mock()
        tts_service.process_token_stream = AsyncMock()
        
        manager = SessionManager(
            asr_service=asr_service,
            llm_service=llm_service,
            tts_service=tts_service
        )
        
        # Create session
        session = await manager.create_session(Mock())
        
        # Give tasks a moment to start
        await asyncio.sleep(0.01)
        
        # Verify services were called with correct queues
        asr_service.process_audio_stream.assert_called_once()
        call_args = asr_service.process_audio_stream.call_args
        assert call_args[0][0] == session.audio_queue
        assert call_args[0][1] == session.transcript_queue
        assert call_args[0][2] == session.latency_tracker
        
        llm_service.process_transcript_stream.assert_called_once()
        call_args = llm_service.process_transcript_stream.call_args
        assert call_args[0][0] == session.transcript_queue
        assert call_args[0][1] == session.token_queue
        assert call_args[0][2] == session.latency_tracker
        
        tts_service.process_token_stream.assert_called_once()
        call_args = tts_service.process_token_stream.call_args
        assert call_args[0][0] == session.token_queue
        assert call_args[0][1] == session.tts_queue
        assert call_args[0][2] == session.latency_tracker
        
        # Cleanup
        await manager.cleanup_session(session.session_id)
        
    @pytest.mark.asyncio
    async def test_cleanup_session_cancels_tasks(self):
        """Test cleanup_session cancels all pipeline tasks."""
        # Create mock services that run indefinitely
        asr_service = Mock()
        asr_service.process_audio_stream = AsyncMock(side_effect=asyncio.sleep(1000))
        
        llm_service = Mock()
        llm_service.process_transcript_stream = AsyncMock(side_effect=asyncio.sleep(1000))
        
        tts_service = Mock()
        tts_service.process_token_stream = AsyncMock(side_effect=asyncio.sleep(1000))
        
        manager = SessionManager(
            asr_service=asr_service,
            llm_service=llm_service,
            tts_service=tts_service
        )
        
        # Create session
        session = await manager.create_session(Mock())
        session_id = session.session_id
        
        # Verify tasks are running
        assert not session.asr_task.done()
        assert not session.llm_task.done()
        assert not session.tts_task.done()
        
        # Cleanup session
        await manager.cleanup_session(session_id)
        
        # Verify tasks are cancelled
        assert session.asr_task.cancelled() or session.asr_task.done()
        assert session.llm_task.cancelled() or session.llm_task.done()
        assert session.tts_task.cancelled() or session.tts_task.done()
        
        # Verify session is removed
        assert session_id not in manager.sessions
        assert manager.get_session(session_id) is None
        assert manager.get_active_session_count() == 0
        
    @pytest.mark.asyncio
    async def test_cleanup_session_timeout(self):
        """Test cleanup_session enforces timeout."""
        # Create a service that doesn't respond to cancellation quickly
        async def slow_cleanup():
            try:
                await asyncio.sleep(10)  # Longer than timeout
            except asyncio.CancelledError:
                await asyncio.sleep(10)  # Ignore cancellation
                
        asr_service = Mock()
        asr_service.process_audio_stream = AsyncMock(side_effect=slow_cleanup)
        
        llm_service = Mock()
        llm_service.process_transcript_stream = AsyncMock(side_effect=asyncio.sleep(1000))
        
        tts_service = Mock()
        tts_service.process_token_stream = AsyncMock(side_effect=asyncio.sleep(1000))
        
        manager = SessionManager(
            asr_service=asr_service,
            llm_service=llm_service,
            tts_service=tts_service
        )
        
        # Create session
        session = await manager.create_session(Mock())
        session_id = session.session_id
        
        # Cleanup with short timeout
        start_time = asyncio.get_event_loop().time()
        await manager.cleanup_session(session_id, timeout=0.1)
        end_time = asyncio.get_event_loop().time()
        
        # Verify cleanup completed within timeout (with some margin)
        assert (end_time - start_time) < 0.5
        
        # Verify session is removed even with timeout
        assert session_id not in manager.sessions
        
    @pytest.mark.asyncio
    async def test_cleanup_nonexistent_session(self):
        """Test cleanup_session handles non-existent session gracefully."""
        manager = SessionManager(
            asr_service=Mock(),
            llm_service=Mock(),
            tts_service=Mock()
        )
        
        # Should not raise exception
        await manager.cleanup_session("nonexistent-session-id")
        
    @pytest.mark.asyncio
    async def test_multiple_concurrent_sessions(self):
        """Test SessionManager can handle multiple concurrent sessions."""
        # Create mock services
        asr_service = Mock()
        asr_service.process_audio_stream = AsyncMock()
        
        llm_service = Mock()
        llm_service.process_transcript_stream = AsyncMock()
        
        tts_service = Mock()
        tts_service.process_token_stream = AsyncMock()
        
        manager = SessionManager(
            asr_service=asr_service,
            llm_service=llm_service,
            tts_service=tts_service
        )
        
        # Create multiple sessions
        session1 = await manager.create_session(Mock())
        session2 = await manager.create_session(Mock())
        session3 = await manager.create_session(Mock())
        
        # Verify all sessions are active
        assert manager.get_active_session_count() == 3
        assert session1.session_id in manager.sessions
        assert session2.session_id in manager.sessions
        assert session3.session_id in manager.sessions
        
        # Verify session IDs are unique
        session_ids = manager.get_session_ids()
        assert len(session_ids) == 3
        assert len(set(session_ids)) == 3  # All unique
        
        # Cleanup one session
        await manager.cleanup_session(session1.session_id)
        assert manager.get_active_session_count() == 2
        assert session1.session_id not in manager.sessions
        
        # Cleanup remaining sessions
        await manager.cleanup_session(session2.session_id)
        await manager.cleanup_session(session3.session_id)
        assert manager.get_active_session_count() == 0
        
    @pytest.mark.asyncio
    async def test_session_isolation(self):
        """Test that sessions have isolated queues and resources."""
        # Create mock services
        asr_service = Mock()
        asr_service.process_audio_stream = AsyncMock()
        
        llm_service = Mock()
        llm_service.process_transcript_stream = AsyncMock()
        
        tts_service = Mock()
        tts_service.process_token_stream = AsyncMock()
        
        manager = SessionManager(
            asr_service=asr_service,
            llm_service=llm_service,
            tts_service=tts_service
        )
        
        # Create two sessions
        session1 = await manager.create_session(Mock())
        session2 = await manager.create_session(Mock())
        
        # Verify queues are different objects
        assert session1.audio_queue is not session2.audio_queue
        assert session1.transcript_queue is not session2.transcript_queue
        assert session1.token_queue is not session2.token_queue
        assert session1.tts_queue is not session2.tts_queue
        
        # Verify latency trackers are different
        assert session1.latency_tracker is not session2.latency_tracker
        assert session1.latency_tracker.session_id != session2.latency_tracker.session_id
        
        # Verify tasks are different
        assert session1.asr_task is not session2.asr_task
        assert session1.llm_task is not session2.llm_task
        assert session1.tts_task is not session2.tts_task
        
        # Cleanup
        await manager.cleanup_session(session1.session_id)
        await manager.cleanup_session(session2.session_id)
        
    @pytest.mark.asyncio
    async def test_get_session(self):
        """Test get_session retrieves correct session."""
        asr_service = Mock()
        asr_service.process_audio_stream = AsyncMock()
        
        llm_service = Mock()
        llm_service.process_transcript_stream = AsyncMock()
        
        tts_service = Mock()
        tts_service.process_token_stream = AsyncMock()
        
        manager = SessionManager(
            asr_service=asr_service,
            llm_service=llm_service,
            tts_service=tts_service
        )
        
        # Create session
        session = await manager.create_session(Mock())
        
        # Retrieve session
        retrieved = manager.get_session(session.session_id)
        assert retrieved == session
        assert retrieved.session_id == session.session_id
        
        # Try to get non-existent session
        assert manager.get_session("nonexistent") is None
        
        # Cleanup
        await manager.cleanup_session(session.session_id)
        
        # Verify session is gone
        assert manager.get_session(session.session_id) is None
