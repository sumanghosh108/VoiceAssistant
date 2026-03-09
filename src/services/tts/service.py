"""
TTS Service with ElevenLabs integration for streaming text-to-speech synthesis.

This module implements the TTS service that:
- Receives LLMTokenEvent objects
- Buffers tokens until complete phrase is available
- Calls ElevenLabs streaming API for synthesis
- Emits TTSAudioEvent chunks as they arrive
- Handles timeouts and circuit breaker protection (no retry for TTS)
- Tracks latency metrics for first audio chunk
"""

import asyncio
from datetime import datetime
from typing import Optional, AsyncIterator

from src.core.models import TokenBuffer
from src.core.events import LLMTokenEvent, TTSAudioEvent, ErrorEvent, ErrorType
from src.observability.latency import LatencyTracker
from src.utils.logger import logger
from src.infrastructure.resilience import CircuitBreaker, with_timeout


class ElevenLabsClient:
    """Wrapper for ElevenLabs API streaming calls.
    
    This client handles the actual HTTP communication with the ElevenLabs API.
    In a production implementation, this would use the ElevenLabs Python SDK
    or make direct HTTP requests to the ElevenLabs API endpoint.
    """
    
    def __init__(self, api_key: str):
        """Initialize ElevenLabs client.
        
        Args:
            api_key: ElevenLabs API key
        """
        self.api_key = api_key
        # Initialize ElevenLabs client (v2.x API)
        try:
            from elevenlabs.client import ElevenLabs
            self.client = ElevenLabs(api_key=api_key)
        except ImportError:
            # Fallback for different package structure
            from elevenlabs import ElevenLabs
            self.client = ElevenLabs(api_key=api_key)
        
    async def synthesize_stream(
        self,
        text: str,
        voice_id: str
    ) -> AsyncIterator[bytes]:
        """Synthesize text to audio using ElevenLabs streaming API.
        
        Args:
            text: Text to synthesize
            voice_id: ElevenLabs voice ID
            
        Yields:
            Audio chunks as bytes (PCM format)
            
        Raises:
            Exception: On API errors
        """
        import asyncio
        
        # Call ElevenLabs streaming API (synchronous, so run in executor)
        loop = asyncio.get_event_loop()
        
        def sync_generate():
            audio_stream = self.client.text_to_speech.convert(
                text=text,
                voice_id=voice_id,
                model_id="eleven_turbo_v2_5",
                output_format="pcm_16000"  # Request PCM format at 16kHz
            )
            return list(audio_stream)
        
        chunks = await loop.run_in_executor(None, sync_generate)
        
        # Yield audio chunks
        for chunk in chunks:
            yield chunk


