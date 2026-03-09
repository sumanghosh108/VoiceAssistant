"""
Unit tests for test fixtures and mock services.

This test file demonstrates how to use the fixtures and validates
that the mock implementations work correctly.
"""

import asyncio
import pytest
from datetime import datetime

from tests.fixtures.mocks import (
    MockWhisperClient,
    MockGeminiClient,
    MockElevenLabsClient,
    generate_silence,
    generate_sine_wave,
    generate_white_noise,
    generate_audio_frames,
    create_transcript_event,
    create_llm_token_events,
    create_tts_audio_events,
    create_error_event,
    create_mock_whisper_client,
    create_mock_gemini_client,
    create_mock_elevenlabs_client
)
from src.core.events import ErrorType


# =============================================================================
# Mock Whisper Client Tests
# =============================================================================

@pytest.mark.asyncio
async def test_mock_whisper_client_default_response():
    """Test MockWhisperClient returns default response."""
    client = MockWhisperClient()
    
    result = await client.transcribe(b'\x00' * 1000, sample_rate=16000)
    
    assert result["text"] == "Hello world"
    assert result["confidence"] == 0.95
    assert result["is_partial"] is False
    assert client.call_count == 1


@pytest.mark.asyncio
async def test_mock_whisper_client_custom_response():
    """Test MockWhisperClient with custom response."""
    client = MockWhisperClient(
        default_text="Custom text",
        default_confidence=0.85,
        default_partial=True
    )
    
    result = await client.transcribe(b'\x00' * 1000)
    
    assert result["text"] == "Custom text"
    assert result["confidence"] == 0.85
    assert result["is_partial"] is True


@pytest.mark.asyncio
async def test_mock_whisper_client_configure_response():
    """Test configuring response after initialization."""
    client = MockWhisperClient()
    
    client.configure_response("New text", confidence=0.75, partial=True)
    result = await client.transcribe(b'\x00' * 1000)
    
    assert result["text"] == "New text"
    assert result["confidence"] == 0.75
    assert result["is_partial"] is True


@pytest.mark.asyncio
async def test_mock_whisper_client_simulate_error():
    """Test MockWhisperClient error simulation."""
    client = MockWhisperClient(simulate_error=TimeoutError("API timeout"))
    
    with pytest.raises(TimeoutError, match="API timeout"):
        await client.transcribe(b'\x00' * 1000)
    
    assert client.call_count == 1


@pytest.mark.asyncio
async def test_mock_whisper_client_configure_error():
    """Test configuring error after initialization."""
    client = MockWhisperClient()
    
    client.configure_error(ValueError("Invalid audio"))
    
    with pytest.raises(ValueError, match="Invalid audio"):
        await client.transcribe(b'\x00' * 1000)


@pytest.mark.asyncio
async def test_mock_whisper_client_delay():
    """Test MockWhisperClient simulated latency."""
    client = MockWhisperClient(delay_seconds=0.1)
    
    start = datetime.now()
    await client.transcribe(b'\x00' * 1000)
    duration = (datetime.now() - start).total_seconds()
    
    assert duration >= 0.1


@pytest.mark.asyncio
async def test_mock_whisper_client_call_tracking():
    """Test MockWhisperClient tracks calls."""
    client = MockWhisperClient()
    
    await client.transcribe(b'\x00' * 1000, sample_rate=16000)
    await client.transcribe(b'\x00' * 2000, sample_rate=8000)
    
    assert client.call_count == 2
    assert len(client.call_history) == 2
    assert client.call_history[0]["audio_bytes"] == 1000
    assert client.call_history[0]["sample_rate"] == 16000
    assert client.call_history[1]["audio_bytes"] == 2000
    assert client.call_history[1]["sample_rate"] == 8000


@pytest.mark.asyncio
async def test_mock_whisper_client_reset():
    """Test MockWhisperClient reset functionality."""
    client = MockWhisperClient()
    
    await client.transcribe(b'\x00' * 1000)
    assert client.call_count == 1
    
    client.reset()
    assert client.call_count == 0
    assert len(client.call_history) == 0


