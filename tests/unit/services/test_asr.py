"""
Unit tests for ASR Service.

Tests cover:
- Audio buffering and transcription
- Partial and final transcript emission
- Timeout handling
- Error event emission
- Circuit breaker integration
"""

import asyncio
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.asr import ASRService, WhisperClient
from src.core.events import AudioFrame, TranscriptEvent, ErrorEvent, ErrorType
from src.infrastructure.resilience import CircuitBreaker
from src.observability.latency import LatencyTracker


@pytest.fixture
def mock_whisper_client():
    """Create a mock WhisperClient for testing."""
    client = MagicMock(spec=WhisperClient)
    client.transcribe = AsyncMock(return_value={
        "text": "Hello world",
        "confidence": 0.95,
        "is_partial": False
    })
    return client


@pytest.fixture
def asr_service(mock_whisper_client):
    """Create ASRService instance with mocked client."""
    service = ASRService(
        api_key="test_key",
        timeout=3.0,
        buffer_duration_ms=1000
    )
    service.client = mock_whisper_client
    return service


@pytest.fixture
def audio_frame():
    """Create a sample AudioFrame for testing."""
    # 1 second of 16kHz mono audio = 32000 bytes (16-bit PCM)
    audio_data = b'\x00' * 32000
    return AudioFrame(
        session_id="test_session",
        data=audio_data,
        timestamp=datetime.now(),
        sequence_number=1,
        sample_rate=16000,
        channels=1
    )


@pytest.mark.asyncio
async def test_audio_buffering_and_transcription(asr_service, audio_frame, mock_whisper_client):
    """Test that audio is buffered and transcribed when ready."""
    audio_queue = asyncio.Queue()
    transcript_queue = asyncio.Queue()
    
    # Put audio frame in queue
    await audio_queue.put(audio_frame)
    
    # Start processing in background
    task = asyncio.create_task(
        asr_service.process_audio_stream(audio_queue, transcript_queue)
    )
    
    # Wait a bit for processing
    await asyncio.sleep(0.1)
    
    # Cancel the task
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    
    # Verify transcription was called
    mock_whisper_client.transcribe.assert_called_once()
    
    # Verify transcript event was emitted
    assert not transcript_queue.empty()
    event = await transcript_queue.get()
    assert isinstance(event, TranscriptEvent)
    assert event.text == "Hello world"
    assert event.confidence == 0.95


@pytest.mark.asyncio
async def test_partial_and_final_transcript_emission(asr_service, audio_frame, mock_whisper_client):
    """Test emission of partial and final transcripts."""
    # Configure mock to return partial result
    mock_whisper_client.transcribe.return_value = {
        "text": "Hello",
        "confidence": 0.85,
        "is_partial": True
    }
    
    audio_queue = asyncio.Queue()
    transcript_queue = asyncio.Queue()
    
    await audio_queue.put(audio_frame)
    
    task = asyncio.create_task(
        asr_service.process_audio_stream(audio_queue, transcript_queue)
    )
    
    await asyncio.sleep(0.1)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    
    # Verify partial transcript
    event = await transcript_queue.get()
    assert isinstance(event, TranscriptEvent)
    assert event.partial is True
    assert event.text == "Hello"


@pytest.mark.asyncio
async def test_timeout_handling(asr_service, audio_frame, mock_whisper_client):
    """Test that timeouts are handled and error events are emitted."""
    # Configure mock to timeout
    mock_whisper_client.transcribe.side_effect = asyncio.TimeoutError("API timeout")
    
    audio_queue = asyncio.Queue()
    transcript_queue = asyncio.Queue()
    
    await audio_queue.put(audio_frame)
    
    task = asyncio.create_task(
        asr_service.process_audio_stream(audio_queue, transcript_queue)
    )
    
    await asyncio.sleep(0.1)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    
    # Verify error event was emitted
    assert not transcript_queue.empty()
    event = await transcript_queue.get()
    assert isinstance(event, ErrorEvent)
    assert event.error_type == ErrorType.TIMEOUT
    assert event.component == "asr"
    assert event.retryable is True


@pytest.mark.asyncio
async def test_error_event_emission(asr_service, audio_frame, mock_whisper_client):
    """Test that API errors result in error events."""
    # Configure mock to raise an error
    mock_whisper_client.transcribe.side_effect = Exception("API error")
    
    audio_queue = asyncio.Queue()
    transcript_queue = asyncio.Queue()
    
    await audio_queue.put(audio_frame)
    
    task = asyncio.create_task(
        asr_service.process_audio_stream(audio_queue, transcript_queue)
    )
    
    await asyncio.sleep(0.1)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    
    # Verify error event was emitted
    assert not transcript_queue.empty()
    event = await transcript_queue.get()
    assert isinstance(event, ErrorEvent)
    assert event.error_type == ErrorType.API_ERROR
    assert event.component == "asr"


@pytest.mark.asyncio
async def test_latency_tracking(asr_service, audio_frame, mock_whisper_client):
    """Test that latency markers are recorded."""
    audio_queue = asyncio.Queue()
    transcript_queue = asyncio.Queue()
    latency_tracker = LatencyTracker("test_session")
    
    await audio_queue.put(audio_frame)
    
    task = asyncio.create_task(
        asr_service.process_audio_stream(
            audio_queue,
            transcript_queue,
            latency_tracker
        )
    )
    
    await asyncio.sleep(0.1)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    
    # Verify latency markers were recorded
    assert "audio_received_1" in latency_tracker.markers
    assert "transcript_start" in latency_tracker.markers
    assert "transcript_emitted" in latency_tracker.markers
    
    # Verify latency measurement was recorded
    measurements = latency_tracker.get_measurements()
    assert len(measurements) > 0
    assert measurements[0].stage == "asr_latency"


@pytest.mark.asyncio
async def test_circuit_breaker_integration(audio_frame):
    """Test that circuit breaker is used for API calls."""
    circuit_breaker = CircuitBreaker(name="test_asr")
    
    asr_service = ASRService(
        api_key="test_key",
        timeout=3.0,
        buffer_duration_ms=1000,
        circuit_breaker=circuit_breaker
    )
    
    # Mock the client
    mock_client = MagicMock(spec=WhisperClient)
    mock_client.transcribe = AsyncMock(return_value={
        "text": "Test",
        "confidence": 0.9,
        "is_partial": False
    })
    asr_service.client = mock_client
    
    audio_queue = asyncio.Queue()
    transcript_queue = asyncio.Queue()
    
    await audio_queue.put(audio_frame)
    
    task = asyncio.create_task(
        asr_service.process_audio_stream(audio_queue, transcript_queue)
    )
    
    await asyncio.sleep(0.1)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    
    # Verify circuit breaker recorded success
    assert circuit_breaker.successes > 0


@pytest.mark.asyncio
async def test_multiple_audio_frames_buffering(asr_service, mock_whisper_client):
    """Test buffering of multiple small audio frames."""
    audio_queue = asyncio.Queue()
    transcript_queue = asyncio.Queue()
    
    # Create multiple small frames that together make 1 second
    for i in range(4):
        frame = AudioFrame(
            session_id="test_session",
            data=b'\x00' * 8000,  # 250ms of audio each
            timestamp=datetime.now(),
            sequence_number=i,
            sample_rate=16000,
            channels=1
        )
        await audio_queue.put(frame)
    
    task = asyncio.create_task(
        asr_service.process_audio_stream(audio_queue, transcript_queue)
    )
    
    await asyncio.sleep(0.2)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    
    # Should have called transcribe once after buffering all frames
    assert mock_whisper_client.transcribe.call_count >= 1
