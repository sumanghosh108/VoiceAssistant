"""Unit tests for SessionRecorder class.

Tests event recording, storage, and persistence functionality.
"""

import pytest
import json
import gzip
from pathlib import Path
from datetime import datetime
from tempfile import TemporaryDirectory

from src.session.recorder import SessionRecorder, RecordedEvent
from src.core.events import (
    AudioFrame, TranscriptEvent, LLMTokenEvent, TTSAudioEvent,
    ErrorEvent, ErrorType
)


@pytest.fixture
def temp_storage():
    """Create temporary storage directory for tests."""
    with TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def recorder(temp_storage):
    """Create SessionRecorder instance with temporary storage."""
    return SessionRecorder(
        session_id="test-session-123",
        storage_path=temp_storage
    )


@pytest.fixture
def sample_audio_frame():
    """Create sample AudioFrame for testing."""
    return AudioFrame(
        session_id="test-session-123",
        data=b"\x00\x01" * 1000,  # 2000 bytes of audio data
        timestamp=datetime(2024, 1, 1, 12, 0, 0),
        sequence_number=1,
        sample_rate=16000,
        channels=1
    )


@pytest.fixture
def sample_transcript_event():
    """Create sample TranscriptEvent for testing."""
    return TranscriptEvent(
        session_id="test-session-123",
        text="Hello world",
        partial=False,
        confidence=0.95,
        timestamp=datetime(2024, 1, 1, 12, 0, 1),
        audio_duration_ms=1000
    )


@pytest.fixture
def sample_token_event():
    """Create sample LLMTokenEvent for testing."""
    return LLMTokenEvent(
        session_id="test-session-123",
        token="Hello",
        is_first=True,
        is_last=False,
        timestamp=datetime(2024, 1, 1, 12, 0, 2),
        token_index=0
    )


@pytest.fixture
def sample_tts_event():
    """Create sample TTSAudioEvent for testing."""
    return TTSAudioEvent(
        session_id="test-session-123",
        audio_data=b"\x00\x01" * 500,
        timestamp=datetime(2024, 1, 1, 12, 0, 3),
        sequence_number=1,
        is_final=False
    )


@pytest.fixture
def sample_error_event():
    """Create sample ErrorEvent for testing."""
    return ErrorEvent(
        session_id="test-session-123",
        component="asr",
        error_type=ErrorType.TIMEOUT,
        message="Whisper API timeout",
        timestamp=datetime(2024, 1, 1, 12, 0, 4),
        retryable=True
    )


class TestSessionRecorderInit:
    """Tests for SessionRecorder initialization."""
    
    def test_init_creates_storage_directory(self, temp_storage):
        """Test that initialization creates storage directory."""
        recorder = SessionRecorder(
            session_id="test-session",
            storage_path=temp_storage
        )
        
        expected_path = temp_storage / "test-session"
        assert expected_path.exists()
        assert expected_path.is_dir()
    
    def test_init_sets_session_id(self, recorder):
        """Test that session_id is set correctly."""
        assert recorder.session_id == "test-session-123"
    
    def test_init_initializes_empty_lists(self, recorder):
        """Test that events and audio_frames are initialized empty."""
        assert recorder.events == []
        assert recorder.audio_frames == []
    
    def test_init_sets_start_time(self, recorder):
        """Test that start_time is set to current time."""
        assert isinstance(recorder.start_time, datetime)
        # Should be recent (within last minute)
        time_diff = (datetime.now() - recorder.start_time).total_seconds()
        assert time_diff < 60


