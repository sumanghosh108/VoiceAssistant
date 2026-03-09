"""
Test fixtures and mock services for the real-time voice assistant.

This module provides:
- Mock Whisper API client for ASR testing
- Mock Gemini API client for LLM testing
- Mock ElevenLabs API client for TTS testing
- Test audio data generators
- Reusable fixtures for common test scenarios

Requirements: 7.3
"""

import asyncio
from datetime import datetime
from typing import AsyncIterator, Optional, List, Dict, Any
from unittest.mock import AsyncMock, MagicMock
import struct
import math

from src.core.events import (
    AudioFrame,
    TranscriptEvent,
    LLMTokenEvent,
    TTSAudioEvent,
    ErrorEvent,
    ErrorType
)


# =============================================================================
# Mock API Clients
# =============================================================================

class MockWhisperClient:
    """Mock Whisper API client for testing ASR service.
    
    This mock allows configuring responses, simulating errors, and tracking calls.
    """
    
    def __init__(
        self,
        default_text: str = "Hello world",
        default_confidence: float = 0.95,
        default_partial: bool = False,
        simulate_error: Optional[Exception] = None,
        delay_seconds: float = 0.0
    ):
        """Initialize mock Whisper client.
        
        Args:
            default_text: Default transcription text to return
            default_confidence: Default confidence score (0.0-1.0)
            default_partial: Whether to return partial results by default
            simulate_error: Exception to raise instead of returning results
            delay_seconds: Simulated API latency in seconds
        """
        self.api_key = "mock_whisper_key"
        self.default_text = default_text
        self.default_confidence = default_confidence
        self.default_partial = default_partial
        self.simulate_error = simulate_error
        self.delay_seconds = delay_seconds
        
        # Track calls for verification
        self.call_count = 0
        self.call_history: List[Dict[str, Any]] = []
        
    async def transcribe(
        self,
        audio_data: bytes,
        sample_rate: int = 16000
    ) -> dict:
        """Mock transcribe method.
        
        Args:
            audio_data: Raw PCM audio bytes
            sample_rate: Audio sample rate in Hz
            
        Returns:
            Dictionary with transcription results
            
        Raises:
            Exception: If simulate_error is set
        """
        # Track call
        self.call_count += 1
        self.call_history.append({
            "audio_bytes": len(audio_data),
            "sample_rate": sample_rate,
            "timestamp": datetime.now()
        })
        
        # Simulate API latency
        if self.delay_seconds > 0:
            await asyncio.sleep(self.delay_seconds)
        
        # Simulate error if configured
        if self.simulate_error:
            raise self.simulate_error
        
        # Return mock result
        return {
            "text": self.default_text,
            "confidence": self.default_confidence,
            "is_partial": self.default_partial
        }
    
    def configure_response(
        self,
        text: str,
        confidence: float = 0.95,
        partial: bool = False
    ) -> None:
        """Configure the response for subsequent calls.
        
        Args:
            text: Transcription text to return
            confidence: Confidence score (0.0-1.0)
            partial: Whether to return partial results
        """
        self.default_text = text
        self.default_confidence = confidence
        self.default_partial = partial
    
    def configure_error(self, error: Exception) -> None:
        """Configure an error to raise on subsequent calls.
        
        Args:
            error: Exception to raise
        """
        self.simulate_error = error
    
    def reset(self) -> None:
        """Reset call tracking."""
        self.call_count = 0
        self.call_history.clear()


