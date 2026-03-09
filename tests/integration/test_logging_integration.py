"""
Integration tests for production logging system.

Tests that the logging system integrates correctly with the application
and produces valid log files with proper formatting.
"""

import json
import pytest
from pathlib import Path
from datetime import datetime

from src.utils.logger import ProductionLogger


class TestLoggingIntegration:
    """Integration tests for production logging."""
    
    def test_complete_logging_workflow(self, tmp_path):
        """Test complete logging workflow from initialization to file output."""
        # Reset logger
        ProductionLogger._initialized = False
        ProductionLogger._instance = None
        
        log_dir = tmp_path / "integration_logs"
        logger = ProductionLogger(log_dir=str(log_dir), level="INFO")
        
        # Simulate application logging
        logger.info("Application started", component="main")
        
        # Simulate session logging
        session_logger = logger.bind(session_id="session-integration-test")
        session_logger.info("Session created", user_id="user-123")
        session_logger.info("Processing audio", component="asr", duration_ms=250)
        session_logger.info("Generating response", component="llm", tokens=150)
        session_logger.info("Synthesizing speech", component="tts", audio_size=8192)
        session_logger.info("Session completed")
        
        # Simulate error
        logger.error(
            "Service error",
            component="tts",
            error_type="TimeoutError",
            retry_count=3
        )
        
        # Verify log file exists
        log_files = list(log_dir.glob("*.log"))
        assert len(log_files) == 1
        
        log_file = log_files[0]
        assert log_file.exists()
        
        # Read and parse all log entries
        with open(log_file, 'r') as f:
            lines = f.readlines()
        
        # Should have multiple log entries
        assert len(lines) >= 7
        
        # Parse and verify each entry
        log_entries = []
        for line in lines:
            if line.strip():
                entry = json.loads(line.strip())
                log_entries.append(entry)
        
        # Verify all entries have required fields
        for entry in log_entries:
            assert "timestamp" in entry
            assert "level" in entry
            assert "event" in entry or "message" in entry
            
            # Verify timestamp format
            timestamp = entry["timestamp"]
            assert timestamp.endswith("Z")
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            assert isinstance(dt, datetime)
        
        # Verify session context is present in session logs
        session_logs = [e for e in log_entries if e.get("session_id") == "session-integration-test"]
        assert len(session_logs) >= 5
        
        for log in session_logs:
            assert log["session_id"] == "session-integration-test"
        
        # Verify error log has error details
        error_logs = [e for e in log_entries if e.get("level") == "error"]
        assert len(error_logs) >= 1
        
        error_log = error_logs[0]
        assert error_log.get("component") == "tts"
        assert error_log.get("error_type") == "TimeoutError"
        
        # Cleanup
        ProductionLogger._initialized = False
        ProductionLogger._instance = None
    
    def test_multiple_sessions_logging(self, tmp_path):
        """Test logging from multiple concurrent sessions."""
        # Reset logger
        ProductionLogger._initialized = False
        ProductionLogger._instance = None
        
        log_dir = tmp_path / "multi_session_logs"
        logger = ProductionLogger(log_dir=str(log_dir), level="INFO")
        
        # Simulate multiple sessions
        sessions = ["session-1", "session-2", "session-3"]
        
        for session_id in sessions:
            session_logger = logger.bind(session_id=session_id)
            session_logger.info("Session started")
            session_logger.info("Processing audio", component="asr")
            session_logger.info("Session ended")
        
        # Read log file
        log_file = list(log_dir.glob("*.log"))[0]
        with open(log_file, 'r') as f:
            lines = f.readlines()
        
        # Parse logs
        log_entries = [json.loads(line.strip()) for line in lines if line.strip()]
        
        # Verify logs from all sessions
        for session_id in sessions:
            session_logs = [e for e in log_entries if e.get("session_id") == session_id]
            assert len(session_logs) >= 3
        
        # Cleanup
        ProductionLogger._initialized = False
        ProductionLogger._instance = None
    
    def test_high_volume_logging(self, tmp_path):
        """Test logging system handles high volume of logs."""
        # Reset logger
        ProductionLogger._initialized = False
        ProductionLogger._instance = None
        
        log_dir = tmp_path / "high_volume_logs"
        logger = ProductionLogger(log_dir=str(log_dir), level="INFO")
        
        # Generate many log entries
        num_logs = 1000
        for i in range(num_logs):
            logger.info(
                f"Log entry {i}",
                index=i,
                component="test",
                session_id=f"session-{i % 10}"
            )
        
        # Verify log file
        log_file = list(log_dir.glob("*.log"))[0]
        with open(log_file, 'r') as f:
            lines = f.readlines()
        
        # Should have at least num_logs + 1 (initialization log)
        assert len(lines) >= num_logs
        
        # Verify all are valid JSON
        for line in lines:
            if line.strip():
                entry = json.loads(line.strip())
                assert "timestamp" in entry
                assert "level" in entry
        
        # Cleanup
        ProductionLogger._initialized = False
        ProductionLogger._instance = None
    
    def test_logging_with_special_characters(self, tmp_path):
        """Test logging handles special characters correctly."""
        # Reset logger
        ProductionLogger._initialized = False
        ProductionLogger._instance = None
        
        log_dir = tmp_path / "special_char_logs"
        logger = ProductionLogger(log_dir=str(log_dir), level="INFO")
        
        # Log with special characters
        logger.info(
            'Message with "quotes" and \\backslashes\\',
            text='Special: \n\t\r',
            unicode="Hello 世界 🌍"
        )
        
        # Read and verify
        log_file = list(log_dir.glob("*.log"))[0]
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Find the special message
        for line in lines:
            if "Special:" in line:
                entry = json.loads(line.strip())
                assert "quotes" in entry.get("event", "")
                assert entry.get("unicode") == "Hello 世界 🌍"
                break
        
        # Cleanup
        ProductionLogger._initialized = False
        ProductionLogger._instance = None