class TestRecordAudio:
    """Tests for record_audio method."""
    
    def test_record_audio_stores_frame(self, recorder, sample_audio_frame):
        """Test that audio frame is stored in audio_frames list."""
        recorder.record_audio(sample_audio_frame)
        
        assert len(recorder.audio_frames) == 1
        assert recorder.audio_frames[0] == sample_audio_frame
    
    def test_record_audio_creates_event(self, recorder, sample_audio_frame):
        """Test that audio recording creates a RecordedEvent."""
        recorder.record_audio(sample_audio_frame)
        
        assert len(recorder.events) == 1
        event = recorder.events[0]
        assert event.event_type == "audio"
        assert event.timestamp == sample_audio_frame.timestamp
    
    def test_record_audio_event_data(self, recorder, sample_audio_frame):
        """Test that audio event contains correct metadata."""
        recorder.record_audio(sample_audio_frame)
        
        event = recorder.events[0]
        assert event.data["sequence_number"] == 1
        assert event.data["data_length"] == 2000
        assert event.data["sample_rate"] == 16000
        assert event.data["channels"] == 1
    
    def test_record_multiple_audio_frames(self, recorder):
        """Test recording multiple audio frames."""
        frames = [
            AudioFrame(
                session_id="test-session-123",
                data=b"\x00" * 100,
                timestamp=datetime(2024, 1, 1, 12, 0, i),
                sequence_number=i
            )
            for i in range(5)
        ]
        
        for frame in frames:
            recorder.record_audio(frame)
        
        assert len(recorder.audio_frames) == 5
        assert len(recorder.events) == 5


class TestRecordTranscript:
    """Tests for record_transcript method."""
    
    def test_record_transcript_creates_event(self, recorder, sample_transcript_event):
        """Test that transcript recording creates a RecordedEvent."""
        recorder.record_transcript(sample_transcript_event)
        
        assert len(recorder.events) == 1
        event = recorder.events[0]
        assert event.event_type == "transcript"
        assert event.timestamp == sample_transcript_event.timestamp
    
    def test_record_transcript_event_data(self, recorder, sample_transcript_event):
        """Test that transcript event contains correct data."""
        recorder.record_transcript(sample_transcript_event)
        
        event = recorder.events[0]
        assert event.data["text"] == "Hello world"
        assert event.data["partial"] is False
        assert event.data["confidence"] == 0.95
        assert event.data["audio_duration_ms"] == 1000
    
    def test_record_partial_transcript(self, recorder):
        """Test recording partial transcript."""
        partial_event = TranscriptEvent(
            session_id="test-session-123",
            text="Hel...",
            partial=True,
            confidence=0.7,
            timestamp=datetime.now(),
            audio_duration_ms=500
        )
        
        recorder.record_transcript(partial_event)
        
        event = recorder.events[0]
        assert event.data["partial"] is True
        assert event.data["text"] == "Hel..."


class TestRecordToken:
    """Tests for record_token method."""
    
    def test_record_token_creates_event(self, recorder, sample_token_event):
        """Test that token recording creates a RecordedEvent."""
        recorder.record_token(sample_token_event)
        
        assert len(recorder.events) == 1
        event = recorder.events[0]
        assert event.event_type == "token"
        assert event.timestamp == sample_token_event.timestamp
    
    def test_record_token_event_data(self, recorder, sample_token_event):
        """Test that token event contains correct data."""
        recorder.record_token(sample_token_event)
        
        event = recorder.events[0]
        assert event.data["token"] == "Hello"
        assert event.data["is_first"] is True
        assert event.data["is_last"] is False
        assert event.data["token_index"] == 0
    
    def test_record_token_sequence(self, recorder):
        """Test recording a sequence of tokens."""
        tokens = ["Hello", " ", "world", "!"]
        
        for i, token_text in enumerate(tokens):
            token_event = LLMTokenEvent(
                session_id="test-session-123",
                token=token_text,
                is_first=(i == 0),
                is_last=(i == len(tokens) - 1),
                timestamp=datetime.now(),
                token_index=i
            )
            recorder.record_token(token_event)
        
        assert len(recorder.events) == 4
        assert recorder.events[0].data["is_first"] is True
        assert recorder.events[-1].data["is_last"] is True


