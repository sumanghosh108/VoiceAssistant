"""
Unit tests for production logging system (backward compatibility tests).

These tests verify that the new ProductionLogger maintains backward
compatibility with the old StructuredLogger interface.
"""

import json
import pytest
from pathlib import Path

from src.utils.logger import ProductionLogger


class TestProductionLoggerBackwardCompatibility:
    """Tests for backward compatibility with old StructuredLogger interface."""
    
    def test_logger_initialization(self, tmp_path):
        """Test logger initialization with different levels."""
        ProductionLogger._initialized = False
        ProductionLogger._instance = None
        
        logger = ProductionLogger(log_dir=str(tmp_path / "logs1"), level="DEBUG")
        assert logger.level == "DEBUG"
        
        ProductionLogger._initialized = False
        ProductionLogger._instance = None
        
        logger = ProductionLogger(log_dir=str(tmp_path / "logs2"), level="INFO")
        assert logger.level == "INFO"
        
        ProductionLogger._initialized = False
        ProductionLogger._instance = None
        
    def test_log_methods_exist(self, tmp_path):
        """Test that all log methods exist and work."""
        ProductionLogger._initialized = False
        ProductionLogger._instance = None
        
        logger = ProductionLogger(log_dir=str(tmp_path / "logs"), level="DEBUG")
        
        # Test each log level method exists
        assert hasattr(logger, 'debug')
        assert hasattr(logger, 'info')
        assert hasattr(logger, 'warning')
        assert hasattr(logger, 'error')
        assert hasattr(logger, 'exception')
        
        # Test they can be called
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        
        ProductionLogger._initialized = False
        ProductionLogger._instance = None
        
    def test_extra_fields_support(self, tmp_path):
        """Test that extra fields work like old logger."""
        ProductionLogger._initialized = False
        ProductionLogger._instance = None
        
        logger = ProductionLogger(log_dir=str(tmp_path / "logs"), level="INFO")
        
        logger.info(
            "Test message",
            session_id="session-123",
            component="test_component",
            custom_field="custom_value"
        )
        
        # Read log file
        log_file = list((tmp_path / "logs").glob("*.log"))[0]
        with open(log_file, 'r') as f:
            lines = f.readlines()
        
        # Find the test message
        for line in lines:
            log_data = json.loads(line.strip())
            if "Test message" in str(log_data):
                assert log_data["session_id"] == "session-123"
                assert log_data["component"] == "test_component"
                assert log_data["custom_field"] == "custom_value"
                break
        
        ProductionLogger._initialized = False
        ProductionLogger._instance = None
        
    def test_json_output_format(self, tmp_path):
        """Test that output is valid JSON."""
        ProductionLogger._initialized = False
        ProductionLogger._instance = None
        
        logger = ProductionLogger(log_dir=str(tmp_path / "logs"), level="INFO")
        
        logger.info("Test message", session_id="test-123")
        
        # Read log file
        log_file = list((tmp_path / "logs").glob("*.log"))[0]
        with open(log_file, 'r') as f:
            lines = f.readlines()
        
        # Every line should be valid JSON
        for line in lines:
            if line.strip():
                log_data = json.loads(line.strip())
                assert isinstance(log_data, dict)
                assert "timestamp" in log_data
                assert "level" in log_data
        
        ProductionLogger._initialized = False
        ProductionLogger._instance = None
        
    def test_component_and_session_context(self, tmp_path):
        """Test session_id and component fields in log context."""
        ProductionLogger._initialized = False
        ProductionLogger._instance = None
        
        logger = ProductionLogger(log_dir=str(tmp_path / "logs"), level="INFO")
        
        logger.info(
            "Processing audio",
            session_id="session-abc-123",
            component="asr_service"
        )
        
        # Read log file
        log_file = list((tmp_path / "logs").glob("*.log"))[0]
        with open(log_file, 'r') as f:
            lines = f.readlines()
        
        # Find the test message
        for line in lines:
            log_data = json.loads(line.strip())
            if "Processing audio" in str(log_data):
                assert log_data["session_id"] == "session-abc-123"
                assert log_data["component"] == "asr_service"
                break
        
        ProductionLogger._initialized = False
        ProductionLogger._instance = None
