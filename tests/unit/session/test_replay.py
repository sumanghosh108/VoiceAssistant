"""Unit tests for ReplaySystem.

Tests the replay system's ability to load recordings, replay sessions,
and compare events.
"""

import pytest
import asyncio
import json
import gzip
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

from src.session.replay import ReplaySystem
from src.session.recorder import RecordedEvent
from src.core.events import AudioFrame, TranscriptEvent, LLMTokenEvent, TTSAudioEvent
from src.services.asr import ASRService
from src.services.llm import ReasoningService
from src.services.tts import TTSService


@pytest.fixture
def temp_storage(tmp_path):
    """Create temporary storage directory."""
    storage_path = tmp_path / "recordings"
    storage_path.mkdir()
    return storage_path


@pytest.fixture
def mock_services():
    """Create mock service instances."""
    asr_service = Mock(spec=ASRService)
    asr_service.process_audio_stream = AsyncMock()
    
    llm_service = Mock(spec=ReasoningService)
    llm_service.process_transcript_stream = AsyncMock()
    
    tts_service = Mock(spec=TTSService)
    tts_service.process_token_stream = AsyncMock()
    
    return asr_service, llm_service, tts_service


@pytest.fixture
def replay_system(mock_services, temp_storage):
    """Create ReplaySystem instance with mocked services."""
    asr_service, llm_service, tts_service = mock_services
    return ReplaySystem(
        asr_service=asr_service,
        llm_service=llm_service,
        tts_service=tts_service,
        storage_path=temp_storage
    )


@pytest.fixture
def sample_recording(temp_storage):
    """Create a sample recording in temp storage."""
    session_id = "test-session-123"
    session_path = temp_storage / session_id
    session_path.mkdir()
    
    # Create metadata
    metadata = {
        "session_id": session_id,
        "start_time": "2024-01-01T10:00:00",
        "end_time": "2024-01-01T10:00:10",
        "duration_seconds": 10.0,
        "event_count": 3,
        "audio_frame_count": 2,
        "error_count": 0
    }
    with open(session_path / "metadata.json", "w") as f:
        json.dump(metadata, f)
    
    # Create events
    events_data = [
        {
            "event_type": "audio",
            "timestamp": "2024-01-01T10:00:00",
            "data": {"sequence_number": 0, "data_length": 1000, "sample_rate": 16000, "channels": 1}
        },
        {
            "event_type": "transcript",
            "timestamp": "2024-01-01T10:00:01",
            "data": {"text": "Hello world", "partial": False, "confidence": 0.95, "audio_duration_ms": 1000}
        },
        {
            "event_type": "token",
            "timestamp": "2024-01-01T10:00:02",
            "data": {"token": "Hi", "is_first": True, "is_last": False, "token_index": 0}
        }
    ]
    with gzip.open(session_path / "events.json.gz", "wt") as f:
        json.dump(events_data, f)
    
    # Create audio frames
    audio_data = {
        "frames": [
            {
                "sequence_number": 0,
                "timestamp": "2024-01-01T10:00:00",
                "data": b"test_audio_data_1".hex(),
                "sample_rate": 16000,
                "channels": 1
            },
            {
                "sequence_number": 1,
                "timestamp": "2024-01-01T10:00:01",
                "data": b"test_audio_data_2".hex(),
                "sample_rate": 16000,
                "channels": 1
            }
        ]
    }
    with gzip.open(session_path / "audio.json.gz", "wt") as f:
        json.dump(audio_data, f)
    
    return session_id, metadata


class TestReplaySystemInit:
    """Test ReplaySystem initialization."""
    
    def test_init_with_services(self, mock_services, temp_storage):
        """Test initialization with service dependencies."""
        asr_service, llm_service, tts_service = mock_services
        
        replay_system = ReplaySystem(
            asr_service=asr_service,
            llm_service=llm_service,
            tts_service=tts_service,
            storage_path=temp_storage
        )
        
        assert replay_system.asr_service == asr_service
        assert replay_system.llm_service == llm_service
        assert replay_system.tts_service == tts_service
        assert replay_system.storage_path == temp_storage
    
    def test_init_with_default_storage_path(self, mock_services):
        """Test initialization with default storage path."""
        asr_service, llm_service, tts_service = mock_services
        
        replay_system = ReplaySystem(
            asr_service=asr_service,
            llm_service=llm_service,
            tts_service=tts_service
        )
        
        assert replay_system.storage_path == Path("./recordings")


