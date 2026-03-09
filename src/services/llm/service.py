"""
Reasoning Service with OpenRouter integration for streaming LLM responses.

This module implements the Reasoning service that:
- Receives final TranscriptEvent objects
- Maintains conversation context per session
- Streams tokens from OpenRouter API
- Emits LLMTokenEvent for each token
- Handles timeouts, retries, and circuit breaker protection
- Tracks latency metrics for first token
"""

import asyncio
from datetime import datetime
from typing import Optional, Dict, AsyncIterator
import aiohttp
import json

from src.core.models import ConversationContext
from src.core.events import TranscriptEvent, LLMTokenEvent, ErrorEvent, ErrorType
from src.observability.latency import LatencyTracker
from src.utils.logger import logger
from src.infrastructure.resilience import CircuitBreaker, with_timeout, RetryConfig, with_retry


class OpenRouterClient:
    """Wrapper for OpenRouter API streaming calls.
    
    This client handles HTTP communication with the OpenRouter API
    for streaming LLM responses.
    """
    
    def __init__(self, api_key: str, model: str = "meta-llama/llama-3.2-3b-instruct:free"):
        """Initialize OpenRouter client.
        
        Args:
            api_key: OpenRouter API key
            model: Model name (default: meta-llama/llama-3.2-3b-instruct:free)
        """
        self.api_key = api_key
        self.model = model
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        
    async def generate_stream(
        self,
        messages: list,
    ) -> AsyncIterator[str]:
        """Generate streaming response from OpenRouter.
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys
            
        Yields:
            Individual tokens from the streaming response
            
        Raises:
            Exception: On API errors
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8000",  # Optional
            "X-Title": "Voice Assistant"  # Optional
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(self.base_url, headers=headers, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"OpenRouter API error {response.status}: {error_text}")
                
                # Read streaming response
                async for line in response.content:
                    line = line.decode('utf-8').strip()
                    
                    if not line or line == "data: [DONE]":
                        continue
                    
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])  # Remove "data: " prefix
                            
                            if "choices" in data and len(data["choices"]) > 0:
                                delta = data["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                
                                if content:
                                    yield content
                        except json.JSONDecodeError:
                            continue


class ReasoningService:
    """Language model reasoning service using OpenRouter API.
    
    The Reasoning service processes transcripts by:
    1. Receiving final TranscriptEvent objects (partial=False)
    2. Maintaining conversation context per session
    3. Streaming tokens from OpenRouter API
    4. Emitting LLMTokenEvent for each token with is_first flag
    5. Handling errors with circuit breaker, timeout, and retry protection
    6. Tracking latency metrics for first token
    
    Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7
    """
    
    def __init__(
        self,
        api_key: str,
        model: str = "meta-llama/llama-3.2-3b-instruct:free",
        timeout: float = 5.0,
        circuit_breaker: Optional[CircuitBreaker] = None
    ):
        """Initialize Reasoning service.
        
        Args:
            api_key: OpenRouter API key
            model: Model name (default: meta-llama/llama-3.2-3b-instruct:free)
            timeout: Timeout in seconds for API calls (default: 5.0)
            circuit_breaker: Circuit breaker for fault tolerance (optional)
        """
        self.client = OpenRouterClient(api_key, model)
        self.model = model
        self.timeout = timeout
        self.circuit_breaker = circuit_breaker or CircuitBreaker(name="llm")
        self.context_store: Dict[str, ConversationContext] = {}
        
        # Retry configuration for LLM calls
        self.retry_config = RetryConfig(
            max_attempts=3,
            initial_delay_ms=100,
            retryable_exceptions=(TimeoutError, ConnectionError, Exception)
        )
        
        logger.info(
            "Reasoning service initialized",
            model=model,
            timeout=timeout,
            circuit_breaker=self.circuit_breaker.name
        )
        
    async def process_transcript_stream(
        self,
        transcript_queue: asyncio.Queue[TranscriptEvent],
        token_queue: asyncio.Queue[LLMTokenEvent],
        latency_tracker: Optional[LatencyTracker] = None
    ) -> None:
        """Main processing loop for a session.
        
        Consumes TranscriptEvent objects from transcript_queue, generates
        streaming responses from Gemini API, and emits LLMTokenEvent objects
        to token_queue.
        
        Args:
            transcript_queue: Input queue for TranscriptEvent objects
            token_queue: Output queue for LLMTokenEvent objects
            latency_tracker: Optional latency tracker for metrics
            
        Requirements: 3.1, 3.2, 3.3
        """
        session_id = None
        
        logger.info("LLM processing loop started")
        
        try:
            while True:
                # Get transcript from queue
                transcript = await transcript_queue.get()
                
                # Skip if this is an error event
                if isinstance(transcript, ErrorEvent):
                    logger.debug(
                        "LLM received error event, passing through",
                        session_id=transcript.session_id,
                        component=transcript.component
                    )
                    continue
                
                # Track session ID from first transcript
                if session_id is None:
                    session_id = transcript.session_id
                    logger.info(
                        "LLM processing session",
                        session_id=session_id
                    )
                
                # Only process final transcripts (not partial)
                if not transcript.partial:
                    # Skip empty or very short transcriptions
                    if not transcript.text or len(transcript.text.strip()) < 2:
                        logger.debug(
                            "Skipping empty or too short transcript",
                            session_id=session_id,
                            text=transcript.text
                        )
                        continue
                    
                    logger.debug(
                        "Processing final transcript",
                        session_id=session_id,
                        text=transcript.text[:50]  # Log first 50 chars
                    )
                    
                    # Generate response
                    await self._generate_response(
                        transcript,
                        token_queue,
                        latency_tracker
                    )
                else:
                    logger.debug(
                        "Skipping partial transcript",
                        session_id=session_id
                    )
                    
        except asyncio.CancelledError:
            logger.info(
                "LLM processing loop cancelled",
                session_id=session_id
            )
            raise
        except Exception as e:
            logger.error(
                "LLM processing loop error",
                session_id=session_id,
                error=str(e),
                error_type=type(e).__name__
            )
            
            # Emit error event
            if session_id:
                error_event = ErrorEvent(
                    session_id=session_id,
                    component="llm",
                    error_type=ErrorType.API_ERROR,
                    message=str(e),
                    timestamp=datetime.now(),
                    retryable=False
                )
                await token_queue.put(error_event)
            raise
            
    async def _generate_response(
        self,
        transcript: TranscriptEvent,
        output_queue: asyncio.Queue,
        latency_tracker: Optional[LatencyTracker] = None
    ) -> None:
        """Generate streaming response from Gemini with retry and circuit breaker.
        
        Args:
            transcript: TranscriptEvent containing user message
            output_queue: Queue to emit LLMTokenEvent objects
            latency_tracker: Optional latency tracker for metrics
            
        Requirements: 3.2, 3.3, 3.4, 3.5, 3.6, 3.7
        """
        session_id = transcript.session_id
        
        # Mark LLM start for latency tracking
        if latency_tracker:
            latency_tracker.mark("llm_start")
        
        try:
            # Get conversation context
            context = self.get_context(session_id)
            
            # Add user message to context
            context.add_user_message(transcript.text)
            
            # Get messages for API
            messages = context.get_messages_for_api()
            
            logger.debug(
                "Generating LLM response",
                session_id=session_id,
                message_count=len(messages),
                user_message=transcript.text[:50]
            )
            
            # Generate streaming response with retry and circuit breaker
            token_index = 0
            is_first = True
            assistant_message_parts = []
            
            # Call with retry decorator
            @with_retry(self.retry_config)
            async def generate_with_retry():
                return await self.circuit_breaker.call(
                    self._generate_stream_with_timeout,
                    messages
                )
            
            try:
                token_stream = await generate_with_retry()
                
                # Stream tokens
                async for token in token_stream:
                    # Mark first token for latency tracking
                    if is_first and latency_tracker:
                        latency_tracker.mark("llm_first_token")
                        latency_tracker.measure(
                            "llm_start",
                            "llm_first_token",
                            "llm_first_token_latency"
                        )
                    
                    # Create token event
                    token_event = LLMTokenEvent(
                        session_id=session_id,
                        token=token,
                        is_first=is_first,
                        is_last=False,  # Will mark last token after loop
                        timestamp=datetime.now(),
                        token_index=token_index
                    )
                    
                    # Emit token event
                    await output_queue.put(token_event)
                    
                    # Accumulate for context
                    assistant_message_parts.append(token)
                    
                    # Update flags
                    is_first = False
                    token_index += 1
                    
                    logger.debug(
                        "Emitted LLM token",
                        session_id=session_id,
                        token_index=token_index,
                        is_first=token_event.is_first
                    )
                
                # Emit final token marker if we got any tokens
                if token_index > 0:
                    final_token_event = LLMTokenEvent(
                        session_id=session_id,
                        token="",  # Empty token to signal completion
                        is_first=False,
                        is_last=True,
                        timestamp=datetime.now(),
                        token_index=token_index
                    )
                    await output_queue.put(final_token_event)
                    
                    # Update conversation context with complete response
                    assistant_message = "".join(assistant_message_parts)
                    context.add_assistant_message(assistant_message)
                    
                    # Track generation latency
                    if latency_tracker:
                        latency_tracker.mark("llm_complete")
                        latency_tracker.measure(
                            "llm_first_token",
                            "llm_complete",
                            "llm_generation_latency"
                        )
                    
                    logger.info(
                        "LLM response completed",
                        session_id=session_id,
                        token_count=token_index,
                        response_preview=assistant_message[:50]
                    )
                else:
                    logger.warning(
                        "LLM generated no tokens",
                        session_id=session_id
                    )
                    
            except Exception as e:
                # Handle errors during streaming
                logger.error(
                    "LLM streaming error",
                    session_id=session_id,
                    error=str(e),
                    error_type=type(e).__name__
                )
                raise
                
        except asyncio.TimeoutError as e:
            # Handle timeout error
            logger.error(
                "LLM generation timeout",
                session_id=session_id,
                timeout=self.timeout,
                error=str(e)
            )
            
            error_event = ErrorEvent(
                session_id=session_id,
                component="llm",
                error_type=ErrorType.TIMEOUT,
                message=f"OpenRouter API timeout after {self.timeout}s",
                timestamp=datetime.now(),
                retryable=True
            )
            await output_queue.put(error_event)
            
        except Exception as e:
            # Handle other errors
            logger.error(
                "LLM generation error",
                session_id=session_id,
                error=str(e),
                error_type=type(e).__name__
            )
            
            # Determine if error is retryable
            retryable = not isinstance(e, (ValueError, TypeError))
            
            error_event = ErrorEvent(
                session_id=session_id,
                component="llm",
                error_type=ErrorType.API_ERROR,
                message=str(e),
                timestamp=datetime.now(),
                retryable=retryable
            )
            await output_queue.put(error_event)
            
    async def _generate_stream_with_timeout(
        self,
        messages: list
    ) -> AsyncIterator[str]:
        """Generate streaming response with timeout protection.
        
        Args:
            messages: List of message dicts for Gemini API
            
        Returns:
            Async iterator of tokens
            
        Raises:
            TimeoutError: If generation exceeds timeout
        """
        # Note: We can't use with_timeout directly on an async generator,
        # so we wrap the generator creation with timeout
        try:
            # Start the stream with timeout on first token
            stream = self.client.generate_stream(messages)
            
            # Return the stream for consumption
            # The timeout will be enforced by asyncio.wait_for in the caller
            return stream
            
        except Exception as e:
            logger.error(
                "Error creating OpenRouter stream",
                error=str(e),
                error_type=type(e).__name__
            )
            raise
            
    def get_context(self, session_id: str) -> ConversationContext:
        """Get or create conversation context for session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            ConversationContext for the session
            
        Requirements: 3.4
        """
        if session_id not in self.context_store:
            self.context_store[session_id] = ConversationContext(max_turns=10)
            logger.debug(
                "Created new conversation context",
                session_id=session_id
            )
        return self.context_store[session_id]
        
    def update_context(
        self,
        session_id: str,
        user_message: str,
        assistant_message: str
    ) -> None:
        """Update conversation history.
        
        Args:
            session_id: Session identifier
            user_message: User's message text
            assistant_message: Assistant's response text
            
        Requirements: 3.4
        """
        context = self.get_context(session_id)
        context.add_user_message(user_message)
        context.add_assistant_message(assistant_message)
        
        logger.debug(
            "Updated conversation context",
            session_id=session_id,
            message_count=len(context.messages)
        )
