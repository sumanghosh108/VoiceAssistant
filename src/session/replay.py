"""Replay system for debugging recorded sessions.

Loads recorded sessions from disk and replays them through the pipeline
for debugging and testing. Compares replayed events with recorded events
to detect discrepancies.
"""

import json
import gzip
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timedelta

from src.core.events import AudioFrame, TranscriptEvent, LLMTokenEvent, TTSAudioEvent, ErrorEvent
from src.session.recorder import RecordedEvent
from src.services.asr import ASRService
from src.services.llm import ReasoningService
from src.services.tts import TTSService
from src.utils.logger import logger


class ReplaySystem:
    """Replays recorded sessions for debugging.
    
    The ReplaySystem loads recorded sessions from disk and replays them
    through the complete pipeline (ASR -> LLM -> TTS). It can compare
    replayed events with recorded events to detect discrepancies.
    
    Features:
    - List available recordings
    - Load recordings from disk
    - Replay audio frames at recorded timestamps
    - Adjust replay speed (real-time, faster, slower)
    - Compare replayed vs recorded events
    - Detect discrepancies in behavior
    
    Requirements: 14.1, 14.2, 14.3, 14.4, 14.5, 14.6
    """
    
    def __init__(
        self,
        asr_service: ASRService,
        llm_service: ReasoningService,
        tts_service: TTSService,
        storage_path: Path = Path("./recordings")
    ):
        """Initialize replay system.
        
        Args:
            asr_service: ASR service instance for transcription
            llm_service: Reasoning service instance for LLM responses
            tts_service: TTS service instance for audio synthesis
            storage_path: Base directory containing recordings
        """
        self.asr_service = asr_service
        self.llm_service = llm_service
        self.tts_service = tts_service
        self.storage_path = storage_path
        
        logger.info(
            "Replay system initialized",
            extra={
                "storage_path": str(storage_path)
            }
        )

    async def list_recordings(self) -> List[Dict[str, Any]]:
        """List all available recordings.
        
        Scans the storage directory for session recordings and returns
        their metadata sorted by start time (most recent first).
        
        Returns:
            List of metadata dictionaries for each recording, sorted by
            start_time in descending order. Each dict contains:
            - session_id: str
            - start_time: str (ISO format)
            - end_time: str (ISO format)
            - duration_seconds: float
            - event_count: int
            - audio_frame_count: int
            - error_count: int
            
        Requirements: 13.5
        """
        recordings = []
        
        # Check if storage path exists
        if not self.storage_path.exists():
            logger.warning(
                "Storage path does not exist",
                extra={"storage_path": str(self.storage_path)}
            )
            return recordings
        
        # Scan for session directories
        for session_dir in self.storage_path.iterdir():
            if session_dir.is_dir():
                metadata_file = session_dir / "metadata.json"
                if metadata_file.exists():
                    try:
                        with open(metadata_file) as f:
                            metadata = json.load(f)
                            recordings.append(metadata)
                    except Exception as e:
                        logger.error(
                            f"Failed to load metadata for {session_dir.name}",
                            extra={
                                "session_dir": str(session_dir),
                                "error": str(e)
                            }
                        )
        
        # Sort by start time (most recent first)
        recordings.sort(key=lambda x: x["start_time"], reverse=True)
        
        logger.info(
            f"Found {len(recordings)} recordings",
            extra={"recording_count": len(recordings)}
        )
        
        return recordings

    async def load_recording(
        self,
        session_id: str
    ) -> Tuple[Dict[str, Any], List[RecordedEvent], List[AudioFrame]]:
        """Load a recording from disk.
        
        Reads the metadata, events, and audio frames for a recorded session
        from compressed storage files.
        
        Args:
            session_id: Session identifier to load
            
        Returns:
            Tuple of (metadata, events, audio_frames):
            - metadata: Dict with session info
            - events: List of RecordedEvent objects
            - audio_frames: List of AudioFrame objects
            
        Raises:
            FileNotFoundError: If recording does not exist
            json.JSONDecodeError: If recording files are corrupted
            
        Requirements: 14.1
        """
        session_path = self.storage_path / session_id
        
        if not session_path.exists():
            raise FileNotFoundError(
                f"Recording not found for session {session_id}"
            )
        
        logger.info(
            f"Loading recording for session {session_id}",
            extra={
                "session_id": session_id,
                "session_path": str(session_path)
            }
        )
        
        # Load metadata
        with open(session_path / "metadata.json") as f:
            metadata = json.load(f)
        
        # Load events
        with gzip.open(session_path / "events.json.gz", "rt") as f:
            events_data = json.load(f)
            events = [
                RecordedEvent(
                    event_type=e["event_type"],
                    timestamp=datetime.fromisoformat(e["timestamp"]),
                    data=e["data"]
                )
                for e in events_data
            ]
        
        # Load audio frames
        with gzip.open(session_path / "audio.json.gz", "rt") as f:
            audio_data = json.load(f)
            frames = [
                AudioFrame(
                    session_id=session_id,
                    data=bytes.fromhex(frame["data"]),
                    timestamp=datetime.fromisoformat(frame["timestamp"]),
                    sequence_number=frame["sequence_number"],
                    sample_rate=frame.get("sample_rate", 16000),
                    channels=frame.get("channels", 1)
                )
                for frame in audio_data["frames"]
            ]
        
        logger.info(
            f"Loaded recording for session {session_id}",
            extra={
                "session_id": session_id,
                "event_count": len(events),
                "audio_frame_count": len(frames),
                "duration_seconds": metadata.get("duration_seconds", 0)
            }
        )
        
        return metadata, events, frames

    async def replay(
        self,
        session_id: str,
        speed: float = 1.0,
        compare: bool = True
    ) -> Dict[str, Any]:
        """Replay a recorded session through the pipeline.
        
        Loads the recorded session and replays it by:
        1. Creating pipeline queues and tasks
        2. Injecting audio frames at recorded timestamps (adjusted by speed)
        3. Collecting events emitted by the pipeline
        4. Comparing replayed events with recorded events (if compare=True)
        5. Returning comparison results
        
        Args:
            session_id: Session identifier to replay
            speed: Replay speed multiplier (1.0 = real-time, 2.0 = 2x faster, 0.5 = half speed)
            compare: Whether to compare replayed events with recorded events
            
        Returns:
            Dictionary with replay results:
            - session_id: str
            - replay_duration_seconds: float
            - recorded_event_count: int
            - replayed_event_count: int
            - discrepancies: List[Dict] (if compare=True)
            
        Requirements: 14.2, 14.3, 14.4, 14.5, 14.6
        """
        # Load recording
        metadata, recorded_events, audio_frames = await self.load_recording(session_id)
        
        logger.info(
            f"Starting replay of session {session_id}",
            extra={
                "session_id": session_id,
                "speed": speed,
                "frame_count": len(audio_frames),
                "event_count": len(recorded_events),
                "compare": compare
            }
        )
        
        # Create replay session ID
        replay_session_id = f"replay_{session_id}"
        
        # Create pipeline queues
        audio_queue = asyncio.Queue()
        transcript_queue = asyncio.Queue()
        token_queue = asyncio.Queue()
        tts_queue = asyncio.Queue()
        
        # Start pipeline tasks
        asr_task = asyncio.create_task(
            self.asr_service.process_audio_stream(audio_queue, transcript_queue)
        )
        llm_task = asyncio.create_task(
            self.llm_service.process_transcript_stream(transcript_queue, token_queue)
        )
        tts_task = asyncio.create_task(
            self.tts_service.process_token_stream(token_queue, tts_queue)
        )
        
        # Collect replayed events
        replayed_events = []
        collection_done = asyncio.Event()
        
        async def collect_transcripts():
            """Collect transcript events from the pipeline."""
            try:
                while True:
                    event = await transcript_queue.get()
                    if not isinstance(event, ErrorEvent):
                        replayed_events.append(("transcript", event))
            except asyncio.CancelledError:
                pass
        
        async def collect_tokens():
            """Collect token events from the pipeline."""
            try:
                while True:
                    event = await token_queue.get()
                    if not isinstance(event, ErrorEvent):
                        replayed_events.append(("token", event))
            except asyncio.CancelledError:
                pass
        
        async def collect_tts():
            """Collect TTS audio events from the pipeline."""
            try:
                while True:
                    event = await tts_queue.get()
                    if not isinstance(event, ErrorEvent):
                        replayed_events.append(("tts", event))
            except asyncio.CancelledError:
                pass
        
        # Start collection tasks
        collect_transcript_task = asyncio.create_task(collect_transcripts())
        collect_token_task = asyncio.create_task(collect_tokens())
        collect_tts_task = asyncio.create_task(collect_tts())
        
        # Inject audio frames at recorded timestamps (adjusted by speed)
        start_time = datetime.now()
        first_frame_time = audio_frames[0].timestamp if audio_frames else datetime.now()
        
        for frame in audio_frames:
            # Calculate delay to maintain timing
            elapsed_since_start = (frame.timestamp - first_frame_time).total_seconds()
            target_time = start_time + timedelta(seconds=elapsed_since_start / speed)
            now = datetime.now()
            
            if target_time > now:
                await asyncio.sleep((target_time - now).total_seconds())
            
            # Inject frame with replay session ID
            replay_frame = AudioFrame(
                session_id=replay_session_id,
                data=frame.data,
                timestamp=datetime.now(),
                sequence_number=frame.sequence_number,
                sample_rate=frame.sample_rate,
                channels=frame.channels
            )
            await audio_queue.put(replay_frame)
            
            logger.debug(
                f"Injected audio frame {frame.sequence_number}",
                extra={
                    "session_id": replay_session_id,
                    "sequence_number": frame.sequence_number
                }
            )
        
        # Wait a short time for processing to complete
        # In a real scenario, we'd wait for specific completion signals
        # For now, just give the pipeline a moment to process
        await asyncio.sleep(0.5)
        
        # Cancel all tasks
        for task in [asr_task, llm_task, tts_task, 
                     collect_transcript_task, collect_token_task, collect_tts_task]:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        # Compare if requested
        discrepancies = []
        if compare:
            discrepancies = self._compare_events(recorded_events, replayed_events)
        
        # Build result
        result = {
            "session_id": session_id,
            "replay_duration_seconds": (datetime.now() - start_time).total_seconds(),
            "recorded_event_count": len(recorded_events),
            "replayed_event_count": len(replayed_events),
            "discrepancies": discrepancies
        }
        
        logger.info(
            f"Replay completed for session {session_id}",
            extra=result
        )
        
        return result

    def _compare_events(
        self,
        recorded: List[RecordedEvent],
        replayed: List[Tuple[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Compare recorded and replayed events to detect discrepancies.
        
        Compares the recorded events with replayed events to identify:
        - Count mismatches (different number of events per type)
        - Transcript text differences
        - Token sequence differences
        - Other behavioral discrepancies
        
        Args:
            recorded: List of RecordedEvent objects from the original session
            replayed: List of (event_type, event) tuples from replay
            
        Returns:
            List of discrepancy dictionaries, each containing:
            - type: str (e.g., "count_mismatch", "transcript_mismatch")
            - event_type: str (optional)
            - Additional fields specific to the discrepancy type
            
        Requirements: 14.4, 14.5
        """
        discrepancies = []
        
        # Group by event type
        recorded_by_type = {}
        for event in recorded:
            if event.event_type not in recorded_by_type:
                recorded_by_type[event.event_type] = []
            recorded_by_type[event.event_type].append(event)
        
        replayed_by_type = {}
        for event_type, event in replayed:
            if event_type not in replayed_by_type:
                replayed_by_type[event_type] = []
            replayed_by_type[event_type].append(event)
        
        # Compare counts
        all_event_types = set(recorded_by_type.keys()) | set(replayed_by_type.keys())
        for event_type in all_event_types:
            recorded_count = len(recorded_by_type.get(event_type, []))
            replayed_count = len(replayed_by_type.get(event_type, []))
            
            if recorded_count != replayed_count:
                discrepancies.append({
                    "type": "count_mismatch",
                    "event_type": event_type,
                    "recorded_count": recorded_count,
                    "replayed_count": replayed_count
                })
                
                logger.warning(
                    f"Event count mismatch for {event_type}",
                    extra={
                        "event_type": event_type,
                        "recorded_count": recorded_count,
                        "replayed_count": replayed_count
                    }
                )
        
        # Compare transcript text
        if "transcript" in recorded_by_type and "transcript" in replayed_by_type:
            # Get final transcripts only (not partial)
            recorded_text = " ".join(
                e.data["text"] for e in recorded_by_type["transcript"] 
                if not e.data.get("partial", False)
            )
            replayed_text = " ".join(
                e.text for e in replayed_by_type["transcript"] 
                if not e.partial
            )
            
            if recorded_text != replayed_text:
                discrepancies.append({
                    "type": "transcript_mismatch",
                    "recorded": recorded_text,
                    "replayed": replayed_text
                })
                
                logger.warning(
                    "Transcript text mismatch",
                    extra={
                        "recorded_length": len(recorded_text),
                        "replayed_length": len(replayed_text),
                        "recorded_preview": recorded_text[:100],
                        "replayed_preview": replayed_text[:100]
                    }
                )
        
        # Compare token sequences
        if "token" in recorded_by_type and "token" in replayed_by_type:
            # Reconstruct token sequences
            recorded_tokens = "".join(
                e.data["token"] for e in recorded_by_type["token"]
            )
            replayed_tokens = "".join(
                e.token for e in replayed_by_type["token"]
            )
            
            if recorded_tokens != replayed_tokens:
                discrepancies.append({
                    "type": "token_sequence_mismatch",
                    "recorded": recorded_tokens,
                    "replayed": replayed_tokens
                })
                
                logger.warning(
                    "Token sequence mismatch",
                    extra={
                        "recorded_length": len(recorded_tokens),
                        "replayed_length": len(replayed_tokens),
                        "recorded_preview": recorded_tokens[:100],
                        "replayed_preview": replayed_tokens[:100]
                    }
                )
        
        # Log summary
        if discrepancies:
            logger.warning(
                f"Found {len(discrepancies)} discrepancies",
                extra={"discrepancy_count": len(discrepancies)}
            )
        else:
            logger.info(
                "No discrepancies found - replay matches recording",
                extra={"discrepancy_count": 0}
            )
        
        return discrepancies