class TestListRecordings:
    """Test listing available recordings."""
    
    @pytest.mark.asyncio
    async def test_list_recordings_empty(self, replay_system):
        """Test listing recordings when storage is empty."""
        recordings = await replay_system.list_recordings()
        assert recordings == []
    
    @pytest.mark.asyncio
    async def test_list_recordings_with_sample(self, replay_system, sample_recording):
        """Test listing recordings with sample recording."""
        session_id, metadata = sample_recording
        
        recordings = await replay_system.list_recordings()
        
        assert len(recordings) == 1
        assert recordings[0]["session_id"] == session_id
        assert recordings[0]["duration_seconds"] == 10.0
        assert recordings[0]["event_count"] == 3
    
    @pytest.mark.asyncio
    async def test_list_recordings_sorted_by_time(self, replay_system, temp_storage):
        """Test that recordings are sorted by start time (most recent first)."""
        # Create multiple recordings with different timestamps
        for i, timestamp in enumerate(["2024-01-01T10:00:00", "2024-01-01T11:00:00", "2024-01-01T09:00:00"]):
            session_id = f"session-{i}"
            session_path = temp_storage / session_id
            session_path.mkdir()
            
            metadata = {
                "session_id": session_id,
                "start_time": timestamp,
                "end_time": timestamp,
                "duration_seconds": 1.0,
                "event_count": 0,
                "audio_frame_count": 0,
                "error_count": 0
            }
            with open(session_path / "metadata.json", "w") as f:
                json.dump(metadata, f)
        
        recordings = await replay_system.list_recordings()
        
        assert len(recordings) == 3
        # Should be sorted by start_time descending
        assert recordings[0]["start_time"] == "2024-01-01T11:00:00"
        assert recordings[1]["start_time"] == "2024-01-01T10:00:00"
        assert recordings[2]["start_time"] == "2024-01-01T09:00:00"
    
    @pytest.mark.asyncio
    async def test_list_recordings_nonexistent_storage(self, mock_services):
        """Test listing recordings when storage path doesn't exist."""
        replay_system = ReplaySystem(
            asr_service=mock_services[0],
            llm_service=mock_services[1],
            tts_service=mock_services[2],
            storage_path=Path("/nonexistent/path")
        )
        
        recordings = await replay_system.list_recordings()
        assert recordings == []


class TestLoadRecording:
    """Test loading recordings from disk."""
    
    @pytest.mark.asyncio
    async def test_load_recording_success(self, replay_system, sample_recording):
        """Test successfully loading a recording."""
        session_id, expected_metadata = sample_recording
        
        metadata, events, frames = await replay_system.load_recording(session_id)
        
        # Check metadata
        assert metadata["session_id"] == session_id
        assert metadata["duration_seconds"] == 10.0
        
        # Check events
        assert len(events) == 3
        assert events[0].event_type == "audio"
        assert events[1].event_type == "transcript"
        assert events[2].event_type == "token"
        
        # Check audio frames
        assert len(frames) == 2
        assert frames[0].sequence_number == 0
        assert frames[0].data == b"test_audio_data_1"
        assert frames[1].sequence_number == 1
        assert frames[1].data == b"test_audio_data_2"
    
    @pytest.mark.asyncio
    async def test_load_recording_not_found(self, replay_system):
        """Test loading a non-existent recording."""
        with pytest.raises(FileNotFoundError):
            await replay_system.load_recording("nonexistent-session")
    
    @pytest.mark.asyncio
    async def test_load_recording_preserves_timestamps(self, replay_system, sample_recording):
        """Test that timestamps are correctly parsed from ISO format."""
        session_id, _ = sample_recording
        
        metadata, events, frames = await replay_system.load_recording(session_id)
        
        # Check that timestamps are datetime objects
        assert isinstance(events[0].timestamp, datetime)
        assert isinstance(frames[0].timestamp, datetime)
        
        # Check timestamp values
        assert events[0].timestamp.year == 2024
        assert events[0].timestamp.month == 1
        assert events[0].timestamp.day == 1


