"""
Integration test examples using test fixtures.

This file demonstrates how to use the test fixtures for integration testing
of the voice assistant services. These examples show realistic test scenarios
that combine multiple components.
"""

import asyncio
import pytest
from datetime import datetime

from tests.fixtures.mocks import (
    MockWhisperClient,
    MockGeminiClient,
    MockElevenLabsClient,
    generate_audio_frames,
    create_transcript_event,
    create_llm_token_events
)
from src.services.asr import ASRService
from src.services.llm import ReasoningService
from src.services.tts import TTSService
from src.observability.latency import LatencyTracker
from src.core.events import ErrorType


# =============================================================================
# ASR Service Integration Tests
# =============================================================================

@pytest.mark.asyncio
async def test_asr_service_with_mock_client():
    """Test ASR service end-to-end with mock Whisper client."""
    # Setup
    asr_service = ASRService(api_key="test_key", buffer_duration_ms=1000)
    mock_client = MockWhisperClient(
        default_text="This is a test transcription",
        default_confidence=0.92
    )
    asr_service.client = mock_client
    
    # Create test audio frames (1 second of audio)
    frames = generate_audio_frames(
        session_id="test_session",
        duration_ms=1000,
        frame_duration_ms=100,
        audio_type="sine"
    )
    
    # Create queues
    audio_queue = asyncio.Queue()
    transcript_queue = asyncio.Queue()
    latency_tracker = LatencyTracker("test_session")
    
    # Add frames to queue
    for frame in frames:
        await audio_queue.put(frame)
    
    # Start processing
    task = asyncio.create_task(
        asr_service.process_audio_stream(
            audio_queue,
            transcript_queue,
            latency_tracker
        )
    )
    
    # Wait for processing
    await asyncio.sleep(0.2)
    
    # Verify results
    assert not transcript_queue.empty()
    transcript = await transcript_queue.get()
    assert transcript.text == "This is a test transcription"
    assert transcript.confidence == 0.92
    assert transcript.session_id == "test_session"
    
    # Verify latency tracking
    measurements = latency_tracker.get_measurements()
    assert len(measurements) > 0
    assert any(m.stage == "asr_latency" for m in measurements)
    
    # Verify mock was called
    assert mock_client.call_count == 1
    
    # Cleanup
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_asr_service_timeout_handling():
    """Test ASR service handles timeouts correctly."""
    # Setup with timeout error
    asr_service = ASRService(api_key="test_key", timeout=1.0)
    mock_client = MockWhisperClient(
        simulate_error=asyncio.TimeoutError("API timeout")
    )
    asr_service.client = mock_client
    
    # Create test audio
    frames = generate_audio_frames(
        session_id="test_session",
        duration_ms=1000,
        audio_type="silence"
    )
    
    # Create queues
    audio_queue = asyncio.Queue()
    transcript_queue = asyncio.Queue()
    
    for frame in frames:
        await audio_queue.put(frame)
    
    # Start processing
    task = asyncio.create_task(
        asr_service.process_audio_stream(audio_queue, transcript_queue)
    )
    
    # Wait for processing
    await asyncio.sleep(0.2)
    
    # Verify error event was emitted
    assert not transcript_queue.empty()
    error_event = await transcript_queue.get()
    assert error_event.error_type == ErrorType.TIMEOUT
    assert error_event.component == "asr"
    assert error_event.retryable is True
    
    # Cleanup
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


# =============================================================================
# Reasoning Service Integration Tests
# =============================================================================

