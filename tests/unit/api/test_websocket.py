"""
Unit tests for WebSocket server.

Tests cover:
- Connection handling and session creation
- Audio frame parsing and emission
- Audio packet sending with sequence numbers
- Error handling and connection closure
- Backpressure handling

Requirements: 1.2, 1.3, 5.3, 5.5
"""

import asyncio
import struct
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.core.events import AudioFrame, TTSAudioEvent
from src.core.models import Session, SessionManager
from src.api.websocket import WebSocketServer


@pytest.fixture
def mock_session_manager():
    """Create a mock SessionManager."""
    manager = Mock(spec=SessionManager)
    return manager


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket connection."""
    ws = AsyncMock()
    ws.remote_address = ("127.0.0.1", 12345)
    return ws


@pytest.fixture
def mock_session():
    """Create a mock Session."""
    session = Mock(spec=Session)
    session.session_id = "test-session-123"
    session.audio_queue = asyncio.Queue(maxsize=100)
    session.tts_queue = asyncio.Queue(maxsize=100)
    return session


class TestWebSocketServer:
    """Test suite for WebSocketServer class."""
    
    def test_init(self, mock_session_manager):
        """Test WebSocketServer initialization."""
        server = WebSocketServer(mock_session_manager)
        
        assert server.session_manager == mock_session_manager
        assert server.server is None
        
    @pytest.mark.asyncio
    async def test_handle_connection_creates_session(
        self,
        mock_session_manager,
        mock_websocket,
        mock_session
    ):
        """Test that handle_connection creates a session."""
        # Setup
        mock_session_manager.create_session = AsyncMock(return_value=mock_session)
        mock_session_manager.cleanup_session = AsyncMock()
        
        server = WebSocketServer(mock_session_manager)
        
        # Mock the receive and send loops to return immediately
        async def mock_receive(*args):
            await asyncio.sleep(0.01)
            
        async def mock_send(*args):
            await asyncio.sleep(0.01)
            
        with patch.object(server, 'receive_audio_loop', side_effect=mock_receive):
            with patch.object(server, 'send_audio_loop', side_effect=mock_send):
                await server.handle_connection(mock_websocket, "/")
        
        # Verify session was created
        mock_session_manager.create_session.assert_called_once_with(mock_websocket)
        
        # Verify cleanup was called
        mock_session_manager.cleanup_session.assert_called_once_with("test-session-123")
        
    @pytest.mark.asyncio
    async def test_handle_connection_cleanup_on_error(
        self,
        mock_session_manager,
        mock_websocket,
        mock_session
    ):
        """Test that handle_connection cleans up session on error."""
        # Setup
        mock_session_manager.create_session = AsyncMock(return_value=mock_session)
        mock_session_manager.cleanup_session = AsyncMock()
        
        server = WebSocketServer(mock_session_manager)
        
        # Mock receive loop to raise an error
        async def mock_receive_error(*args):
            raise Exception("Test error")
            
        async def mock_send(*args):
            await asyncio.sleep(10)  # Long sleep
            
        with patch.object(server, 'receive_audio_loop', side_effect=mock_receive_error):
            with patch.object(server, 'send_audio_loop', side_effect=mock_send):
                await server.handle_connection(mock_websocket, "/")
        
        # Verify cleanup was still called
        mock_session_manager.cleanup_session.assert_called_once_with("test-session-123")
        
    @pytest.mark.asyncio
    async def test_receive_audio_loop_parses_valid_frame(
        self,
        mock_session_manager,
        mock_websocket,
        mock_session
    ):
        """Test that receive_audio_loop correctly parses valid audio frames."""
        server = WebSocketServer(mock_session_manager)
        
        # Create valid audio frame message
        timestamp = datetime.now().timestamp()
        sequence_number = 42
        audio_data = b'\x00\x01' * 1000  # 2000 bytes of audio
        
        message = struct.pack('!dI', timestamp, sequence_number) + audio_data
        
        # Mock websocket to yield one message then close
        async def mock_iter(self):
            yield message
            
        mock_websocket.__aiter__ = mock_iter
        
        # Run receive loop in background
        task = asyncio.create_task(
            server.receive_audio_loop(mock_websocket, mock_session)
        )
        
        # Wait a bit for processing
        await asyncio.sleep(0.1)
        
        # Cancel task
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        
        # Verify AudioFrame was added to queue
        assert not mock_session.audio_queue.empty()
        audio_frame = await mock_session.audio_queue.get()
        
        assert audio_frame.session_id == "test-session-123"
        assert audio_frame.data == audio_data
        assert audio_frame.sequence_number == sequence_number
        assert audio_frame.sample_rate == 16000
        assert audio_frame.channels == 1
        
    @pytest.mark.asyncio
    async def test_receive_audio_loop_rejects_zero_timestamp(
        self,
        mock_session_manager,
        mock_websocket,
        mock_session
    ):
        """Test that receive_audio_loop rejects frames with zero timestamp."""
        server = WebSocketServer(mock_session_manager)
        
        # Create audio frame with zero timestamp
        timestamp = 0.0
        sequence_number = 42
        audio_data = b'\x00\x01' * 1000
        
        message = struct.pack('!dI', timestamp, sequence_number) + audio_data
        
        # Mock websocket to yield one message then close
        async def mock_iter(self):
            yield message
            
        mock_websocket.__aiter__ = mock_iter
        
        # Run receive loop in background
        task = asyncio.create_task(
            server.receive_audio_loop(mock_websocket, mock_session)
        )
        
        # Wait a bit for processing
        await asyncio.sleep(0.1)
        
        # Cancel task
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        
        # Verify AudioFrame was NOT added to queue
        assert mock_session.audio_queue.empty()
        
    @pytest.mark.asyncio
    async def test_receive_audio_loop_ignores_short_messages(
        self,
        mock_session_manager,
        mock_websocket,
        mock_session
    ):
        """Test that receive_audio_loop ignores messages that are too short."""
        server = WebSocketServer(mock_session_manager)
        
        # Create message that's too short (less than 12 bytes)
        message = b'\x00\x01\x02\x03'
        
        # Mock websocket to yield one message then close
        async def mock_iter(self):
            yield message
            
        mock_websocket.__aiter__ = mock_iter
        
        # Run receive loop in background
        task = asyncio.create_task(
            server.receive_audio_loop(mock_websocket, mock_session)
        )
        
        # Wait a bit for processing
        await asyncio.sleep(0.1)
        
        # Cancel task
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        
        # Verify AudioFrame was NOT added to queue
        assert mock_session.audio_queue.empty()
        
    @pytest.mark.asyncio
    async def test_receive_audio_loop_ignores_non_binary(
        self,
        mock_session_manager,
        mock_websocket,
        mock_session
    ):
        """Test that receive_audio_loop ignores non-binary messages."""
        server = WebSocketServer(mock_session_manager)
        
        # Mock websocket to yield text message
        async def mock_iter(self):
            yield "text message"
            
        mock_websocket.__aiter__ = mock_iter
        
        # Run receive loop in background
        task = asyncio.create_task(
            server.receive_audio_loop(mock_websocket, mock_session)
        )
        
        # Wait a bit for processing
        await asyncio.sleep(0.1)
        
        # Cancel task
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        
        # Verify AudioFrame was NOT added to queue
        assert mock_session.audio_queue.empty()
        
    @pytest.mark.asyncio
    async def test_send_audio_loop_sends_packets_with_sequence_numbers(
        self,
        mock_session_manager,
        mock_websocket,
        mock_session
    ):
        """Test that send_audio_loop sends packets with correct sequence numbers."""
        server = WebSocketServer(mock_session_manager)
        
        # Create TTS audio events
        tts_event1 = TTSAudioEvent(
            session_id="test-session-123",
            audio_data=b'\x00\x01' * 500,
            timestamp=datetime.now(),
            sequence_number=1,
            is_final=False
        )
        
        tts_event2 = TTSAudioEvent(
            session_id="test-session-123",
            audio_data=b'\x02\x03' * 500,
            timestamp=datetime.now(),
            sequence_number=2,
            is_final=True
        )
        
        # Add events to queue
        await mock_session.tts_queue.put(tts_event1)
        await mock_session.tts_queue.put(tts_event2)
        
        # Run send loop in background
        task = asyncio.create_task(
            server.send_audio_loop(mock_websocket, mock_session)
        )
        
        # Wait for processing
        await asyncio.sleep(0.2)
        
        # Cancel task
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        
        # Verify packets were sent
        assert mock_websocket.send.call_count == 2
        
        # Check first packet
        call1_args = mock_websocket.send.call_args_list[0][0][0]
        seq1, is_final1 = struct.unpack('!IB', call1_args[:5])
        audio1 = call1_args[5:]
        
        assert seq1 == 1
        assert is_final1 == 0
        assert audio1 == tts_event1.audio_data
        
        # Check second packet
        call2_args = mock_websocket.send.call_args_list[1][0][0]
        seq2, is_final2 = struct.unpack('!IB', call2_args[:5])
        audio2 = call2_args[5:]
        
        assert seq2 == 2
        assert is_final2 == 1
        assert audio2 == tts_event2.audio_data
        
    @pytest.mark.asyncio
    async def test_send_audio_loop_handles_backpressure(
        self,
        mock_session_manager,
        mock_websocket,
        mock_session
    ):
        """Test that send_audio_loop handles backpressure by dropping frames."""
        server = WebSocketServer(mock_session_manager)
        
        # Mock websocket.send to timeout (simulate slow client)
        async def slow_send(*args):
            raise asyncio.TimeoutError()
            
        mock_websocket.send = AsyncMock(side_effect=slow_send)
        
        # Create TTS audio event
        tts_event = TTSAudioEvent(
            session_id="test-session-123",
            audio_data=b'\x00\x01' * 500,
            timestamp=datetime.now(),
            sequence_number=1,
            is_final=False
        )
        
        # Add event to queue
        await mock_session.tts_queue.put(tts_event)
        
        # Run send loop in background
        task = asyncio.create_task(
            server.send_audio_loop(mock_websocket, mock_session)
        )
        
        # Wait for processing
        await asyncio.sleep(0.2)
        
        # Cancel task
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        
        # Verify send was attempted (frame was dropped due to timeout)
        assert mock_websocket.send.call_count >= 1
        
    @pytest.mark.asyncio
    async def test_send_audio_loop_closes_on_network_error(
        self,
        mock_session_manager,
        mock_websocket,
        mock_session
    ):
        """Test that send_audio_loop closes connection on network error."""
        server = WebSocketServer(mock_session_manager)
        
        # Mock websocket.send to raise network error
        async def network_error(*args):
            raise ConnectionError("Network error")
            
        mock_websocket.send = AsyncMock(side_effect=network_error)
        
        # Create TTS audio event
        tts_event = TTSAudioEvent(
            session_id="test-session-123",
            audio_data=b'\x00\x01' * 500,
            timestamp=datetime.now(),
            sequence_number=1,
            is_final=False
        )
        
        # Add event to queue
        await mock_session.tts_queue.put(tts_event)
        
        # Run send loop
        await server.send_audio_loop(mock_websocket, mock_session)
        
        # Verify connection was closed
        mock_websocket.close.assert_called_once()
