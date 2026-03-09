"""
Unit tests for production logging system with structlog.

Tests the ProductionLogger class including:
- Log file creation with timestamps
- Dual output (console and file)
- Structured JSON logging
- Dynamic contextual fields
- ISO 8601 UTC timestamps
"""

import json
import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock
import structlog

from src.utils.logger import ProductionLogger


class TestProductionLogger:
    """Test suite for ProductionLogger."""
    
    def test_logger_creates_logs_directory(self, tmp_path):
        """Test that logger creates logs directory if it doesn't exist."""
        log_dir = tmp_path / "test_logs"
        assert not log_dir.exists()
        
        logger = ProductionLogger.__new__(ProductionLogger)
        ProductionLogger._initialized = False
        logger.__init__(log_dir=str(log_dir))
        
        assert log_dir.exists()
        assert log_dir.is_dir()
        
        # Cleanup
        ProductionLogger._initialized = False
    
    def test_log_file_naming_format(self, tmp_path):
        """Test that log files use timestamp-based naming."""
        log_dir = tmp_path / "test_logs"
        
        logger = ProductionLogger.__new__(ProductionLogger)
        ProductionLogger._initialized = False
        logger.__init__(log_dir=str(log_dir))
        
        # Check log file exists and has correct format
        log_files = list(log_dir.glob("voice_assistant_*.log"))
        assert len(log_files) == 1
        
        log_file = log_files[0]
        # Format: voice_assistant_YYYYMMDD_HHMMSS.log
        assert log_file.name.startswith("voice_assistant_")
        assert log_file.name.endswith(".log")
        
        # Extract timestamp part
        timestamp_part = log_file.stem.replace("voice_assistant_", "")
        # Should be in format YYYYMMDD_HHMMSS
        assert len(timestamp_part) == 15  # YYYYMMDD_HHMMSS
        assert timestamp_part[8] == "_"
        
        # Cleanup
        ProductionLogger._initialized = False
    
    def test_singleton_pattern(self, tmp_path):
        """Test that ProductionLogger follows singleton pattern."""
        log_dir = tmp_path / "test_logs"
        
        ProductionLogger._initialized = False
        ProductionLogger._instance = None
        
        logger1 = ProductionLogger(log_dir=str(log_dir))
        logger2 = ProductionLogger(log_dir=str(log_dir))
        
        assert logger1 is logger2
        
        # Cleanup
        ProductionLogger._initialized = False
        ProductionLogger._instance = None
    
    def test_log_levels(self, tmp_path):
        """Test that all log levels work correctly."""
        log_dir = tmp_path / "test_logs"
        
        logger = ProductionLogger.__new__(ProductionLogger)
        ProductionLogger._initialized = False
        logger.__init__(log_dir=str(log_dir))
        
        # Log at different levels
        logger.debug("Debug message", component="test")
        logger.info("Info message", component="test")
        logger.warning("Warning message", component="test")
        logger.error("Error message", component="test")
        
        # Read log file
        log_file = list(log_dir.glob("*.log"))[0]
        with open(log_file, 'r') as f:
            lines = f.readlines()
        
        # Should have at least 4 log entries (debug might be filtered)
        assert len(lines) >= 3
        
        # Parse and verify JSON format
        for line in lines:
            log_entry = json.loads(line.strip())
            assert "event" in log_entry or "message" in log_entry
            assert "timestamp" in log_entry
            assert "level" in log_entry
        
        # Cleanup
        ProductionLogger._initialized = False
    
    def test_contextual_fields(self, tmp_path):
        """Test that contextual fields are included in logs."""
        log_dir = tmp_path / "test_logs"
        
        logger = ProductionLogger.__new__(ProductionLogger)
        ProductionLogger._initialized = False
        logger.__init__(log_dir=str(log_dir))
        
        # Log with various contextual fields
        logger.info(
            "Test message",
            session_id="session-123",
            component="asr",
            user_id="user-456",
            custom_field="custom_value"
        )
        
        # Read log file
        log_file = list(log_dir.glob("*.log"))[0]
        with open(log_file, 'r') as f:
            lines = f.readlines()
        
        # Find the test message
        test_log = None
        for line in lines:
            log_entry = json.loads(line.strip())
            if "Test message" in str(log_entry):
                test_log = log_entry
                break
        
        assert test_log is not None
        assert test_log.get("session_id") == "session-123"
        assert test_log.get("component") == "asr"
        assert test_log.get("user_id") == "user-456"
        assert test_log.get("custom_field") == "custom_value"
        
        # Cleanup
        ProductionLogger._initialized = False
    
    def test_bind_context(self, tmp_path):
        """Test that bind() creates logger with persistent context."""
        log_dir = tmp_path / "test_logs"
        
        logger = ProductionLogger.__new__(ProductionLogger)
        ProductionLogger._initialized = False
        logger.__init__(log_dir=str(log_dir))
        
        # Create bound logger with context
        bound_logger = logger.bind(session_id="session-789", component="tts")
        
        # Log messages with bound context
        bound_logger.info("First message")
        bound_logger.info("Second message")
        
        # Read log file
        log_file = list(log_dir.glob("*.log"))[0]
        with open(log_file, 'r') as f:
            lines = f.readlines()
        
        # Check that both messages have the bound context
        message_logs = []
        for line in lines:
            log_entry = json.loads(line.strip())
            if "First message" in str(log_entry) or "Second message" in str(log_entry):
                message_logs.append(log_entry)
        
        assert len(message_logs) == 2
        for log_entry in message_logs:
            assert log_entry.get("session_id") == "session-789"
            assert log_entry.get("component") == "tts"
        
        # Cleanup
        ProductionLogger._initialized = False
    
    def test_iso8601_timestamp_format(self, tmp_path):
        """Test that timestamps are in ISO 8601 UTC format."""
        log_dir = tmp_path / "test_logs"
        
        logger = ProductionLogger.__new__(ProductionLogger)
        ProductionLogger._initialized = False
        logger.__init__(log_dir=str(log_dir))
        
        logger.info("Timestamp test")
        
        # Read log file
        log_file = list(log_dir.glob("*.log"))[0]
        with open(log_file, 'r') as f:
            lines = f.readlines()
        
        # Find the test message
        for line in lines:
            log_entry = json.loads(line.strip())
            if "Timestamp test" in str(log_entry):
                timestamp = log_entry.get("timestamp")
                assert timestamp is not None
                
                # Verify ISO 8601 format (can be parsed)
                parsed = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                assert parsed is not None
                
                # Should end with Z (UTC)
                assert timestamp.endswith('Z')
                break
        
        # Cleanup
        ProductionLogger._initialized = False
    
    def test_exception_logging(self, tmp_path):
        """Test that exceptions are logged with traceback."""
        log_dir = tmp_path / "test_logs"
        
        logger = ProductionLogger.__new__(ProductionLogger)
        ProductionLogger._initialized = False
        logger.__init__(log_dir=str(log_dir))
        
        # Log an exception
        try:
            raise ValueError("Test exception")
        except ValueError:
            logger.exception("Exception occurred", component="test")
        
        # Read log file
        log_file = list(log_dir.glob("*.log"))[0]
        with open(log_file, 'r') as f:
            content = f.read()
        
        # Should contain exception information
        assert "Exception occurred" in content
        assert "ValueError" in content or "exception" in content.lower()
        
        # Cleanup
        ProductionLogger._initialized = False
    
    def test_multiple_runs_create_different_files(self, tmp_path):
        """Test that different runs create different log files."""
        log_dir = tmp_path / "test_logs"
        
        # First run
        ProductionLogger._initialized = False
        ProductionLogger._instance = None
        logger1 = ProductionLogger(log_dir=str(log_dir))
        logger1.info("First run")
        log_file1 = logger1.log_file
        
        # Reset for second run
        ProductionLogger._initialized = False
        ProductionLogger._instance = None
        
        # Small delay to ensure different timestamp
        import time
        time.sleep(1)
        
        # Second run
        logger2 = ProductionLogger(log_dir=str(log_dir))
        logger2.info("Second run")
        log_file2 = logger2.log_file
        
        # Should have different log files
        assert log_file1 != log_file2
        assert log_file1.exists()
        assert log_file2.exists()
        
        # Cleanup
        ProductionLogger._initialized = False
        ProductionLogger._instance = None
    
    def test_json_format_validity(self, tmp_path):
        """Test that all log entries are valid JSON."""
        log_dir = tmp_path / "test_logs"
        
        logger = ProductionLogger.__new__(ProductionLogger)
        ProductionLogger._initialized = False
        logger.__init__(log_dir=str(log_dir))
        
        # Log various messages
        logger.info("Simple message")
        logger.info("Message with context", session_id="123", component="test")
        logger.warning("Warning message", error_code=404)
        logger.error("Error message", exception_type="ValueError")
        
        # Read log file
        log_file = list(log_dir.glob("*.log"))[0]
        with open(log_file, 'r') as f:
            lines = f.readlines()
        
        # Every line should be valid JSON
        for line in lines:
            if line.strip():
                log_entry = json.loads(line.strip())
                assert isinstance(log_entry, dict)
                assert "timestamp" in log_entry
                assert "level" in log_entry
        
        # Cleanup
        ProductionLogger._initialized = False