@pytest.mark.asyncio
async def test_reasoning_service_with_mock_client():
    """Test reasoning service end-to-end with mock Gemini client."""
    # Setup
    reasoning_service = ReasoningService(api_key="test_key")
    mock_client = MockGeminiClient(
        default_tokens=["The", " answer", " is", " 42", "."]
    )
    reasoning_service.client = mock_client
    
    # Create test transcript
    transcript = create_transcript_event(
        session_id="test_session",
        text="What is the answer?",
        partial=False
    )
    
    # Create queues
    transcript_queue = asyncio.Queue()
    token_queue = asyncio.Queue()
    latency_tracker = LatencyTracker("test_session")
    
    await transcript_queue.put(transcript)
    
    # Start processing
    task = asyncio.create_task(
        reasoning_service.process_transcript_stream(
            transcript_queue,
            token_queue,
            latency_tracker
        )
    )
    
    # Wait for processing
    await asyncio.sleep(0.2)
    
    # Collect tokens
    tokens = []
    while not token_queue.empty():
        event = await token_queue.get()
        tokens.append(event.token)
    
    # Verify results (includes empty final token)
    assert tokens == ["The", " answer", " is", " 42", ".", ""]
    
    # Verify latency tracking
    measurements = latency_tracker.get_measurements()
    assert any(m.stage == "llm_first_token_latency" for m in measurements)
    
    # Cleanup
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_reasoning_service_conversation_context():
    """Test reasoning service maintains conversation context."""
    # Setup
    reasoning_service = ReasoningService(api_key="test_key")
    mock_client = MockGeminiClient(default_tokens=["Response"])
    reasoning_service.client = mock_client
    
    session_id = "test_session"
    
    # First interaction
    transcript1 = create_transcript_event(
        session_id=session_id,
        text="Hello",
        partial=False
    )
    
    transcript_queue = asyncio.Queue()
    token_queue = asyncio.Queue()
    
    await transcript_queue.put(transcript1)
    
    task = asyncio.create_task(
        reasoning_service.process_transcript_stream(
            transcript_queue,
            token_queue
        )
    )
    
    await asyncio.sleep(0.2)
    
    # Verify context was created
    context = reasoning_service.get_context(session_id)
    assert len(context.messages) == 2  # User + assistant
    assert context.messages[0].role == "user"
    assert context.messages[0].content == "Hello"
    
    # Second interaction
    transcript2 = create_transcript_event(
        session_id=session_id,
        text="How are you?",
        partial=False
    )
    
    await transcript_queue.put(transcript2)
    await asyncio.sleep(0.2)
    
    # Verify context was updated
    context = reasoning_service.get_context(session_id)
    assert len(context.messages) == 4  # 2 turns
    
    # Cleanup
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


# =============================================================================
# TTS Service Integration Tests
# =============================================================================

@pytest.mark.asyncio
async def test_tts_service_with_mock_client():
    """Test TTS service end-to-end with mock ElevenLabs client."""
    # Setup
    tts_service = TTSService(
        api_key="test_key",
        voice_id="test_voice",
        phrase_buffer_tokens=3
    )
    mock_client = MockElevenLabsClient(
        default_chunks=[b'audio_chunk_1', b'audio_chunk_2', b'audio_chunk_3']
    )
    tts_service.client = mock_client
    
    # Create test token events
    token_events = create_llm_token_events(
        session_id="test_session",
        tokens=["Hello", " ", "world", "."]
    )
    
    # Create queues
    token_queue = asyncio.Queue()
    audio_queue = asyncio.Queue()
    latency_tracker = LatencyTracker("test_session")
    
    for event in token_events:
        await token_queue.put(event)
    
    # Start processing
    task = asyncio.create_task(
        tts_service.process_token_stream(
            token_queue,
            audio_queue,
            latency_tracker
        )
    )
    
    # Wait for processing
    await asyncio.sleep(0.3)
    
    # Collect audio chunks
    chunks = []
    while not audio_queue.empty():
        event = await audio_queue.get()
        if event.audio_data:  # Skip empty final marker
            chunks.append(event.audio_data)
    
    # Verify results - TTS synthesizes twice (once for first 3 tokens, once for last token with period)
    # Each synthesis produces 3 chunks, so we get 6 total
    assert len(chunks) == 6
    assert chunks[0] == b'audio_chunk_1'
    assert chunks[1] == b'audio_chunk_2'
    assert chunks[2] == b'audio_chunk_3'
    
    # Verify latency tracking
    measurements = latency_tracker.get_measurements()
    assert any(m.stage == "tts_latency" for m in measurements)
    
    # Verify mock was called twice (once for "Hello world", once for ".")
    assert mock_client.call_count == 2
    
    # Cleanup
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_tts_service_phrase_buffering():
    """Test TTS service buffers tokens until phrase boundary."""
    # Setup with small buffer
    tts_service = TTSService(
        api_key="test_key",
        voice_id="test_voice",
        phrase_buffer_tokens=5  # Buffer 5 tokens before synthesizing
    )
    mock_client = MockElevenLabsClient(default_chunks=[b'audio'])
    tts_service.client = mock_client
    
    # Create tokens without sentence boundary
    token_events = create_llm_token_events(
        session_id="test_session",
        tokens=["One", " ", "two", " ", "three"]  # 5 tokens, no period
    )
    
    # Create queues
    token_queue = asyncio.Queue()
    audio_queue = asyncio.Queue()
    
    # Add first 3 tokens
    for event in token_events[:3]:
        await token_queue.put(event)
    
    # Start processing
    task = asyncio.create_task(
        tts_service.process_token_stream(token_queue, audio_queue)
    )
    
    # Wait briefly - should not synthesize yet (only 3 tokens)
    await asyncio.sleep(0.1)
    assert audio_queue.qsize() == 0
    
    # Add remaining tokens to reach buffer size
    for event in token_events[3:]:
        await token_queue.put(event)
    
    # Wait for processing
    await asyncio.sleep(0.2)
    
    # Now should have synthesized
    assert audio_queue.qsize() > 0
    
    # Cleanup
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


