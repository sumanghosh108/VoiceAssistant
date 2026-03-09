"""
Unit tests for TTS service.

Tests token buffering, phrase detection, audio chunk emission,
timeout handling, and error event emission.
"""

import asyncio
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.tts import TTSService, ElevenLabsClient
from src.core.events import LLMTokenEvent, TTSAudioEvent, ErrorEvent, ErrorType
from src.infrastructure.resilience import CircuitBreaker, CircuitBreakerOpenError
from src.observability.latency import LatencyTracker


@pytest.fixture
def mock_elevenlabs_client():
    """Create mock ElevenLabs client."""
    client = MagicMock(spec=ElevenLabsClient)
    return client


@pytest.fixture
def tts_service(mock_elevenlabs_client):
    """Create TTS service with mock client."""
    with patch('src.tts_service.ElevenLabsClient', return_value=mock_elevenlabs_client):
        service = TTSService(
            api_key="test_key",
            voice_id="test_voice",
            timeout=3.0,
            phrase_buffer_tokens=3  # Small buffer for testing
        )
        service.client = mock_elevenlabs_client
        return service


@pytest.mark.asyncio
async def test_token_buffering_until_phrase_complete(tts_service, mock_elevenlabs_client):
    """Test that tokens are buffered until phrase boundary is reached."""
    # Setup mock to return audio chunks
    async def mock_stream(text, voice_id):
        yield b"audio_chunk_1"
        yield b"audio_chunk_2"
    
    mock_elevenlabs_client.synthesize_stream = mock_stream
    
    # Create queues
    token_queue = asyncio.Queue()
    audio_queue = asyncio.Queue()
    
    # Add tokens without sentence boundary
    await token_queue.put(LLMTokenEvent(
        session_id="test_session",
        token="Hello",
        is_first=True,
        is_last=False,
        timestamp=datetime.now(),
        token_index=0
    ))
    await token_queue.put(LLMTokenEvent(
        session_id="test_session",
        token=" world",
        is_first=False,
        is_last=False,
        timestamp=datetime.now(),
        token_index=1
    ))
    
    # Start processing in background
    process_task = asyncio.create_task(
        tts_service.process_token_stream(token_queue, audio_queue)
    )
    
    # Wait a bit - should not synthesize yet (only 2 tokens, buffer is 3)
    await asyncio.sleep(0.1)
    assert audio_queue.qsize() == 0
    
    # Add token with sentence boundary
    await token_queue.put(LLMTokenEvent(
        session_id="test_session",
        token=".",
        is_first=False,
        is_last=True,
        timestamp=datetime.now(),
        token_index=2
    ))
    
    # Wait for processing
    await asyncio.sleep(0.2)
    
    # Should have synthesized now
    assert audio_queue.qsize() > 0
    
    # Cleanup
    process_task.cancel()
    try:
        await process_task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_phrase_detection_on_sentence_boundary(tts_service, mock_elevenlabs_client):
    """Test that phrase is detected on sentence boundaries (., !, ?, newline)."""
    # Setup mock
    async def mock_stream(text, voice_id):
        yield b"audio_chunk"
    
    mock_elevenlabs_client.synthesize_stream = mock_stream
    
    # Create queues
    token_queue = asyncio.Queue()
    audio_queue = asyncio.Queue()
    
    # Add token with period (sentence boundary)
    await token_queue.put(LLMTokenEvent(
        session_id="test_session",
        token="Hello.",
        is_first=True,
        is_last=True,
        timestamp=datetime.now(),
        token_index=0
    ))
    
    # Start processing
    process_task = asyncio.create_task(
        tts_service.process_token_stream(token_queue, audio_queue)
    )
    
    # Wait for processing
    await asyncio.sleep(0.2)
    
    # Should have synthesized
    assert audio_queue.qsize() > 0
    
    # Cleanup
    process_task.cancel()
    try:
        await process_task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_audio_chunk_emission(tts_service, mock_elevenlabs_client):
    """Test that audio chunks are emitted as TTSAudioEvent objects."""
    # Setup mock to return multiple chunks
    async def mock_stream(text, voice_id):
        yield b"chunk_1"
        yield b"chunk_2"
        yield b"chunk_3"
    
    mock_elevenlabs_client.synthesize_stream = mock_stream
    
    # Create queues
    token_queue = asyncio.Queue()
    audio_queue = asyncio.Queue()
    
    # Add token
    await token_queue.put(LLMTokenEvent(
        session_id="test_session",
        token="Test.",
        is_first=True,
        is_last=True,
        timestamp=datetime.now(),
        token_index=0
    ))
    
    # Start processing
    process_task = asyncio.create_task(
        tts_service.process_token_stream(token_queue, audio_queue)
    )
    
    # Wait for processing
    await asyncio.sleep(0.2)
    
    # Should have emitted audio events
    events = []
    while not audio_queue.empty():
        events.append(await audio_queue.get())
    
    # Should have 3 audio chunks + 1 final marker
    assert len(events) == 4
    
    # Check first 3 are audio chunks
    for i in range(3):
        assert isinstance(events[i], TTSAudioEvent)
        assert events[i].session_id == "test_session"
        assert events[i].audio_data == f"chunk_{i+1}".encode()
        assert events[i].sequence_number == i
        assert events[i].is_final == False
    
    # Check final marker
    assert isinstance(events[3], TTSAudioEvent)
    assert events[3].is_final == True
    assert events[3].audio_data == b""
    
    # Cleanup
    process_task.cancel()
    try:
        await process_task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_timeout_handling(tts_service, mock_elevenlabs_client):
    """Test that timeout errors are handled and error events are emitted."""
    # Setup mock to timeout
    async def mock_stream_timeout(text, voice_id):
        await asyncio.sleep(10)  # Longer than timeout
        yield b"chunk"
    
    mock_elevenlabs_client.synthesize_stream = mock_stream_timeout
    
    # Create queues
    token_queue = asyncio.Queue()
    audio_queue = asyncio.Queue()
    
    # Add token
    await token_queue.put(LLMTokenEvent(
        session_id="test_session",
        token="Test.",
        is_first=True,
        is_last=True,
        timestamp=datetime.now(),
        token_index=0
    ))
    
    # Mock circuit breaker to raise timeout
    async def mock_call_timeout(func, *args, **kwargs):
        raise asyncio.TimeoutError("Timeout")
    
    tts_service.circuit_breaker.call = mock_call_timeout
    
    # Start processing
    process_task = asyncio.create_task(
        tts_service.process_token_stream(token_queue, audio_queue)
    )
    
    # Wait for processing
    await asyncio.sleep(0.2)
    
    # Should have emitted error event
    assert audio_queue.qsize() > 0
    error_event = await audio_queue.get()
    
    assert isinstance(error_event, ErrorEvent)
    assert error_event.component == "tts"
    assert error_event.error_type == ErrorType.TIMEOUT
    assert error_event.retryable == False  # No retry for TTS
    
    # Cleanup
    process_task.cancel()
    try:
        await process_task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_error_event_emission_without_retry(tts_service, mock_elevenlabs_client):
    """Test that errors emit ErrorEvent without retry."""
    # Setup mock to raise error
    async def mock_stream_error(text, voice_id):
        raise Exception("API Error")
    
    mock_elevenlabs_client.synthesize_stream = mock_stream_error
    
    # Create queues
    token_queue = asyncio.Queue()
    audio_queue = asyncio.Queue()
    
    # Add token
    await token_queue.put(LLMTokenEvent(
        session_id="test_session",
        token="Test.",
        is_first=True,
        is_last=True,
        timestamp=datetime.now(),
        token_index=0
    ))
    
    # Mock circuit breaker to propagate error
    async def mock_call_error(func, *args, **kwargs):
        raise Exception("API Error")
    
    tts_service.circuit_breaker.call = mock_call_error
    
    # Start processing
    process_task = asyncio.create_task(
        tts_service.process_token_stream(token_queue, audio_queue)
    )
    
    # Wait for processing
    await asyncio.sleep(0.2)
    
    # Should have emitted error event
    assert audio_queue.qsize() > 0
    error_event = await audio_queue.get()
    
    assert isinstance(error_event, ErrorEvent)
    assert error_event.component == "tts"
    assert error_event.error_type == ErrorType.API_ERROR
    assert error_event.retryable == False  # No retry for TTS
    assert "API Error" in error_event.message
    
    # Cleanup
    process_task.cancel()
    try:
        await process_task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_latency_tracking(tts_service, mock_elevenlabs_client):
    """Test that latency markers are added for tracking."""
    # Setup mock
    async def mock_stream(text, voice_id):
        yield b"audio_chunk"
    
    mock_elevenlabs_client.synthesize_stream = mock_stream
    
    # Create queues and latency tracker
    token_queue = asyncio.Queue()
    audio_queue = asyncio.Queue()
    latency_tracker = LatencyTracker("test_session")
    
    # Add token
    await token_queue.put(LLMTokenEvent(
        session_id="test_session",
        token="Test.",
        is_first=True,
        is_last=True,
        timestamp=datetime.now(),
        token_index=0
    ))
    
    # Start processing with latency tracker
    process_task = asyncio.create_task(
        tts_service.process_token_stream(token_queue, audio_queue, latency_tracker)
    )
    
    # Wait for processing
    await asyncio.sleep(0.2)
    
    # Check latency markers were added
    assert "tts_start" in latency_tracker.markers
    assert "tts_audio_start" in latency_tracker.markers
    
    # Check measurement was recorded
    measurements = latency_tracker.get_measurements()
    assert len(measurements) > 0
    assert any(m.stage == "tts_latency" for m in measurements)
    
    # Cleanup
    process_task.cancel()
    try:
        await process_task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_circuit_breaker_integration(tts_service, mock_elevenlabs_client):
    """Test that circuit breaker is used for API calls."""
    # Setup mock
    async def mock_stream(text, voice_id):
        yield b"audio_chunk"
    
    mock_elevenlabs_client.synthesize_stream = mock_stream
    
    # Create custom circuit breaker to track calls
    circuit_breaker = CircuitBreaker(name="test_tts")
    tts_service.circuit_breaker = circuit_breaker
    
    # Create queues
    token_queue = asyncio.Queue()
    audio_queue = asyncio.Queue()
    
    # Add token
    await token_queue.put(LLMTokenEvent(
        session_id="test_session",
        token="Test.",
        is_first=True,
        is_last=True,
        timestamp=datetime.now(),
        token_index=0
    ))
    
    # Start processing
    process_task = asyncio.create_task(
        tts_service.process_token_stream(token_queue, audio_queue)
    )
    
    # Wait for processing
    await asyncio.sleep(0.2)
    
    # Circuit breaker should have recorded success
    assert circuit_breaker.successes > 0
    
    # Cleanup
    process_task.cancel()
    try:
        await process_task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_empty_text_skipped(tts_service, mock_elevenlabs_client):
    """Test that empty or whitespace-only text is skipped."""
    # Setup mock (should not be called)
    call_count = 0
    
    async def mock_stream(text, voice_id):
        nonlocal call_count
        call_count += 1
        yield b"audio_chunk"
    
    mock_elevenlabs_client.synthesize_stream = mock_stream
    
    # Create queues
    token_queue = asyncio.Queue()
    audio_queue = asyncio.Queue()
    
    # Add empty token
    await token_queue.put(LLMTokenEvent(
        session_id="test_session",
        token="",
        is_first=True,
        is_last=True,
        timestamp=datetime.now(),
        token_index=0
    ))
    
    # Start processing
    process_task = asyncio.create_task(
        tts_service.process_token_stream(token_queue, audio_queue)
    )
    
    # Wait for processing
    await asyncio.sleep(0.2)
    
    # Should not have called API
    assert call_count == 0
    
    # Should not have emitted audio events
    assert audio_queue.qsize() == 0
    
    # Cleanup
    process_task.cancel()
    try:
        await process_task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_sequence_numbers_increment(tts_service, mock_elevenlabs_client):
    """Test that sequence numbers increment correctly across multiple syntheses."""
    # Setup mock
    async def mock_stream(text, voice_id):
        yield b"chunk_1"
        yield b"chunk_2"
    
    mock_elevenlabs_client.synthesize_stream = mock_stream
    
    # Create queues
    token_queue = asyncio.Queue()
    audio_queue = asyncio.Queue()
    
    # Add first phrase
    await token_queue.put(LLMTokenEvent(
        session_id="test_session",
        token="First.",
        is_first=True,
        is_last=False,
        timestamp=datetime.now(),
        token_index=0
    ))
    
    # Add second phrase
    await token_queue.put(LLMTokenEvent(
        session_id="test_session",
        token="Second.",
        is_first=False,
        is_last=True,
        timestamp=datetime.now(),
        token_index=1
    ))
    
    # Start processing
    process_task = asyncio.create_task(
        tts_service.process_token_stream(token_queue, audio_queue)
    )
    
    # Wait for processing
    await asyncio.sleep(0.3)
    
    # Collect events
    events = []
    while not audio_queue.empty():
        events.append(await audio_queue.get())
    
    # Should have events from both syntheses
    assert len(events) > 0
    
    # Check sequence numbers increment
    audio_events = [e for e in events if isinstance(e, TTSAudioEvent) and not e.is_final]
    if len(audio_events) > 1:
        for i in range(len(audio_events) - 1):
            assert audio_events[i+1].sequence_number > audio_events[i].sequence_number
    
    # Cleanup
    process_task.cancel()
    try:
        await process_task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_error_events_passed_through(tts_service):
    """Test that error events from upstream are passed through without processing."""
    # Create queues
    token_queue = asyncio.Queue()
    audio_queue = asyncio.Queue()
    
    # Add error event
    error_event = ErrorEvent(
        session_id="test_session",
        component="llm",
        error_type=ErrorType.API_ERROR,
        message="Upstream error",
        timestamp=datetime.now(),
        retryable=False
    )
    await token_queue.put(error_event)
    
    # Add a token to keep loop running
    await token_queue.put(LLMTokenEvent(
        session_id="test_session",
        token="Test.",
        is_first=True,
        is_last=True,
        timestamp=datetime.now(),
        token_index=0
    ))
    
    # Start processing
    process_task = asyncio.create_task(
        tts_service.process_token_stream(token_queue, audio_queue)
    )
    
    # Wait for processing
    await asyncio.sleep(0.2)
    
    # Error event should be skipped (not in audio queue)
    # Only audio events from the token should be there
    events = []
    while not audio_queue.empty():
        events.append(await audio_queue.get())
    
    # Should not contain the error event (it was skipped)
    error_events = [e for e in events if isinstance(e, ErrorEvent) and e.component == "llm"]
    assert len(error_events) == 0
    
    # Cleanup
    process_task.cancel()
    try:
        await process_task
    except asyncio.CancelledError:
        pass
