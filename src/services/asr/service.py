"""
ASR Service with Groq Whisper API integration for real-time speech recognition.

This module implements the Automatic Speech Recognition service that:
- Buffers incoming audio frames
- Uses Groq Whisper API for fast, accurate transcription
- Emits TranscriptEvent objects (partial and final)
- Handles timeouts and circuit breaker protection
- Tracks latency metrics
"""

import asyncio
from datetime import datetime
from typing import Optional
import io

from src.core.models import AudioBuffer
from src.core.events import AudioFrame, TranscriptEvent, ErrorEvent, ErrorType
from src.observability.latency import LatencyTracker
from src.utils.logger import logger
from src.infrastructure.resilience import CircuitBreaker, with_timeout


class WhisperClient:
    """Wrapper for Groq Whisper API.
    
    This client handles API communication with Groq's Whisper service
    for high-accuracy, fast speech recognition.
    """
    
    def __init__(self, api_key: str):
        """Initialize Whisper client.
        
        Args:
            api_key: Groq API key
        """
        from groq import AsyncGroq
        
        self.client = AsyncGroq(api_key=api_key)
        
        logger.info("Groq Whisper API client initialized")
        
    async def transcribe(
        self,
        audio_data: bytes,
        sample_rate: int = 16000
    ) -> dict:
        """Transcribe audio using Groq Whisper API.
        
        Args:
            audio_data: Raw PCM audio bytes (16-bit)
            sample_rate: Audio sample rate in Hz
            
        Returns:
            Dictionary with transcription results:
            {
                "text": str,
                "confidence": float,
                "is_partial": bool
            }
            
        Raises:
            Exception: On API errors
        """
        import wave
        
        # Convert raw PCM to WAV format for Whisper API
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_data)
        
        wav_buffer.seek(0)
        wav_buffer.name = "audio.wav"  # Required by API
        
        # Call Groq Whisper API (whisper-large-v3-turbo is fastest and most accurate)
        response = await self.client.audio.transcriptions.create(
            model="whisper-large-v3-turbo",
            file=wav_buffer,
            response_format="json"
        )
        
        # Return result
        return {
            "text": response.text.strip(),
            "confidence": 1.0,  # Whisper doesn't provide confidence scores
            "is_partial": False
        }