# =============================================================================
# Multi-Service Pipeline Tests
# =============================================================================

@pytest.mark.asyncio
async def test_full_pipeline_simulation():
    """Test simulated full pipeline: ASR -> LLM -> TTS."""
    # Setup all services with mocks
    asr_service = ASRService(api_key="test_key")
    asr_mock = MockWhisperClient(default_text="Hello assistant")
    asr_service.client = asr_mock
    
    reasoning_service = ReasoningService(api_key="test_key")
    llm_mock = MockGeminiClient(default_tokens=["Hello", " ", "user", "!"])
    reasoning_service.client = llm_mock
    
    tts_service = TTSService(api_key="test_key", voice_id="test_voice")
    tts_mock = MockElevenLabsClient(default_chunks=[b'audio1', b'audio2'])
    tts_service.client = tts_mock
    
    # Create pipeline queues
    audio_queue = asyncio.Queue()
    transcript_queue = asyncio.Queue()
    token_queue = asyncio.Queue()
    tts_audio_queue = asyncio.Queue()
    
    # Generate test audio
    frames = generate_audio_frames(
        session_id="test_session",
        duration_ms=1000,
        audio_type="sine"
    )
    
    for frame in frames:
        await audio_queue.put(frame)
    
    # Start all services
    asr_task = asyncio.create_task(
        asr_service.process_audio_stream(audio_queue, transcript_queue)
    )
    llm_task = asyncio.create_task(
        reasoning_service.process_transcript_stream(transcript_queue, token_queue)
    )
    tts_task = asyncio.create_task(
        tts_service.process_token_stream(token_queue, tts_audio_queue)
    )
    
    # Wait for pipeline to process
    await asyncio.sleep(0.5)
    
    # Verify each stage
    assert asr_mock.call_count > 0, "ASR should have been called"
    assert llm_mock.call_count > 0, "LLM should have been called"
    assert tts_mock.call_count > 0, "TTS should have been called"
    
    # Verify final audio output
    assert not tts_audio_queue.empty(), "Should have audio output"
    
    # Cleanup
    asr_task.cancel()
    llm_task.cancel()
    tts_task.cancel()
    try:
        await asyncio.gather(asr_task, llm_task, tts_task)
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_pipeline_with_latency_tracking():
    """Test full pipeline with comprehensive latency tracking."""
    # Setup services
    asr_service = ASRService(api_key="test_key")
    asr_mock = MockWhisperClient(
        default_text="Test",
        delay_seconds=0.05  # Simulate 50ms ASR latency
    )
    asr_service.client = asr_mock
    
    reasoning_service = ReasoningService(api_key="test_key")
    llm_mock = MockGeminiClient(
        default_tokens=["Response"],
        delay_seconds=0.03  # Simulate 30ms first token latency
    )
    reasoning_service.client = llm_mock
    
    tts_service = TTSService(api_key="test_key", voice_id="test_voice")
    tts_mock = MockElevenLabsClient(
        default_chunks=[b'audio'],
        delay_seconds=0.04  # Simulate 40ms TTS latency
    )
    tts_service.client = tts_mock
    
    # Create latency tracker
    latency_tracker = LatencyTracker("test_session")
    
    # Create queues
    audio_queue = asyncio.Queue()
    transcript_queue = asyncio.Queue()
    token_queue = asyncio.Queue()
    tts_audio_queue = asyncio.Queue()
    
    # Generate audio
    frames = generate_audio_frames(
        session_id="test_session",
        duration_ms=1000,
        audio_type="silence"
    )
    
    for frame in frames:
        await audio_queue.put(frame)
    
    # Start pipeline with latency tracking
    asr_task = asyncio.create_task(
        asr_service.process_audio_stream(
            audio_queue,
            transcript_queue,
            latency_tracker
        )
    )
    llm_task = asyncio.create_task(
        reasoning_service.process_transcript_stream(
            transcript_queue,
            token_queue,
            latency_tracker
        )
    )
    tts_task = asyncio.create_task(
        tts_service.process_token_stream(
            token_queue,
            tts_audio_queue,
            latency_tracker
        )
    )
    
    # Wait for processing
    await asyncio.sleep(0.5)
    
    # Verify latency measurements
    measurements = latency_tracker.get_measurements()
    assert len(measurements) > 0
    
    # Check for expected latency stages
    stages = [m.stage for m in measurements]
    assert "asr_latency" in stages
    assert "llm_first_token_latency" in stages
    assert "tts_latency" in stages
    
    # Cleanup
    asr_task.cancel()
    llm_task.cancel()
    tts_task.cancel()
    try:
        await asyncio.gather(asr_task, llm_task, tts_task)
    except asyncio.CancelledError:
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
