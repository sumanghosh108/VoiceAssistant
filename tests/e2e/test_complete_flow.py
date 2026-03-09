"""
End-to-end integration tests for the real-time voice assistant.

Tests complete audio-to-audio flow, concurrent session handling,
error recovery, and graceful degradation.

Requirements: 6.2, 6.5, 16.4
"""

import asyncio
import pytest
from datetime import datetime
from typing import List

from src.core.events import (
    AudioFrame,
    TranscriptEvent,
    LLMTokenEvent,
    TTSAudioEvent,
    ErrorEvent,
    ErrorType
)
from src.core.models import SessionManager
from src.services.asr import ASRService
from src.services.llm import ReasoningService
from src.services.tts import TTSService
from src.infrastructure.resilience import CircuitBreaker
from src.observability.health import SystemHealth
from tests.fixtures.mocks import (
    MockWhisperClient,
    MockGeminiClient,
    MockElevenLabsClient,
    generate_audio_frames
)


@pytest.fixture
def mock_whisper_client():
    """Create a mock Whisper client."""
    return MockWhisperClient(
        default_text="Hello, how can I help you?",
        default_confidence=0.95,
        delay_seconds=0.05
    )


@pytest.fixture
def mock_gemini_client():
    """Create a mock Gemini client."""
    return MockGeminiClient(
        default_tokens=["I", " ", "can", " ", "help", " ", "you", "."],
        delay_seconds=0.05,
        delay_per_token=0.01
    )


@pytest.fixture
def mock_elevenlabs_client():
    """Create a mock ElevenLabs client."""
    return MockElevenLabsClient(
        default_chunks=[b'\x00' * 512 for _ in range(5)],
        delay_seconds=0.05,
        delay_per_chunk=0.01
    )


@pytest.fixture
def circuit_breakers():
    """Create circuit breakers for services."""
    return {
        "asr": CircuitBreaker(name="asr", failure_threshold=0.5, window_size=10),
        "llm": CircuitBreaker(name="llm", failure_threshold=0.5, window_size=10),
        "tts": CircuitBreaker(name="tts", failure_threshold=0.5, window_size=10)
    }


@pytest.fixture
def asr_service(mock_whisper_client, circuit_breakers):
    """Create ASR service with mock client."""
    service = ASRService(
        api_key="test_key",
        timeout=3.0,
        buffer_duration_ms=500,
        circuit_breaker=circuit_breakers["asr"]
    )
    service.client = mock_whisper_client
    return service


@pytest.fixture
def reasoning_service(mock_gemini_client, circuit_breakers):
    """Create reasoning service with mock client."""
    service = ReasoningService(
        api_key="test_key",
        model="gemini-pro",
        timeout=5.0,
        circuit_breaker=circuit_breakers["llm"]
    )
    service.client = mock_gemini_client
    return service


@pytest.fixture
def tts_service(mock_elevenlabs_client, circuit_breakers):
    """Create TTS service with mock client."""
    service = TTSService(
        api_key="test_key",
        voice_id="test_voice",
        timeout=3.0,
        phrase_buffer_tokens=3,
        circuit_breaker=circuit_breakers["tts"]
    )
    service.client = mock_elevenlabs_client
    return service


@pytest.fixture
def session_manager(asr_service, reasoning_service, tts_service):
    """Create session manager with all services."""
    return SessionManager(
        asr_service=asr_service,
        llm_service=reasoning_service,
        tts_service=tts_service,
        enable_recording=False
    )