# =============================================================================
# Mock Gemini Client Tests
# =============================================================================

@pytest.mark.asyncio
async def test_mock_gemini_client_default_response():
    """Test MockGeminiClient returns default tokens."""
    client = MockGeminiClient()
    
    tokens = []
    async for token in client.generate_stream([]):
        tokens.append(token)
    
    assert tokens == ["Hello", " ", "world", "!"]
    assert client.call_count == 1


@pytest.mark.asyncio
async def test_mock_gemini_client_custom_tokens():
    """Test MockGeminiClient with custom tokens."""
    client = MockGeminiClient(default_tokens=["Test", " ", "response"])
    
    tokens = []
    async for token in client.generate_stream([]):
        tokens.append(token)
    
    assert tokens == ["Test", " ", "response"]


@pytest.mark.asyncio
async def test_mock_gemini_client_configure_response():
    """Test configuring tokens after initialization."""
    client = MockGeminiClient()
    
    client.configure_response(["New", " ", "tokens"])
    
    tokens = []
    async for token in client.generate_stream([]):
        tokens.append(token)
    
    assert tokens == ["New", " ", "tokens"]


@pytest.mark.asyncio
async def test_mock_gemini_client_simulate_error():
    """Test MockGeminiClient error simulation."""
    client = MockGeminiClient(simulate_error=TimeoutError("API timeout"))
    
    with pytest.raises(TimeoutError, match="API timeout"):
        async for _ in client.generate_stream([]):
            pass
    
    assert client.call_count == 1


@pytest.mark.asyncio
async def test_mock_gemini_client_delay():
    """Test MockGeminiClient simulated latency."""
    client = MockGeminiClient(delay_seconds=0.1, delay_per_token=0.05)
    
    start = datetime.now()
    tokens = []
    async for token in client.generate_stream([]):
        tokens.append(token)
    duration = (datetime.now() - start).total_seconds()
    
    # Should have initial delay + per-token delays
    # 0.1 + (4 tokens * 0.05) = 0.3 seconds minimum
    assert duration >= 0.3


@pytest.mark.asyncio
async def test_mock_gemini_client_call_tracking():
    """Test MockGeminiClient tracks calls."""
    client = MockGeminiClient()
    
    messages1 = [{"role": "user", "content": "Hello"}]
    messages2 = [{"role": "user", "content": "Hi"}, {"role": "assistant", "content": "Hello"}]
    
    async for _ in client.generate_stream(messages1):
        pass
    async for _ in client.generate_stream(messages2):
        pass
    
    assert client.call_count == 2
    assert len(client.call_history) == 2
    assert client.call_history[0]["message_count"] == 1
    assert client.call_history[1]["message_count"] == 2


# =============================================================================
# Mock ElevenLabs Client Tests
# =============================================================================

@pytest.mark.asyncio
async def test_mock_elevenlabs_client_default_response():
    """Test MockElevenLabsClient returns default chunks."""
    client = MockElevenLabsClient()
    
    chunks = []
    async for chunk in client.synthesize_stream("Test text", "voice_id"):
        chunks.append(chunk)
    
    assert len(chunks) == 3
    assert all(len(chunk) == 1024 for chunk in chunks)
    assert client.call_count == 1


@pytest.mark.asyncio
async def test_mock_elevenlabs_client_custom_chunks():
    """Test MockElevenLabsClient with custom chunks."""
    custom_chunks = [b'chunk1', b'chunk2']
    client = MockElevenLabsClient(default_chunks=custom_chunks)
    
    chunks = []
    async for chunk in client.synthesize_stream("Test", "voice_id"):
        chunks.append(chunk)
    
    assert chunks == custom_chunks


@pytest.mark.asyncio
async def test_mock_elevenlabs_client_configure_response():
    """Test configuring chunks after initialization."""
    client = MockElevenLabsClient()
    
    new_chunks = [b'new1', b'new2', b'new3']
    client.configure_response(new_chunks)
    
    chunks = []
    async for chunk in client.synthesize_stream("Test", "voice_id"):
        chunks.append(chunk)
    
    assert chunks == new_chunks


