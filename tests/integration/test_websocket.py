"""
Integration tests for WebSocket server with session management.

Tests the complete integration between WebSocketServer and SessionManager,
verifying that audio flows correctly through the pipeline.
"""

import asyncio
import struct
from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest

from src.core.events import AudioFrame, TTSAudioEvent
from src.core.models import SessionManager
from src.api.websocket import WebSocketServer


@pytest.fixture
def mock_services():
    """Create mock ASR, LLM, and TTS services."""
    asr_service = Mock()
    llm_service = Mock()
    tts_service = Mock()
    
    # Mock process methods to be async no-ops
    async def mock_process(*args, **kwargs):
        await asyncio.sleep(10)  # Long sleep to keep tasks alive
        
    asr_service.process_audio_stream = AsyncMock(side_effect=mock_process)
    llm_service.process_transcript_stream = AsyncMock(side_effect=mock_process)
    tts_service.process_token_stream = AsyncMock(side_effect=mock_process)
    
    return asr_service, llm_service, tts_service


@pytest.fixture
def session_manager(mock_services):
    """Create a SessionManager with mock services."""
    asr_service, llm_service, tts_service = mock_services
    
    manager = SessionManager(
        asr_service=asr_service,
        llm_service=llm_service,
        tts_service=tts_service,
        enable_recording=False
    )
    
    return manager


@pytest.fixture
def websocket_server(session_manager):
    """Create a WebSocketServer with SessionManager."""
    return WebSocketServer(session_manager)


class TestWebSocketIntegration:
    """Integration tests for WebSocket server."""
    
    @pytest.mark.asyncio
    async def test_audio_flows_through_pipeline(
        self,
        websocket_server,
        session_manager
    ):
        ""