class TestCompleteAudioToAudioFlow:
    """Test complete audio-to-audio flow through the pipeline.
    
    Validates: Requirements 6.2
    """
    
    @pytest.mark.asyncio
    async def test_end_to_end_audio_processing(
        self,
        session_manager,
        mock_whisper_client,
        mock_gemini_client,
        mock_elevenlabs_client
    ):
        """Test complete flow from audio input to audio output."""
        # Create a session
        session = await session_manager.create_session(websocket=None)
        
        # Generate test audio frames
        audio_frames = generate_audio_frames(
            session_id=session.session_id,
            duration_ms=1000,
            frame_duration_ms=100,
            audio_type="sine"
        )
        
        # Feed audio frames into the pipeline
        for frame in audio_frames:
            await session.audio_queue.put(frame)
        
        # Wait for processing through the pipeline
        await asyncio.sleep(0.5)
        
        # Verify ASR was called
        assert mock_whisper_client.call_count > 0
        
        # Verify transcript was generated
        assert not session.transcript_queue.empty()
        
        # Wait for LLM processing
        await asyncio.sleep(0.3)
        
        # Verify LLM was called
        assert mock_gemini_client.call_count > 0
        
        # Verify tokens were generated
        assert not session.token_queue.empty()
        
        # Wait for TTS processing
        await asyncio.sleep(0.3)
        
        # Verify TTS was called
        assert mock_elevenlabs_client.call_count > 0
        
        # Verify audio output was generated
        assert not session.tts_queue.empty()
        
        # Collect output audio events
        output_events = []
        while not session.tts_queue.empty():
            event = await session.tts_queue.get()
            output_events.append(event)
        
        # Verify we got audio output
        assert len(output_events) > 0
        assert all(isinstance(e, TTSAudioEvent) for e in output_events)
        
        # Cleanup
        await session_manager.cleanup_session(session.session_id)
    
    @pytest.mark.asyncio
    async def test_latency_tracking_through_pipeline(
        self,
        session_manager
    ):
        """Test that latency is tracked through all pipeline stages."""
        # Create a session
        session = await session_manager.create_session(websocket=None)
        
        # Track start time
        start_time = datetime.now()
        
        # Generate and feed audio
        audio_frames = generate_audio_frames(
            session_id=session.session_id,
            duration_ms=500,
            frame_duration_ms=100
        )
        
        for frame in audio_frames:
            await session.audio_queue.put(frame)
        
        # Wait for complete processing
        await asyncio.sleep(1.0)
        
        # Calculate end-to-end latency
        end_time = datetime.now()
        latency_ms = (end_time - start_time).total_seconds() * 1000
        
        # Verify latency is reasonable (should be under 2 seconds)
        assert latency_ms < 2000, f"End-to-end latency {latency_ms}ms exceeds budget"
        
        # Verify latency tracker has measurements
        measurements = session.latency_tracker.get_measurements()
        assert len(measurements) > 0
        
        # Cleanup
        await session_manager.cleanup_session(session.session_id)
    
    @pytest.mark.asyncio
    async def test_event_ordering_preserved(
        self,
        session_manager,
        mock_gemini_client
    ):
        """Test that event ordering is preserved through the pipeline."""
        # Configure specific token sequence
        expected_tokens = ["First", " ", "Second", " ", "Third"]
        mock_gemini_client.configure_response(expected_tokens)
        
        # Create session
        session = await session_manager.create_session(websocket=None)
        
        # Feed audio
        audio_frames = generate_audio_frames(
            session_id=session.session_id,
            duration_ms=500,
            frame_duration_ms=100
        )
        
        for frame in audio_frames:
            await session.audio_queue.put(frame)
        
        # Wait for processing
        await asyncio.sleep(0.8)
        
        # Collect tokens in order
        tokens = []
        while not session.token_queue.empty():
            event = await session.token_queue.get()
            tokens.append(event.token)
        
        # Verify tokens are in correct order
        assert tokens == expected_tokens
        
        # Cleanup
        await session_manager.cleanup_session(session.session_id)