@pytest.mark.asyncio
async def test_mock_elevenlabs_client_simulate_error():
    """Test MockElevenLabsClient error simulation."""
    client = MockElevenLabsClient(simulate_error=TimeoutError("API timeout"))
    
    with pytest.raises(TimeoutError, match="API timeout"):
        async for _ in client.synthesize_stream("Test", "voice_id"):
            pass
    
    assert client.call_count == 1


@pytest.mark.asyncio
async def test_mock_elevenlabs_client_delay():
    """Test MockElevenLabsClient simulated latency."""
    client = MockElevenLabsClient(delay_seconds=0.1, delay_per_chunk=0.05)
    
    start = datetime.now()
    chunks = []
    async for chunk in client.synthesize_stream("Test", "voice_id"):
        chunks.append(chunk)
    duration = (datetime.now() - start).total_seconds()
    
    # Should have initial delay + per-chunk delays
    # 0.1 + (3 chunks * 0.05) = 0.25 seconds minimum
    assert duration >= 0.25


@pytest.mark.asyncio
async def test_mock_elevenlabs_client_call_tracking():
    """Test MockElevenLabsClient tracks calls."""
    client = MockElevenLabsClient()
    
    async for _ in client.synthesize_stream("First text", "voice1"):
        pass
    async for _ in client.synthesize_stream("Second text", "voice2"):
        pass
    
    assert client.call_count == 2
    assert len(client.call_history) == 2
    assert client.call_history[0]["text"] == "First text"
    assert client.call_history[0]["voice_id"] == "voice1"
    assert client.call_history[1]["text"] == "Second text"
    assert client.call_history[1]["voice_id"] == "voice2"


# =============================================================================
# Audio Data Generator Tests
# =============================================================================

def test_generate_silence():
    """Test silence generation."""
    audio = generate_silence(duration_ms=1000, sample_rate=16000)
    
    # 1 second at 16kHz = 16000 samples * 2 bytes = 32000 bytes
    assert len(audio) == 32000
    assert audio == b'\x00' * 32000


def test_generate_silence_custom_duration():
    """Test silence generation with custom duration."""
    audio = generate_silence(duration_ms=500, sample_rate=16000)
    
    # 0.5 seconds at 16kHz = 8000 samples * 2 bytes = 16000 bytes
    assert len(audio) == 16000


def test_generate_sine_wave():
    """Test sine wave generation."""
    audio = generate_sine_wave(duration_ms=1000, frequency=440.0, sample_rate=16000)
    
    # 1 second at 16kHz = 16000 samples * 2 bytes = 32000 bytes
    assert len(audio) == 32000
    # Should not be all zeros (unlike silence)
    assert audio != b'\x00' * 32000


def test_generate_sine_wave_custom_frequency():
    """Test sine wave generation with custom frequency."""
    audio = generate_sine_wave(duration_ms=100, frequency=880.0, sample_rate=16000)
    
    # 0.1 seconds at 16kHz = 1600 samples * 2 bytes = 3200 bytes
    assert len(audio) == 3200


def test_generate_white_noise():
    """Test white noise generation."""
    audio = generate_white_noise(duration_ms=1000, sample_rate=16000)
    
    # 1 second at 16kHz = 16000 samples * 2 bytes = 32000 bytes
    assert len(audio) == 32000
    # Should not be all zeros (unlike silence)
    assert audio != b'\x00' * 32000


def test_generate_audio_frames_silence():
    """Test audio frame generation with silence."""
    frames = generate_audio_frames(
        session_id="test_session",
        duration_ms=1000,
        frame_duration_ms=100,
        audio_type="silence"
    )
    
    assert len(frames) == 10  # 1000ms / 100ms = 10 frames
    assert all(frame.session_id == "test_session" for frame in frames)
    assert all(frame.sample_rate == 16000 for frame in frames)
    assert all(frame.channels == 1 for frame in frames)
    assert all(len(frame.data) == 3200 for frame in frames)  # 100ms at 16kHz
    assert frames[0].sequence_number == 0
    assert frames[-1].sequence_number == 9