class MockGeminiClient:
    """Mock Gemini API client for testing LLM service.
    
    This mock allows configuring streaming responses, simulating errors, and tracking calls.
    """
    
    def __init__(
        self,
        default_tokens: Optional[List[str]] = None,
        simulate_error: Optional[Exception] = None,
        delay_seconds: float = 0.0,
        delay_per_token: float = 0.0
    ):
        """Initialize mock Gemini client.
        
        Args:
            default_tokens: List of tokens to stream (default: ["Hello", " ", "world", "!"])
            simulate_error: Exception to raise instead of streaming tokens
            delay_seconds: Simulated API latency before first token
            delay_per_token: Simulated delay between tokens
        """
        self.api_key = "mock_gemini_key"
        self.model = "gemini-pro"
        self.default_tokens = default_tokens or ["Hello", " ", "world", "!"]
        self.simulate_error = simulate_error
        self.delay_seconds = delay_seconds
        self.delay_per_token = delay_per_token
        
        # Track calls for verification
        self.call_count = 0
        self.call_history: List[Dict[str, Any]] = []
        
    async def generate_stream(
        self,
        messages: list,
    ) -> AsyncIterator[str]:
        """Mock streaming generation method.
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys
            
        Yields:
            Individual tokens from the streaming response
            
        Raises:
            Exception: If simulate_error is set
        """
        # Track call
        self.call_count += 1
        self.call_history.append({
            "message_count": len(messages),
            "timestamp": datetime.now()
        })
        
        # Simulate initial API latency
        if self.delay_seconds > 0:
            await asyncio.sleep(self.delay_seconds)
        
        # Simulate error if configured
        if self.simulate_error:
            raise self.simulate_error
        
        # Stream tokens
        for token in self.default_tokens:
            yield token
            
            # Simulate per-token delay
            if self.delay_per_token > 0:
                await asyncio.sleep(self.delay_per_token)
    
    def configure_response(self, tokens: List[str]) -> None:
        """Configure the tokens to stream on subsequent calls.
        
        Args:
            tokens: List of tokens to stream
        """
        self.default_tokens = tokens
    
    def configure_error(self, error: Exception) -> None:
        """Configure an error to raise on subsequent calls.
        
        Args:
            error: Exception to raise
        """
        self.simulate_error = error
    
    def reset(self) -> None:
        """Reset call tracking."""
        self.call_count = 0
        self.call_history.clear()


class MockElevenLabsClient:
    """Mock ElevenLabs API client for testing TTS service.
    
    This mock allows configuring audio chunk responses, simulating errors, and tracking calls.
    """
    
    def __init__(
        self,
        default_chunks: Optional[List[bytes]] = None,
        simulate_error: Optional[Exception] = None,
        delay_seconds: float = 0.0,
        delay_per_chunk: float = 0.0
    ):
        """Initialize mock ElevenLabs client.
        
        Args:
            default_chunks: List of audio chunks to stream (default: 3 chunks of 1024 bytes)
            simulate_error: Exception to raise instead of streaming audio
            delay_seconds: Simulated API latency before first chunk
            delay_per_chunk: Simulated delay between chunks
        """
        self.api_key = "mock_elevenlabs_key"
        self.default_chunks = default_chunks or [
            b'\x00' * 1024,  # Chunk 1
            b'\x00' * 1024,  # Chunk 2
            b'\x00' * 1024,  # Chunk 3
        ]
        self.simulate_error = simulate_error
        self.delay_seconds = delay_seconds
        self.delay_per_chunk = delay_per_chunk
        
        # Track calls for verification
        self.call_count = 0
        self.call_history: List[Dict[str, Any]] = []
        
    async def synthesize_stream(
        self,
        text: str,
        voice_id: str
    ) -> AsyncIterator[bytes]:
        """Mock streaming synthesis method.
        
        Args:
            text: Text to synthesize
            voice_id: ElevenLabs voice ID
            
        Yields:
            Audio chunks as bytes (PCM format)
            
        Raises:
            Exception: If simulate_error is set
        """
        # Track call
        self.call_count += 1
        self.call_history.append({
            "text": text,
            "text_length": len(text),
            "voice_id": voice_id,
            "timestamp": datetime.now()
        })
        
        # Simulate initial API latency
        if self.delay_seconds > 0:
            await asyncio.sleep(self.delay_seconds)
        
        # Simulate error if configured
        if self.simulate_error:
            raise self.simulate_error
        
        # Stream audio chunks
        for chunk in self.default_chunks:
            yield chunk
            
            # Simulate per-chunk delay
            if self.delay_per_chunk > 0:
                await asyncio.sleep(self.delay_per_chunk)
    
    def configure_response(self, chunks: List[bytes]) -> None:
        """Configure the audio chunks to stream on subsequent calls.
        
        Args:
            chunks: List of audio chunks to stream
        """
        self.default_chunks = chunks
    
    def configure_error(self, error: Exception) -> None:
        """Configure an error to raise on subsequent calls.
        
        Args:
            error: Exception to raise
        """
        self.simulate_error = error
    
    def reset(self) -> None:
        """Reset call tracking."""
        self.call_count = 0
        self.call_history.clear()