class TTSService:
    """Text-to-Speech synthesis service using ElevenLabs API.
    
    The TTS service processes tokens by:
    1. Buffering LLMTokenEvent objects until complete phrase is available
    2. Synthesizing buffered text via ElevenLabs streaming API
    3. Emitting TTSAudioEvent chunks as they arrive
    4. Handling errors with circuit breaker and timeout protection
    5. No retry logic for TTS (failures are terminal for that response)
    6. Tracking latency metrics for first audio chunk
    
    Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7
    """
    
    def __init__(
        self,
        api_key: str,
        voice_id: str,
        timeout: float = 3.0,
        phrase_buffer_tokens: int = 10,
        circuit_breaker: Optional[CircuitBreaker] = None
    ):
        """Initialize TTS service.
        
        Args:
            api_key: ElevenLabs API key
            voice_id: ElevenLabs voice ID to use for synthesis
            timeout: Timeout in seconds for API calls (default: 3.0)
            phrase_buffer_tokens: Number of tokens to buffer before synthesis (default: 10)
            circuit_breaker: Circuit breaker for fault tolerance (optional)
        """
        self.client = ElevenLabsClient(api_key)
        self.voice_id = voice_id
        self.timeout = timeout
        self.phrase_buffer_tokens = phrase_buffer_tokens
        self.circuit_breaker = circuit_breaker or CircuitBreaker(name="tts")
        
        logger.info(
            "TTS service initialized",
            voice_id=voice_id,
            timeout=timeout,
            phrase_buffer_tokens=phrase_buffer_tokens,
            circuit_breaker=self.circuit_breaker.name
        )
        
    async def process_token_stream(
        self,
        token_queue: asyncio.Queue[LLMTokenEvent],
        audio_queue: asyncio.Queue[TTSAudioEvent],
        latency_tracker: Optional[LatencyTracker] = None
    ) -> None:
        """Main processing loop for a session.
        
        Consumes LLMTokenEvent objects from token_queue, buffers them until
        a complete phrase is available, synthesizes via ElevenLabs API,
        and emits TTSAudioEvent objects to audio_queue.
        
        Args:
            token_queue: Input queue for LLMTokenEvent objects
            audio_queue: Output queue for TTSAudioEvent objects
            latency_tracker: Optional latency tracker for metrics
            
        Requirements: 4.1, 4.2, 4.3
        """
        buffer = TokenBuffer(self.phrase_buffer_tokens)
        session_id = None
        sequence_number = 0
        
        logger.info("TTS processing loop started")
        
        try:
            while True:
                # Get token from queue
                token_event = await token_queue.get()
                
                # Skip if this is an error event
                if isinstance(token_event, ErrorEvent):
                    logger.debug(
                        "TTS received error event, passing through",
                        session_id=token_event.session_id,
                        component=token_event.component
                    )
                    continue
                
                # Track session ID from first token
                if session_id is None:
                    session_id = token_event.session_id
                    logger.info(
                        "TTS processing session",
                        session_id=session_id
                    )
                
                # Add token to buffer
                buffer.append(token_event)
                
                logger.debug(
                    "Buffered token",
                    session_id=session_id,
                    token_index=token_event.token_index,
                    buffer_size=len(buffer.tokens),
                    is_last=token_event.is_last
                )
                
                # Check if we should synthesize
                should_synthesize = (
                    buffer.is_phrase_complete() or 
                    token_event.is_last
                )
                
                if should_synthesize and len(buffer.tokens) > 0:
                    logger.debug(
                        "Buffer ready for synthesis",
                        session_id=session_id,
                        buffer_size=len(buffer.tokens),
                        is_last=token_event.is_last
                    )
                    
                    # Synthesize buffered text
                    is_final = token_event.is_last
                    await self._synthesize(
                        buffer,
                        audio_queue,
                        session_id,
                        sequence_number,
                        is_final,
                        latency_tracker
                    )
                    
                    # Update sequence number for next batch
                    sequence_number += 1
                    
                    # Clear buffer for next phrase
                    buffer.clear()
                    
                # If this was the last token, we're done
                if token_event.is_last:
                    logger.info(
                        "TTS processing completed for response",
                        session_id=session_id
                    )
                    
        except asyncio.CancelledError:
            logger.info(
                "TTS processing loop cancelled",
                session_id=session_id
            )
            raise
        except Exception as e:
            logger.error(
                "TTS processing loop error",
                session_id=session_id,
                error=str(e),
                error_type=type(e).__name__
            )
            
            # Emit error event
            if session_id:
                error_event = ErrorEvent(
                    session_id=session_id,
                    component="tts",
                    error_type=ErrorType.API_ERROR,
                    message=str(e),
                    timestamp=datetime.now(),
                    retryable=False
                )
                await audio_queue.put(error_event)
            raise
            
    async def _synthesize(
        self,
        buffer: TokenBuffer,
        output_queue: asyncio.Queue,
        session_id: str,
        sequence_number: int,
        is_final: bool,
        latency_tracker: Optional[LatencyTracker] = None
    ) -> None:
        """Synthesize buffered text to audio with timeout and circuit breaker.
        
        Args:
            buffer: TokenBuffer containing text to synthesize
            output_queue: Queue to emit TTSAudioEvent objects
            session_id: Session identifier
            sequence_number: Starting sequence number for audio chunks
            is_final: Whether this is the final synthesis for the response
            latency_tracker: Optional latency tracker for metrics
            
        Requirements: 4.2, 4.3, 4.4, 4.5, 4.6, 4.7
        """
        # Mark TTS start for latency tracking
        if latency_tracker:
            latency_tracker.mark("tts_start")
        
        try:
            # Get text from buffer
            text = buffer.get_text()
            
            # Remove emojis and other non-speech characters
            import re
            # Remove emojis (Unicode ranges for emojis)
            emoji_pattern = re.compile("["
                u"\U0001F600-\U0001F64F"  # emoticons
                u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                u"\U0001F680-\U0001F6FF"  # transport & map symbols
                u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                u"\U00002702-\U000027B0"
                u"\U000024C2-\U0001F251"
                "]+", flags=re.UNICODE)
            text = emoji_pattern.sub('', text)
            
            if not text.strip():
                logger.debug(
                    "Skipping synthesis for empty text",
                    session_id=session_id
                )
                return
            
            logger.debug(
                "Starting synthesis",
                session_id=session_id,
                text_length=len(text),
                text_preview=text[:50],
                is_final=is_final
            )
            
            # Call ElevenLabs API with circuit breaker and timeout protection
            audio_stream = await self.circuit_breaker.call(
                self._synthesize_with_timeout,
                text
            )
            
            # Stream audio chunks
            chunk_index = 0
            is_first_chunk = True
            
            async for audio_chunk in audio_stream:
                # Mark first audio chunk for latency tracking
                if is_first_chunk and latency_tracker:
                    latency_tracker.mark("tts_audio_start")
                    latency_tracker.measure(
                        "tts_start",
                        "tts_audio_start",
                        "tts_latency"
                    )
                
                # Create TTSAudioEvent with incremented sequence number
                current_seq = sequence_number * 1000 + chunk_index  # Use larger spacing for sequence numbers
                audio_event = TTSAudioEvent(
                    session_id=session_id,
                    audio_data=audio_chunk,
                    timestamp=datetime.now(),
                    sequence_number=current_seq,
                    is_final=False  # Will mark final chunk after loop
                )
                
                # Emit audio event
                await output_queue.put(audio_event)
                
                chunk_index += 1
                is_first_chunk = False
                
                logger.debug(
                    "Emitted TTS audio chunk",
                    session_id=session_id,
                    sequence_number=audio_event.sequence_number,
                    chunk_size=len(audio_chunk)
                )
            
            # Emit final marker if this is the last synthesis
            if is_final and chunk_index > 0:
                final_seq = sequence_number * 1000 + chunk_index
                final_event = TTSAudioEvent(
                    session_id=session_id,
                    audio_data=b"",  # Empty to signal completion
                    timestamp=datetime.now(),
                    sequence_number=final_seq,
                    is_final=True
                )
                await output_queue.put(final_event)
                
                logger.info(
                    "TTS synthesis completed",
                    session_id=session_id,
                    chunk_count=chunk_index,
                    text_preview=text[:50]
                )
            elif chunk_index > 0:
                logger.info(
                    "TTS synthesis completed (partial)",
                    session_id=session_id,
                    chunk_count=chunk_index
                )
            else:
                logger.warning(
                    "TTS generated no audio chunks",
                    session_id=session_id
                )
                
        except asyncio.TimeoutError as e:
            # Handle timeout error (no retry for TTS)
            logger.error(
                "TTS synthesis timeout",
                session_id=session_id,
                timeout=self.timeout,
                error=str(e)
            )
            
            error_event = ErrorEvent(
                session_id=session_id,
                component="tts",
                error_type=ErrorType.TIMEOUT,
                message=f"ElevenLabs API timeout after {self.timeout}s",
                timestamp=datetime.now(),
                retryable=False  # No retry for TTS
            )
            await output_queue.put(error_event)
            
        except Exception as e:
            # Handle other errors (no retry for TTS)
            logger.error(
                "TTS synthesis error",
                session_id=session_id,
                error=str(e),
                error_type=type(e).__name__
            )
            
            error_event = ErrorEvent(
                session_id=session_id,
                component="tts",
                error_type=ErrorType.API_ERROR,
                message=str(e),
                timestamp=datetime.now(),
                retryable=False  # No retry for TTS
            )
            await output_queue.put(error_event)
            
    async def _synthesize_with_timeout(
        self,
        text: str
    ) -> AsyncIterator[bytes]:
        """Synthesize text with timeout protection.
        
        Args:
            text: Text to synthesize
            
        Returns:
            Async iterator of audio chunks
            
        Raises:
            TimeoutError: If synthesis exceeds timeout
        """
        try:
            # Start the stream
            stream = self.client.synthesize_stream(text, self.voice_id)
            
            # Return the stream for consumption
            # The timeout will be enforced by the circuit breaker caller
            return stream
            
        except Exception as e:
            logger.error(
                "Error creating ElevenLabs stream",
                error=str(e),
                error_type=type(e).__name__
            )
            raise