class TestCompareEvents:
    """Test event comparison logic."""
    
    def test_compare_events_no_discrepancies(self, replay_system):
        """Test comparison when events match perfectly."""
        recorded = [
            RecordedEvent(
                event_type="transcript",
                timestamp=datetime.now(),
                data={"text": "Hello", "partial": False}
            )
        ]
        
        replayed = [
            ("transcript", TranscriptEvent(
                session_id="test",
                text="Hello",
                partial=False,
                confidence=0.9,
                timestamp=datetime.now(),
                audio_duration_ms=1000
            ))
        ]
        
        discrepancies = replay_system._compare_events(recorded, replayed)
        assert len(discrepancies) == 0
    
    def test_compare_events_count_mismatch(self, replay_system):
        """Test detection of event count mismatches."""
        recorded = [
            RecordedEvent(event_type="transcript", timestamp=datetime.now(), data={"text": "A", "partial": False}),
            RecordedEvent(event_type="transcript", timestamp=datetime.now(), data={"text": "B", "partial": False})
        ]
        
        replayed = [
            ("transcript", TranscriptEvent(
                session_id="test", text="A", partial=False,
                confidence=0.9, timestamp=datetime.now(), audio_duration_ms=1000
            ))
        ]
        
        discrepancies = replay_system._compare_events(recorded, replayed)
        
        # Should detect both count mismatch and transcript mismatch
        assert len(discrepancies) == 2
        
        # Check for count mismatch
        count_mismatch = [d for d in discrepancies if d["type"] == "count_mismatch"]
        assert len(count_mismatch) == 1
        assert count_mismatch[0]["event_type"] == "transcript"
        assert count_mismatch[0]["recorded_count"] == 2
        assert count_mismatch[0]["replayed_count"] == 1
        
        # Check for transcript mismatch
        transcript_mismatch = [d for d in discrepancies if d["type"] == "transcript_mismatch"]
        assert len(transcript_mismatch) == 1
    
    def test_compare_events_transcript_mismatch(self, replay_system):
        """Test detection of transcript text differences."""
        recorded = [
            RecordedEvent(
                event_type="transcript",
                timestamp=datetime.now(),
                data={"text": "Hello world", "partial": False}
            )
        ]
        
        replayed = [
            ("transcript", TranscriptEvent(
                session_id="test",
                text="Hello there",
                partial=False,
                confidence=0.9,
                timestamp=datetime.now(),
                audio_duration_ms=1000
            ))
        ]
        
        discrepancies = replay_system._compare_events(recorded, replayed)
        
        assert len(discrepancies) == 1
        assert discrepancies[0]["type"] == "transcript_mismatch"
        assert discrepancies[0]["recorded"] == "Hello world"
        assert discrepancies[0]["replayed"] == "Hello there"
    
    def test_compare_events_token_sequence_mismatch(self, replay_system):
        """Test detection of token sequence differences."""
        recorded = [
            RecordedEvent(event_type="token", timestamp=datetime.now(), data={"token": "Hello"}),
            RecordedEvent(event_type="token", timestamp=datetime.now(), data={"token": " world"})
        ]
        
        replayed = [
            ("token", LLMTokenEvent(
                session_id="test", token="Hello", is_first=True, is_last=False,
                timestamp=datetime.now(), token_index=0
            )),
            ("token", LLMTokenEvent(
                session_id="test", token=" there", is_first=False, is_last=True,
                timestamp=datetime.now(), token_index=1
            ))
        ]
        
        discrepancies = replay_system._compare_events(recorded, replayed)
        
        assert len(discrepancies) == 1
        assert discrepancies[0]["type"] == "token_sequence_mismatch"
        assert discrepancies[0]["recorded"] == "Hello world"
        assert discrepancies[0]["replayed"] == "Hello there"
    
    def test_compare_events_ignores_partial_transcripts(self, replay_system):
        """Test that partial transcripts are ignored in comparison."""
        recorded = [
            RecordedEvent(event_type="transcript", timestamp=datetime.now(), 
                         data={"text": "Hel", "partial": True}),
            RecordedEvent(event_type="transcript", timestamp=datetime.now(), 
                         data={"text": "Hello", "partial": False})
        ]
        
        replayed = [
            ("transcript", TranscriptEvent(
                session_id="test", text="He", partial=True,
                confidence=0.9, timestamp=datetime.now(), audio_duration_ms=500
            )),
            ("transcript", TranscriptEvent(
                session_id="test", text="Hello", partial=False,
                confidence=0.9, timestamp=datetime.now(), audio_duration_ms=1000
            ))
        ]
        
        discrepancies = replay_system._compare_events(recorded, replayed)
        
        # Should have no discrepancies since final transcripts match
        assert len(discrepancies) == 0


class TestReplay:
    """Test replay functionality."""
    
    @pytest.mark.asyncio
    async def test_replay_basic(self, replay_system, sample_recording, mock_services):
        """Test basic replay functionality."""
        session_id, _ = sample_recording
        
        # Mock the service processing to avoid actual API calls
        asr_service, llm_service, tts_service = mock_services
        
        result = await replay_system.replay(session_id, speed=1.0, compare=False)
        
        # Check result structure
        assert result["session_id"] == session_id
        assert "replay_duration_seconds" in result
        assert result["recorded_event_count"] == 3
        assert "replayed_event_count" in result
        
        # Verify services were called
        asr_service.process_audio_stream.assert_called_once()
        llm_service.process_transcript_stream.assert_called_once()
        tts_service.process_token_stream.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_replay_with_speed_adjustment(self, replay_system, sample_recording, mock_services):
        """Test replay with speed adjustment."""
        session_id, _ = sample_recording
        
        # Test with 2x speed
        result = await replay_system.replay(session_id, speed=2.0, compare=False)
        
        assert result["session_id"] == session_id
        # Replay should be faster than real-time
        assert result["replay_duration_seconds"] < 10.0  # Original was 10 seconds
    
    @pytest.mark.asyncio
    async def test_replay_with_comparison(self, replay_system, sample_recording, mock_services):
        """Test replay with event comparison enabled."""
        session_id, _ = sample_recording
        
        result = await replay_system.replay(session_id, speed=1.0, compare=True)
        
        assert "discrepancies" in result
        assert isinstance(result["discrepancies"], list)