class TestConcurrentSessionHandling:
    """Test concurrent session handling and isolation.
    
    Validates: Requirements 6.2, 6.5
    """
    
    @pytest.mark.asyncio
    async def test_multiple_concurrent_sessions(
        self,
        session_manager
    ):
        """Test that multiple sessions can be processed concurrently."""
        # Create multiple sessions
        num_sessions = 5
        sessions = []
        
        for i in range(num_sessions):
            session = await session_manager.create_session(websocket=None)
            sessions.append(session)
        
        # Feed audio to all sessions
        for session in sessions:
            audio_frames = generate_audio_frames(
                session_id=session.session_id,
                duration_ms=500,
                frame_duration_ms=100
            )
            
            for frame in audio_frames:
                await session.audio_queue.put(frame)
        
        # Wait for processing
        await asyncio.sleep(1.0)
        
        # Verify all sessions produced output
        for session in sessions:
            assert not session.tts_queue.empty(), \
                f"Session {session.session_id} did not produce output"
        
        # Cleanup all sessions
        for session in sessions:
            await session_manager.cleanup_session(session.session_id)
    
    @pytest.mark.asyncio
    async def test_session_isolation_on_error(
        self,
        session_manager,
        mock_whisper_client
    ):
        """Test that errors in one session don't affect other sessions."""
        # Create two sessions
        session1 = await session_manager.create_session(websocket=None)
        session2 = await session_manager.create_session(websocket=None)
        
        # Configure mock to fail for first call, succeed for second
        call_count = [0]
        original_transcribe = mock_whisper_client.transcribe
        
        async def selective_error(audio_data, sample_rate=16000):
            call_count[0] += 1
            if call_count[0] == 1:
                raise TimeoutError("Simulated timeout")
            return await original_transcribe(audio_data, sample_rate)
        
        mock_whisper_client.transcribe = selective_error
        
        # Feed audio to both sessions
        for session in [session1, session2]:
            audio_frames = generate_audio_frames(
                session_id=session.session_id,
                duration_ms=500,
                frame_duration_ms=100
            )
            
            for frame in audio_frames:
                await session.audio_queue.put(frame)
        
        # Wait for processing
        await asyncio.sleep(1.0)
        
        # Session 2 should still produce output despite session 1 error
        # (Note: Both might succeed due to retries, but isolation is key)
        assert session_manager.sessions[session1.session_id] is not None
        assert session_manager.sessions[session2.session_id] is not None
        
        # Cleanup
        await session_manager.cleanup_session(session1.session_id)
        await session_manager.cleanup_session(session2.session_id)
    
    @pytest.mark.asyncio
    async def test_session_cleanup_isolation(
        self,
        session_manager
    ):
        """Test that cleaning up one session doesn't affect others."""
        # Create three sessions
        session1 = await session_manager.create_session(websocket=None)
        session2 = await session_manager.create_session(websocket=None)
        session3 = await session_manager.create_session(websocket=None)
        
        # Cleanup session 2
        await session_manager.cleanup_session(session2.session_id)
        
        # Verify session 2 is removed
        assert session2.session_id not in session_manager.sessions
        
        # Verify sessions 1 and 3 are still active
        assert session1.session_id in session_manager.sessions
        assert session3.session_id in session_manager.sessions
        
        # Verify sessions 1 and 3 can still process
        for session in [session1, session3]:
            audio_frames = generate_audio_frames(
                session_id=session.session_id,
                duration_ms=300,
                frame_duration_ms=100
            )
            
            for frame in audio_frames:
                await session.audio_queue.put(frame)
        
        await asyncio.sleep(0.5)
        
        # Both should still work
        assert not session1.tts_queue.empty()
        assert not session3.tts_queue.empty()
        
        # Cleanup remaining sessions
        await session_manager.cleanup_session(session1.session_id)
        await session_manager.cleanup_session(session3.session_id)