# =============================================================================
# Test Audio Data Generators
# =============================================================================

def generate_silence(
    duration_ms: int,
    sample_rate: int = 16000,
    channels: int = 1
) -> bytes:
    """Generate silent audio data (all zeros).
    
    Args:
        duration_ms: Duration in milliseconds
        sample_rate: Sample rate in Hz (default: 16000)
        channels: Number of audio channels (default: 1)
        
    Returns:
        Raw PCM audio bytes (16-bit signed integers)
    """
    num_samples = (sample_rate * duration_ms) // 1000
    # 16-bit PCM: 2 bytes per sample
    return b'\x00' * (num_samples * 2 * channels)


def generate_sine_wave(
    duration_ms: int,
    frequency: float = 440.0,
    sample_rate: int = 16000,
    amplitude: float = 0.5
) -> bytes:
    """Generate a sine wave audio signal.
    
    Args:
        duration_ms: Duration in milliseconds
        frequency: Frequency in Hz (default: 440.0 - A4 note)
        sample_rate: Sample rate in Hz (default: 16000)
        amplitude: Amplitude (0.0-1.0, default: 0.5)
        
    Returns:
        Raw PCM audio bytes (16-bit signed integers)
    """
    num_samples = (sample_rate * duration_ms) // 1000
    samples = []
    
    for i in range(num_samples):
        # Generate sine wave sample
        t = i / sample_rate
        sample = amplitude * math.sin(2 * math.pi * frequency * t)
        
        # Convert to 16-bit signed integer
        sample_int = int(sample * 32767)
        sample_int = max(-32768, min(32767, sample_int))  # Clamp
        
        # Pack as 16-bit little-endian
        samples.append(struct.pack('<h', sample_int))
    
    return b''.join(samples)


def generate_white_noise(
    duration_ms: int,
    sample_rate: int = 16000,
    amplitude: float = 0.3
) -> bytes:
    """Generate white noise audio signal.
    
    Args:
        duration_ms: Duration in milliseconds
        sample_rate: Sample rate in Hz (default: 16000)
        amplitude: Amplitude (0.0-1.0, default: 0.3)
        
    Returns:
        Raw PCM audio bytes (16-bit signed integers)
    """
    import random
    
    num_samples = (sample_rate * duration_ms) // 1000
    samples = []
    
    for _ in range(num_samples):
        # Generate random sample
        sample = amplitude * (random.random() * 2 - 1)  # Range: -amplitude to +amplitude
        
        # Convert to 16-bit signed integer
        sample_int = int(sample * 32767)
        sample_int = max(-32768, min(32767, sample_int))  # Clamp
        
        # Pack as 16-bit little-endian
        samples.append(struct.pack('<h', sample_int))
    
    return b''.join(samples)


def generate_audio_frames(
    session_id: str,
    duration_ms: int,
    frame_duration_ms: int = 100,
    audio_type: str = "silence",
    sample_rate: int = 16000
) -> List[AudioFrame]:
    """Generate a list of AudioFrame objects for testing.
    
    Args:
        session_id: Session identifier
        duration_ms: Total duration in milliseconds
        frame_duration_ms: Duration of each frame in milliseconds (default: 100)
        audio_type: Type of audio to generate: "silence", "sine", or "noise" (default: "silence")
        sample_rate: Sample rate in Hz (default: 16000)
        
    Returns:
        List of AudioFrame objects
    """
    frames = []
    num_frames = duration_ms // frame_duration_ms
    
    for i in range(num_frames):
        # Generate audio data based on type
        if audio_type == "sine":
            audio_data = generate_sine_wave(frame_duration_ms, sample_rate=sample_rate)
        elif audio_type == "noise":
            audio_data = generate_white_noise(frame_duration_ms, sample_rate=sample_rate)
        else:  # silence
            audio_data = generate_silence(frame_duration_ms, sample_rate=sample_rate)
        
        # Create AudioFrame
        frame = AudioFrame(
            session_id=session_id,
            data=audio_data,
            timestamp=datetime.now(),
            sequence_number=i,
            sample_rate=sample_rate,
            channels=1
        )
        frames.append(frame)
    
    return frames