class TestRecordTTS:
    """Tests for record_tts method."""
    
    def test_record_tts_creates_event(self, recorder, sample_tts_event):
        """Test that TTS recording creates a RecordedEvent."""
        recorder.record_tts(sample_tts_event)
        
        assert len(recorder.events) == 1
        event = recorder.events[0]
        assert event.event_type == "tts"
        assert event.timestamp == sample_tts_event.timestamp
    
    def test_record_tts_event_data(self, recorder, sample_tts_event):
        """Test that TTS event contains correct metadata."""
        recorder.record_tts(sample_tts_event)
        
        event = recorder.events[0]
        assert event.data["sequence_number"] == 1
        assert event.data["audio_length"] == 1000
        assert event.data["is_final"] is False
    
    def test_record_tts_does_not_store_audio_data(self, recorder, sample_tts_event):
        """Test that TTS audio data is not stored in events (only metadata)."""
        recorder.record_tts(sample_tts_event)
        
        event = recorder.events[0]
        assert "audio_data" not in event.data
        assert "audio_length" in event.data


class TestRecordError:
    """Tests for record_error method."""
    
    def test_record_error_creates_event(self, recorder, sample_error_event):
        """Test that error recording creates a RecordedEvent."""
        recorder.record_error(sample_error_event)
        
        assert len(recorder.events) == 1
        event = recorder.events[0]
        assert event.event_type == "error"
        assert event.timestamp == sample_error_event.timestamp
    
    def test_record_error_event_data(self, recorder, sample_error_event):
        """Test that error event contains correct data."""
        recorder.record_error(sample_error_event)
        
        event = recorder.events[0]
        assert event.data["component"] == "asr"
        assert event.data["error_type"] == "timeout"
        assert event.data["message"] == "Whisper API timeout"
        assert event.data["retryable"] is True
    
    def test_record_multiple_errors(self, recorder):
        """Test recording multiple errors."""
        error_types = [ErrorType.TIMEOUT, ErrorType.API_ERROR, ErrorType.NETWORK_ERROR]
        
        for i, error_type in enumerate(error_types):
            error_event = ErrorEvent(
                session_id="test-session-123",
                component="test",
                error_type=error_type,
                message=f"Error {i}",
                timestamp=datetime.now(),
                retryable=True
            )
            recorder.record_error(error_event)
        
        assert len(recorder.events) == 3
        assert recorder.events[0].data["error_type"] == "timeout"
        assert recorder.events[1].data["error_type"] == "api_error"
        assert recorder.events[2].data["error_type"] == "network_error"