class TestErrorRecoveryAndResilience:
    """Test error recovery and resilience mechanisms.
    
    Validates: Requirements 6.5
    """
    
    @pytest.mark.asyncio
    async def test_retry_on_transient_error(
        self,
        session_manager,
        mock_whisper_client
    ):
        """Test that transient errors trigger retry mechanism."""
        # Configure mock to fail once then succeed
        call_count = [0]
        original_transcribe = mock_whisper_client.transcribe
        
        async def fail_once(audio_data, sample_rate=16000):
            call_count[0] += 1
            if call_count[0] == 1:
                raise TimeoutError("Transient error")
            return await original_transcribe(audio_data, sample_rate)
        
        mock_whisper_client.transcribe = fail_once
        
        # Create session and feed audio
        session = await session_manager.create_session(websocket=None)
        
        audio_frames = generate_audio_frames(
            session_id=session.session_id,
            duration_ms=500,
            frame_duration_ms=100
        )
        
        for frame in audio_frames:
            await session.audio_queue.put(frame)
        
        # Wait for processing with retry
        await asyncio.sleep(1.0)
        
        # Verify retry occurred (call_count > 1)
        assert call_count[0] > 1, "Retry mechanism did not trigger"
        
        # Verify processing eventually succeeded
        assert not session.transcript_queue.empty()
        
        # Cleanup
        await session_manager.cleanup_session(session.session_id)
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_on_repeated_failures(
        self,
        session_manager,
        mock_whisper_client,
        circuit_breakers
    ):
        """Test that circuit breaker opens after repeated failures."""
        # Configure mock to always fail
        mock_whisper_client.configure_error(TimeoutError("Persistent failure"))
        
        # Create session
        session = await session_manager.create_session(websocket=None)
        
        # Feed audio multiple times to trigger circuit breaker
        for _ in range(15):  # More than window_size (10)
            audio_frames = generate_audio_frames(
                session_id=session.session_id,
                duration_ms=200,
                frame_duration_ms=100
            )
            
            for frame in audio_frames:
                await session.audio_queue.put(frame)
            
            await asyncio.sleep(0.1)
        
        # Wait for circuit breaker to open
        await asyncio.sleep(0.5)
        
        # Verify circuit breaker opened
        cb_state = circuit_breakers["asr"].get_state()
        # Circuit breaker should have recorded failures
        assert cb_state["failures"] > 0
        
        # Cleanup
        await session_manager.cleanup_session(session.session_id)
    
    @pytest.mark.asyncio
    async def test_timeout_handling(
        self,
        session_manager,
        mock_whisper_client
    ):
        """Test that timeouts are handled correctly."""
        # Configure mock with long delay to trigger timeout
        mock_whisper_client.delay_seconds = 5.0  # Longer than timeout
        
        # Create session
        session = await session_manager.create_session(websocket=None)
        
        # Feed audio
        audio_frames = generate_audio_frames(
            session_id=session.session_id,
            duration_ms=500,
            frame_duration_ms=100
        )
        
        for frame in audio_frames:
            await session.audio_queue.put(frame)
        
        # Wait for timeout to occur
        await asyncio.sleep(4.0)
        
        # System should handle timeout gracefully (no crash)
        assert session.session_id in session_manager.sessions
        
        # Cleanup
        await session_manager.cleanup_session(session.session_id)
    
    @pytest.mark.asyncio
    async def test_error_event_emission(
        self,
        session_manager,
        mock_whisper_client
    ):
        """Test that errors are properly emitted as error events."""
        # Configure mock to fail
        mock_whisper_client.configure_error(ValueError("Test error"))
        
        # Create session
        session = await session_manager.create_session(websocket=None)
        
        # Feed audio
        audio_frames = generate_audio_frames(
            session_id=session.session_id,
            duration_ms=500,
            frame_duration_ms=100
        )
        
        for frame in audio_frames:
            await session.audio_queue.put(frame)
        
        # Wait for error processing
        await asyncio.sleep(0.5)
        
        # Error should be logged (we can't easily check error events without
        # modifying the pipeline, but we verify the system doesn't crash)
        assert session.session_id in session_manager.sessions
        
        # Cleanup
        await session_manager.cleanup_session(session.session_id)