def test_generate_audio_frames_sine():
    """Test audio frame generation with sine wave."""
    frames = generate_audio_frames(
        session_id="test_session",
        duration_ms=500,
        frame_duration_ms=100,
        audio_type="sine"
    )
    
    assert len(frames) == 5
    # Sine wave should not be all zeros
    assert frames[0].data != b'\x00' * 3200


def test_generate_audio_frames_noise():
    """Test audio frame generation with white noise."""
    frames = generate_audio_frames(
        session_id="test_session",
        duration_ms=500,
        frame_duration_ms=100,
        audio_type="noise"
    )
    
    assert len(frames) == 5
    # Noise should not be all zeros
    assert frames[0].data != b'\x00' * 3200


# =============================================================================
# Event Generator Tests
# =============================================================================

def test_create_transcript_event():
    """Test transcript event creation."""
    event = create_transcript_event(
        session_id="test_session",
        text="Hello world",
        partial=False,
        confidence=0.95
    )
    
    assert event.session_id == "test_session"
    assert event.text == "Hello world"
    assert event.partial is False
    assert event.confidence == 0.95
    assert event.audio_duration_ms == 1000


def test_create_transcript_event_defaults():
    """Test transcript event creation with defaults."""
    event = create_transcript_event()
    
    assert event.session_id == "test_session"
    assert event.text == "Hello world"
    assert event.partial is False


def test_create_llm_token_events():
    """Test LLM token event creation."""
    events = create_llm_token_events(
        session_id="test_session",
        tokens=["Hello", " ", "world"]
    )
    
    assert len(events) == 3
    assert events[0].token == "Hello"
    assert events[0].is_first is True
    assert events[0].is_last is False
    assert events[1].is_first is False
    assert events[1].is_last is False
    assert events[2].is_last is True


def test_create_llm_token_events_defaults():
    """Test LLM token event creation with defaults."""
    events = create_llm_token_events()
    
    assert len(events) == 4
    assert events[0].token == "Hello"
    assert events[-1].token == "!"


def test_create_tts_audio_events():
    """Test TTS audio event creation."""
    events = create_tts_audio_events(
        session_id="test_session",
        num_chunks=5,
        chunk_size=512
    )
    
    assert len(events) == 5
    assert all(event.session_id == "test_session" for event in events)
    assert all(len(event.audio_data) == 512 for event in events)
    assert events[0].sequence_number == 0
    assert events[-1].sequence_number == 4
    assert events[-1].is_final is True
    assert all(not event.is_final for event in events[:-1])


def test_create_error_event():
    """Test error event creation."""
    event = create_error_event(
        session_id="test_session",
        component="asr",
        error_type=ErrorType.TIMEOUT,
        message="Timeout error",
        retryable=True
    )
    
    assert event.session_id == "test_session"
    assert event.component == "asr"
    assert event.error_type == ErrorType.TIMEOUT
    assert event.message == "Timeout error"
    assert event.retryable is True


def test_create_error_event_defaults():
    """Test error event creation with defaults."""
    event = create_error_event()
    
    assert event.session_id == "test_session"
    assert event.component == "asr"
    assert event.error_type == ErrorType.API_ERROR


# =============================================================================
# Factory Function Tests
# =============================================================================

def test_create_mock_whisper_client_factory():
    """Test MockWhisperClient factory function."""
    client = create_mock_whisper_client(default_text="Factory test")
    
    assert isinstance(client, MockWhisperClient)
    assert client.default_text == "Factory test"


def test_create_mock_gemini_client_factory():
    """Test MockGeminiClient factory function."""
    client = create_mock_gemini_client(default_tokens=["Test"])
    
    assert isinstance(client, MockGeminiClient)
    assert client.default_tokens == ["Test"]


def test_create_mock_elevenlabs_client_factory():
    """Test MockElevenLabsClient factory function."""
    client = create_mock_elevenlabs_client(default_chunks=[b'test'])
    
    assert isinstance(client, MockElevenLabsClient)
    assert client.default_chunks == [b'test']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