class ASRService:
    """Automatic Speech Recognition service using Groq Whisper API.
    
    The ASR service processes streaming audio by:
    1. Buffering audio frames until sufficient duration is available
    2. Transcribing buffered audio via Groq Whisper API (fast & accurate)
    3. Emitting TranscriptEvent objects with partial/final flags
    4. Handling errors with circuit breaker and timeout protection
    5. Tracking latency metrics for observability
    
    Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7
    """
    
    def __init__(
        self,
        api_key: str,
        timeout: float = 3.0,
        buffer_duration_ms: int = 1000,
        circuit_breaker: Optional[CircuitBreaker] = None
    ):
        """Initialize ASR service.
        
        Args:
            api_key: Groq API key
            timeout: Timeout in seconds for API calls (default: 3.0)
            buffer_duration_ms: Audio buffer duration in milliseconds (default: 1000)
            circuit_breaker: Circuit breaker for fault tolerance (optional)
        """
        self.client = WhisperClient(api_key)
        self.timeout = timeout
        self.buffer_duration_ms = buffer_duration_ms
        self.circuit_breaker = circuit_breaker or CircuitBreaker(name="asr")
        
        logger.info(
            "ASR service initialized",
            model="whisper-large-v3-turbo",
            provider="groq",
            timeout=timeout,
            buffer_duration_ms=buffer_duration_ms,
            circuit_breaker=self.circuit_breaker.name
        )
        
    async def process_audio_stream(
        self,
        audio_queue: asyncio.Queue[AudioFrame],
        transcript_queue: asyncio.Queue[TranscriptEvent],
        latency_tracker: Optional[LatencyTracker] = None
    ) -> None:
        """Main processing loop for a session.
        
        Consumes AudioFrame events from audio_queue, buffers them until
        sufficient duration is available, transcribes via Whisper API,
        and emits TranscriptEvent objects to transcript_queue.
        
        Args:
            audio_queue: Input queue for AudioFrame events
            transcript_queue: Output queue for TranscriptEvent objects
            latency_tracker: Optional latency tracker for metrics
            
        Requirements: 2.1, 2.2, 2.3, 2.4
        """
        buffer = AudioBuffer(self.buffer_duration_ms)
        session_id = None
        
        logger.info("ASR processing loop started")
        
        try:
            while True:
                # Get audio frame from queue
                audio_frame = await audio_queue.get()
                
                # Track session ID from first frame
                if session_id is None:
                    session_id = audio_frame.session_id
                    logger.info(
                        "ASR processing session",
                        session_id=session_id
                    )
                
                # Mark audio received for latency tracking
                if latency_tracker:
                    latency_tracker.mark(f"audio_received_{audio_frame.sequence_number}")
                
                # Add frame to buffer
                buffer.append(audio_frame)
                
                # Check if buffer is ready for transcription
                if buffer.is_ready():
                    logger.debug(
                        "Audio buffer ready for transcription",
                        session_id=session_id,
                        total_samples=buffer.total_samples,
                        target_samples=buffer.target_samples
                    )
                    
                    # Transcribe buffered audio
                    await self._transcribe(
                        buffer,
                        transcript_queue,
                        session_id,
                        latency_tracker
                    )
                    
                    # Clear buffer for next batch
                    buffer.clear()
                    
        except asyncio.CancelledError:
            logger.info(
                "ASR processing loop cancelled",
                session_id=session_id
            )
            raise
        except Exception as e:
            logger.error(
                "ASR processing loop error",
                session_id=session_id,
                error=str(e),
                error_type=type(e).__name__
            )
            
            # Emit error event
            if session_id:
                error_event = ErrorEvent(
                    session_id=session_id,
                    component="asr",
                    error_type=ErrorType.API_ERROR,
                    message=str(e),
                    timestamp=datetime.now(),
                    retryable=False
                )
                await transcript_queue.put(error_event)
            raise
            
    async def _transcribe(
        self,
        buffer: AudioBuffer,
        output_queue: asyncio.Queue,
        session_id: str,
        latency_tracker: Optional[LatencyTracker] = None
    ) -> None:
        """Transcribe buffered audio with timeout and circuit breaker.
        
        Args:
            buffer: AudioBuffer containing audio to transcribe
            output_queue: Queue to emit TranscriptEvent objects
            session_id: Session identifier
            latency_tracker: Optional latency tracker for metrics
            
        Requirements: 2.2, 2.3, 2.4, 2.5, 2.6, 2.7
        """
        # Mark transcription start for latency tracking
        if latency_tracker:
            latency_tracker.mark("transcript_start")
        
        try:
            # Get audio bytes from buffer
            audio_data = buffer.get_audio_bytes()
            audio_duration_ms = (len(audio_data) // 2) * 1000 // buffer.sample_rate
            
            logger.debug(
                "Starting transcription",
                session_id=session_id,
                audio_bytes=len(audio_data),
                audio_duration_ms=audio_duration_ms
            )
            
            # Call Whisper API with circuit breaker and timeout protection
            result = await self.circuit_breaker.call(
                self._transcribe_with_timeout,
                audio_data,
                buffer.sample_rate
            )
            
            # Create TranscriptEvent from result
            transcript_event = TranscriptEvent(
                session_id=session_id,
                text=result["text"],
                partial=result.get("is_partial", False),
                confidence=result.get("confidence", 1.0),
                timestamp=datetime.now(),
                audio_duration_ms=audio_duration_ms
            )
            
            # Emit transcript event
            await output_queue.put(transcript_event)
            
            # Track latency
            if latency_tracker:
                latency_tracker.mark("transcript_emitted")
                latency_tracker.measure(
                    "transcript_start",
                    "transcript_emitted",
                    "asr_latency"
                )
            
            logger.info(
                "Transcription completed",
                session_id=session_id,
                text=transcript_event.text[:50],  # Log first 50 chars
                partial=transcript_event.partial,
                confidence=transcript_event.confidence
            )
            
        except asyncio.TimeoutError as e:
            # Handle timeout error
            logger.error(
                "Transcription timeout",
                session_id=session_id,
                timeout=self.timeout,
                error=str(e)
            )
            
            error_event = ErrorEvent(
                session_id=session_id,
                component="asr",
                error_type=ErrorType.TIMEOUT,
                message=f"Groq Whisper API timeout after {self.timeout}s",
                timestamp=datetime.now(),
                retryable=True
            )
            await output_queue.put(error_event)
            
        except Exception as e:
            # Handle other errors
            logger.error(
                "Transcription error",
                session_id=session_id,
                error=str(e),
                error_type=type(e).__name__
            )
            
            # Determine if error is retryable
            retryable = not isinstance(e, (ValueError, TypeError))
            
            error_event = ErrorEvent(
                session_id=session_id,
                component="asr",
                error_type=ErrorType.API_ERROR,
                message=str(e),
                timestamp=datetime.now(),
                retryable=retryable
            )
            await output_queue.put(error_event)
            
    async def _transcribe_with_timeout(
        self,
        audio_data: bytes,
        sample_rate: int
    ) -> dict:
        """Transcribe audio with timeout protection.
        
        Args:
            audio_data: Raw PCM audio bytes
            sample_rate: Audio sample rate in Hz
            
        Returns:
            Transcription result dictionary
            
        Raises:
            TimeoutError: If transcription exceeds timeout
        """
        return await with_timeout(
            self.client.transcribe(audio_data, sample_rate),
            timeout_seconds=self.timeout,
            operation_name="groq_whisper_transcription"
        )
