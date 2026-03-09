"""
Session lifecycle management.

Manages active sessions including creation, pipeline coordination,
and graceful cleanup with timeout enforcement.
"""

import asyncio
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from src.core.models import Session
from src.observability.latency import LatencyTracker
from src.utils.logger import logger


class SessionManager:
    """
    Manages active sessions and their lifecycle.
    
    The SessionManager coordinates multiple concurrent sessions by:
    - Creating new sessions with initialized pipeline tasks
    - Managing session-scoped event queues
    - Starting ASR, LLM, and TTS processing tasks
    - Cleaning up sessions with timeout enforcement
    - Saving recordings when enabled
    
    Requirements: 1.6, 1.7, 6.2, 13.1, 13.2
    """
    
    def __init__(
        self,
        asr_service: Any,
        llm_service: Any,
        tts_service: Any,
        enable_recording: bool = False,
        recording_storage_path: str = "./recordings"
    ):
        """Initialize SessionManager with service dependencies."""
        self.asr_service = asr_service
        self.llm_service = llm_service
        self.tts_service = tts_service
        self.enable_recording = enable_recording
        self.recording_storage_path = recording_storage_path
        
        # Active sessions dictionary
        self.sessions: Dict[str, Session] = {}
        
        logger.info(
            "SessionManager initialized",
            enable_recording=enable_recording,
            recording_storage_path=recording_storage_path
        )
        
    async def create_session(self, websocket: Any) -> Session:
        """Create a new session and start pipeline tasks."""
        # Generate unique session ID
        session_id = str(uuid.uuid4())
        
        logger.info("Creating new session", session_id=session_id)
        
        # Create event queues with appropriate maxsize for backpressure
        audio_queue = asyncio.Queue(maxsize=100)
        transcript_queue = asyncio.Queue(maxsize=50)
        token_queue = asyncio.Queue(maxsize=200)
        tts_queue = asyncio.Queue(maxsize=100)
        
        # Create latency tracker
        latency_tracker = LatencyTracker(session_id)
        
        # Create session recorder if enabled
        recorder = None
        if self.enable_recording:
            from src.session.recorder import SessionRecorder
            recorder = SessionRecorder(session_id, self.recording_storage_path)
            logger.info("Session recording enabled", session_id=session_id)
        
        # Create session object
        session = Session(
            session_id=session_id,
            created_at=datetime.now(),
            websocket=websocket,
            audio_queue=audio_queue,
            transcript_queue=transcript_queue,
            token_queue=token_queue,
            tts_queue=tts_queue,
            latency_tracker=latency_tracker,
            recorder=recorder
        )
        
        # Start pipeline tasks
        logger.debug("Starting pipeline tasks", session_id=session_id)
        
        # ASR task: audio_queue -> transcript_queue
        session.asr_task = asyncio.create_task(
            self.asr_service.process_audio_stream(
                session.audio_queue,
                session.transcript_queue,
                session.latency_tracker
            ),
            name=f"asr_{session_id}"
        )
        
        # LLM task: transcript_queue -> token_queue
        session.llm_task = asyncio.create_task(
            self.llm_service.process_transcript_stream(
                session.transcript_queue,
                session.token_queue,
                session.latency_tracker
            ),
            name=f"llm_{session_id}"
        )
        
        # TTS task: token_queue -> tts_queue
        session.tts_task = asyncio.create_task(
            self.tts_service.process_token_stream(
                session.token_queue,
                session.tts_queue,
                session.latency_tracker
            ),
            name=f"tts_{session_id}"
        )
        
        # Store session
        self.sessions[session_id] = session
        
        logger.info(
            "Session created and pipeline started",
            session_id=session_id,
            active_sessions=len(self.sessions)
        )
        
        return session
        
    async def cleanup_session(
        self,
        session_id: str,
        timeout: float = 5.0
    ) -> None:
        """Clean up session resources with timeout enforcement."""
        session = self.sessions.get(session_id)
        if not session:
            logger.warning(
                "Attempted to cleanup non-existent session",
                session_id=session_id
            )
            return
        
        logger.info(
            "Starting session cleanup",
            session_id=session_id,
            timeout=timeout
        )
        
        # Cancel all pipeline tasks
        tasks = []
        if session.asr_task and not session.asr_task.done():
            session.asr_task.cancel()
            tasks.append(session.asr_task)
            
        if session.llm_task and not session.llm_task.done():
            session.llm_task.cancel()
            tasks.append(session.llm_task)
            
        if session.tts_task and not session.tts_task.done():
            session.tts_task.cancel()
            tasks.append(session.tts_task)
        
        # Wait for tasks to complete with timeout
        if tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                logger.warning(
                    "Session cleanup timed out, forcing termination",
                    session_id=session_id,
                    timeout=timeout
                )
        
        # Save recording if enabled
        if session.recorder:
            try:
                await session.recorder.save()
                logger.info("Session recording saved", session_id=session_id)
            except Exception as e:
                logger.error(
                    "Failed to save session recording",
                    session_id=session_id,
                    error=str(e)
                )
        
        # Calculate session duration
        duration = (datetime.now() - session.created_at).total_seconds()
        
        # Remove from active sessions
        del self.sessions[session_id]
        
        logger.info(
            "Session cleanup completed",
            session_id=session_id,
            duration_seconds=duration,
            active_sessions=len(self.sessions)
        )
        
    def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID."""
        return self.sessions.get(session_id)
        
    def get_active_session_count(self) -> int:
        """Get count of active sessions."""
        return len(self.sessions)
        
    def get_session_ids(self) -> list[str]:
        """Get list of active session IDs."""
        return list(self.sessions.keys())
