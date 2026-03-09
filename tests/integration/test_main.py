"""
Unit tests for main application entry point.

Tests basic initialization and configuration loading for the main application.
"""

import pytest
import os
from unittest.mock import Mock, patch, AsyncMock
from src.main import main


class TestMainEntryPoint:
    """Tests for main application entry point."""
    
    def test_main_module_imports(self):
        """Test that main module can be imported without errors."""
        import src.main
        assert hasattr(src.main, 'main')
        assert callable(src.main.main)
    
    @pytest.mark.asyncio
    async def test_main_requires_configuration(self):
        """Test that main exits with error when required configuration is missing."""
        # Clear any existing API key environment variables
        env_backup = {}
        for key in ['WHISPER_API_KEY', 'GEMINI_API_KEY', 'ELEVENLABS_API_KEY', 'ELEVENLABS_VOICE_ID']:
            env_backup[key] = os.environ.get(key)
            if key in os.environ:
                del os.environ[key]
        
        try:
            # Mock sys.exit to capture the exit call
            with patch('sys.exit') as mock_exit:
                await main()
                # Should have called sys.exit(1) due to missing config
                mock_exit.assert_called_once_with(1)
        finally:
            # Restore environment variables
            for key, value in env_backup.items():
                if value is not None:
                    os.environ[key] = value
    
    @pytest.mark.asyncio
    async def test_main_initialization_with_valid_config(self):
        """Test that main initializes all components with valid configuration."""
        # Set up minimal required configuration
        os.environ['WHISPER_API_KEY'] = 'test-whisper-key'
        os.environ['GEMINI_API_KEY'] = 'test-gemini-key'
        os.environ['ELEVENLABS_API_KEY'] = 'test-elevenlabs-key'
        os.environ['ELEVENLABS_VOICE_ID'] = 'test-voice-id'
        
        # Mock all the server start methods to prevent actual server startup
        with patch('src.main.WebSocketServer') as mock_ws_server, \
             patch('src.main.web.AppRunner') as mock_app_runner, \
             patch('src.main.web.TCPSite') as mock_tcp_site, \
             patch('asyncio.Event') as mock_event:
            
            # Configure mocks
            mock_ws_instance = Mock()
            mock_ws_instance.start = AsyncMock()
            mock_ws_server.return_value = mock_ws_instance
            
            mock_runner_instance = Mock()
            mock_runner_instance.setup = AsyncMock()
            mock_runner_instance.cleanup = AsyncMock()
            mock_app_runner.return_value = mock_runner_instance
            
            mock_site_instance = Mock()
            mock_site_instance.start = AsyncMock()
            mock_tcp_site.return_value = mock_site_instance
            
            # Mock the event to immediately trigger shutdown
            mock_event_instance = Mock()
            mock_event_instance.wait = AsyncMock(side_effect=KeyboardInterrupt())
            mock_event.return_value = mock_event_instance
            
            # Run main and expect KeyboardInterrupt
            try:
                await main()
            except KeyboardInterrupt:
                pass
            
            # Verify that servers were started
            mock_ws_instance.start.assert_called_once()
            mock_runner_instance.setup.assert_called()
            mock_site_instance.start.assert_called()
            
            # Verify cleanup was called
            mock_runner_instance.cleanup.assert_called_once()