# =============================================================================
# Event Generators
# =============================================================================

def create_transcript_event(
    session_id: str = "test_session",
    text: str = "Hello world",
    partial: bool = False,
    confidence: float = 0.95,
    audio_duration_ms: int = 1000
) -> TranscriptEvent:
    """Create a TranscriptEvent for testing.
    
    Args:
        session_id: Session identifier
        text: Transcription text
        partial: Whether this is a partial result
        confidence: Confidence score (0.0-1.0)
        audio_duration_ms: Duration of audio that was transcribed
        
    Returns:
        TranscriptEvent object
    """
    return TranscriptEvent(
        session_id=session_id,
        text=text,
        partial=partial,
        confidence=confidence,
        timestamp=datetime.now(),
        audio_duration_ms=audio_duration_ms
    )


def create_llm_token_events(
    session_id: str = "test_session",
    tokens: Optional[List[str]] = None
) -> List[LLMTokenEvent]:
    """Create a list of LLMTokenEvent objects for testing.
    
    Args:
        session_id: Session identifier
        tokens: List of tokens (default: ["Hello", " ", "world", "!"])
        
    Returns:
        List of LLMTokenEvent objects
    """
    if tokens is None:
        tokens = ["Hello", " ", "world", "!"]
    
    events = []
    for i, token in enumerate(tokens):
        event = LLMTokenEvent(
            session_id=session_id,
            token=token,
            is_first=(i == 0),
            is_last=(i == len(tokens) - 1),
            timestamp=datetime.now(),
            token_index=i
        )
        events.append(event)
    
    return events


def create_tts_audio_events(
    session_id: str = "test_session",
    num_chunks: int = 3,
    chunk_size: int = 1024
) -> List[TTSAudioEvent]:
    """Create a list of TTSAudioEvent objects for testing.
    
    Args:
        session_id: Session identifier
        num_chunks: Number of audio chunks to create
        chunk_size: Size of each chunk in bytes
        
    Returns:
        List of TTSAudioEvent objects
    """
    events = []
    for i in range(num_chunks):
        event = TTSAudioEvent(
            session_id=session_id,
            audio_data=b'\x00' * chunk_size,
            timestamp=datetime.now(),
            sequence_number=i,
            is_final=(i == num_chunks - 1)
        )
        events.append(event)
    
    return events


def create_error_event(
    session_id: str = "test_session",
    component: str = "asr",
    error_type: ErrorType = ErrorType.API_ERROR,
    message: str = "Test error",
    retryable: bool = True
) -> ErrorEvent:
    """Create an ErrorEvent for testing.
    
    Args:
        session_id: Session identifier
        component: Component that generated the error
        error_type: Type of error
        message: Error message
        retryable: Whether the error is retryable
        
    Returns:
        ErrorEvent object
    """
    return ErrorEvent(
        session_id=session_id,
        component=component,
        error_type=error_type,
        message=message,
        timestamp=datetime.now(),
        retryable=retryable
    )


# =============================================================================
# Pytest Fixtures
# =============================================================================

def create_mock_whisper_client(**kwargs) -> MockWhisperClient:
    """Factory function for creating MockWhisperClient instances.
    
    Args:
        **kwargs: Arguments to pass to MockWhisperClient constructor
        
    Returns:
        MockWhisperClient instance
    """
    return MockWhisperClient(**kwargs)


def create_mock_gemini_client(**kwargs) -> MockGeminiClient:
    """Factory function for creating MockGeminiClient instances.
    
    Args:
        **kwargs: Arguments to pass to MockGeminiClient constructor
        
    Returns:
        MockGeminiClient instance
    """
    return MockGeminiClient(**kwargs)


def create_mock_elevenlabs_client(**kwargs) -> MockElevenLabsClient:
    """Factory function for creating MockElevenLabsClient instances.
    
    Args:
        **kwargs: Arguments to pass to MockElevenLabsClient constructor
        
    Returns:
        MockElevenLabsClient instance
    """
    return MockElevenLabsClient(**kwargs)