class TestSave:
    """Tests for save method."""
    
    @pytest.mark.asyncio
    async def test_save_creates_metadata_file(self, recorder, temp_storage):
        """Test that save creates metadata.json file."""
        await recorder.save()
        
        metadata_path = temp_storage / "test-session-123" / "metadata.json"
        assert metadata_path.exists()
    
    @pytest.mark.asyncio
    async def test_save_metadata_content(self, recorder, temp_storage):
        """Test that metadata contains correct information."""
        # Record some events
        recorder.record_audio(AudioFrame(
            session_id="test-session-123",
            data=b"\x00" * 100,
            timestamp=datetime.now(),
            sequence_number=1
        ))
        recorder.record_error(ErrorEvent(
            session_id="test-session-123",
            component="test",
            error_type=ErrorType.TIMEOUT,
            message="Test error",
            timestamp=datetime.now(),
            retryable=True
        ))
        
        await recorder.save()
        
        metadata_path = temp_storage / "test-session-123" / "metadata.json"
        with open(metadata_path) as f:
            metadata = json.load(f)
        
        assert metadata["session_id"] == "test-session-123"
        assert "start_time" in metadata
        assert "end_time" in metadata
        assert "duration_seconds" in metadata
        assert metadata["event_count"] == 2
        assert metadata["audio_frame_count"] == 1
        assert metadata["error_count"] == 1
    
    @pytest.mark.asyncio
    async def test_save_creates_events_file(self, recorder, temp_storage):
        """Test that save creates events.json.gz file."""
        await recorder.save()
        
        events_path = temp_storage / "test-session-123" / "events.json.gz"
        assert events_path.exists()
    
    @pytest.mark.asyncio
    async def test_save_events_content(self, recorder, temp_storage, sample_transcript_event):
        """Test that events file contains correct data."""
        recorder.record_transcript(sample_transcript_event)
        
        await recorder.save()
        
        events_path = temp_storage / "test-session-123" / "events.json.gz"
        with gzip.open(events_path, "rt") as f:
            events_data = json.load(f)
        
        assert len(events_data) == 1
        assert events_data[0]["event_type"] == "transcript"
        assert events_data[0]["data"]["text"] == "Hello world"
    
    @pytest.mark.asyncio
    async def test_save_creates_audio_file(self, recorder, temp_storage):
        """Test that save creates audio.json.gz file."""
        await recorder.save()
        
        audio_path = temp_storage / "test-session-123" / "audio.json.gz"
        assert audio_path.exists()
    
    @pytest.mark.asyncio
    async def test_save_audio_content(self, recorder, temp_storage, sample_audio_frame):
        """Test that audio file contains correct data."""
        recorder.record_audio(sample_audio_frame)
        
        await recorder.save()
        
        audio_path = temp_storage / "test-session-123" / "audio.json.gz"
        with gzip.open(audio_path, "rt") as f:
            audio_data = json.load(f)
        
        assert len(audio_data["frames"]) == 1
        frame = audio_data["frames"][0]
        assert frame["sequence_number"] == 1
        assert frame["sample_rate"] == 16000
        assert frame["channels"] == 1
        # Verify audio data is hex-encoded
        assert isinstance(frame["data"], str)
        # Verify we can decode it back
        decoded = bytes.fromhex(frame["data"])
        assert decoded == sample_audio_frame.data
    
    @pytest.mark.asyncio
    async def test_save_with_all_event_types(
        self,
        recorder,
        temp_storage,
        sample_audio_frame,
        sample_transcript_event,
        sample_token_event,
        sample_tts_event,
        sample_error_event
    ):
        """Test saving with all event types."""
        recorder.record_audio(sample_audio_frame)
        recorder.record_transcript(sample_transcript_event)
        recorder.record_token(sample_token_event)
        recorder.record_tts(sample_tts_event)
        recorder.record_error(sample_error_event)
        
        await recorder.save()
        
        # Verify all files exist
        session_path = temp_storage / "test-session-123"
        assert (session_path / "metadata.json").exists()
        assert (session_path / "events.json.gz").exists()
        assert (session_path / "audio.json.gz").exists()
        
        # Verify event count
        with open(session_path / "metadata.json") as f:
            metadata = json.load(f)
        assert metadata["event_count"] == 5
        assert metadata["audio_frame_count"] == 1
        assert metadata["error_count"] == 1
    
    @pytest.mark.asyncio
    async def test_save_empty_session(self, recorder, temp_storage):
        """Test saving a session with no events."""
        await recorder.save()
        
        metadata_path = temp_storage / "test-session-123" / "metadata.json"
        with open(metadata_path) as f:
            metadata = json.load(f)
        
        assert metadata["event_count"] == 0
        assert metadata["audio_frame_count"] == 0
        assert metadata["error_count"] == 0
    
    @pytest.mark.asyncio
    async def test_save_calculates_duration(self, recorder, temp_storage):
        """Test that save calculates session duration correctly."""
        import asyncio
        
        # Wait a bit to ensure measurable duration
        await asyncio.sleep(0.1)
        
        await recorder.save()
        
        metadata_path = temp_storage / "test-session-123" / "metadata.json"
        with open(metadata_path) as f:
            metadata = json.load(f)
        
        assert metadata["duration_seconds"] > 0
        assert metadata["duration_seconds"] < 1  # Should be less than 1 second