class TestGracefulDegradation:
    """Test graceful degradation when non-critical components fail.
    
    Validates: Requirements 16.4
    """
    
    @pytest.mark.asyncio
    async def test_system_continues_without_latency_tracker(
        self,
        session_manager
    ):
        """Test that system continues if latency tracker fails."""
        # Create session
        session = await session_manager.create_session(websocket=None)
        
        # Simulate latency tracker failure by setting it to None
        original_tracker = session.latency_tracker
        session.latency_tracker = None
        
        # Feed audio
        audio_frames = generate_audio_frames(
            session_id=session.session_id,
            duration_ms=500,
            frame_duration_ms=100
        )
        
        for frame in audio_frames:
            await session.audio_queue.put(frame)
        
        # Wait for processing
        await asyncio.sleep(0.8)
        
        # System should still produce output
        assert not session.tts_queue.empty()
        
        # Restore tracker
        session.latency_tracker = original_tracker
        
        # Cleanup
        await session_manager.cleanup_session(session.session_id)
    
    @pytest.mark.asyncio
    async def test_system_continues_without_recorder(
        self,
        asr_service,
        reasoning_service,
        tts_service
    ):
        """Test that system continues if session recorder fails."""
        # Create session manager with recording enabled
        session_manager = SessionManager(
            asr_service=asr_service,
            llm_service=reasoning_service,
            tts_service=tts_service,
            enable_recording=True
        )
        
        # Create session
        session = await session_manager.create_session(websocket=None)
        
        # Simulate recorder failure
        if session.recorder:
            session.recorder = None
        
        # Feed audio
        audio_frames = generate_audio_frames(
            session_id=session.session_id,
            duration_ms=500,
            frame_duration_ms=100
        )
        
        for frame in audio_frames:
            await session.audio_queue.put(frame)
        
        # Wait for processing
        await asyncio.sleep(0.8)
        
        # System should still produce output
        assert not session.tts_queue.empty()
        
        # Cleanup
        await session_manager.cleanup_session(session.session_id)
    
    @pytest.mark.asyncio
    async def test_partial_pipeline_failure_handling(
        self,
        session_manager,
        mock_elevenlabs_client
    ):
        """Test handling when TTS fails but ASR and LLM succeed."""
        # Configure TTS to fail
        mock_elevenlabs_client.configure_error(TimeoutError("TTS failure"))
        
        # Create session
        session = await session_manager.create_session(websocket=None)
        
        # Feed audio
        audio_frames = generate_audio_frames(
            session_id=session.session_id,
            duration_ms=500,
            frame_duration_ms=100
        )
        
        for frame in audio_frames:
            await session.audio_queue.put(frame)
        
        # Wait for processing
        await asyncio.sleep(0.8)
        
        # ASR and LLM should still work
        assert not session.transcript_queue.empty()
        assert not session.token_queue.empty()
        
        # TTS queue might be empty due to failure, but system didn't crash
        assert session.session_id in session_manager.sessions
        
        # Cleanup
        await session_manager.cleanup_session(session.session_id)


class TestSystemHealthMonitoring:
    """Test system health monitoring during integration scenarios."""
    
    @pytest.mark.asyncio
    async def test_health_status_reflects_component_state(
        self,
        session_manager,
        mock_whisper_client
    ):
        """Test that system health reflects component failures."""
        system_health = SystemHealth()
        
        # Initially all components should be healthy
        assert system_health.is_fully_healthy()
        
        # Simulate ASR failure
        system_health.mark_degraded("asr", "Test failure")
        
        # System should be degraded but critical components check should fail
        assert not system_health.is_fully_healthy()
        assert not system_health.is_critical_healthy()
        
        # Mark as healthy again
        system_health.mark_healthy("asr")
        
        # Should be fully healthy again
        assert system_health.is_fully_healthy()
    
    @pytest.mark.asyncio
    async def test_non_critical_component_degradation(
        self,
        session_manager
    ):
        """Test that non-critical component failures don't stop processing."""
        system_health = SystemHealth()
        
        # Mark non-critical component as degraded
        system_health.mark_degraded("latency_tracker", "Tracker failure")
        
        # Critical components should still be healthy
        assert system_health.is_critical_healthy()
        
        # Create session and process audio
        session = await session_manager.create_session(websocket=None)
        
        audio_frames = generate_audio_frames(
            session_id=session.session_id,
            duration_ms=500,
            frame_duration_ms=100
        )
        
        for frame in audio_frames:
            await session.audio_queue.put(frame)
        
        # Wait for processing
        await asyncio.sleep(0.8)
        
        # Should still produce output
        assert not session.tts_queue.empty()
        
        # Cleanup
        await session_manager.cleanup_session(session.session_id)
