"""
Unit tests for utils.logger module.

Tests the logger package exports and integration.
"""

import pytest
from pathlib import Path

from src.utils.logger import ProductionLogger, logger
from src.utils import logger as utils_logger


class TestLoggerPackage:
    """Test suite for logger package."""
    
    def test_logger_exports(self):
        """Test that logger package exports correct classes."""
        from src.utils.logger import ProductionLogger, logger
        
        assert ProductionLogger is not None
        assert logger is not None
        assert isinstance(logger, ProductionLogger)
    
    def test_utils_exports_logger(self):
        """Test that utils package exports logger."""
        from src.utils import logger, ProductionLogger
        
        assert ProductionLogger is not None
        assert logger is not None
        assert isinstance(logger, ProductionLogger)
    
    def test_logger_singleton_across_imports(self):
        """Test that logger is same instance across different imports."""
        from src.utils.logger import logger as logger1
        from src.utils import logger as logger2
        from src.infrastructure import logger as logger3
        
        # All should be the same instance
        assert logger1 is logger2
        assert logger2 is logger3
    
    def test_logger_has_required_methods(self):
        """Test that logger has all required methods."""
        from src.utils.logger import logger
        
        assert hasattr(logger, 'debug')
        assert hasattr(logger, 'info')
        assert hasattr(logger, 'warning')
        assert hasattr(logger, 'error')
        assert hasattr(logger, 'exception')
        assert hasattr(logger, 'bind')
    
    def test_logger_creates_log_files(self, tmp_path):
        """Test that logger creates log files in logs directory."""
        ProductionLogger._initialized = False
        ProductionLogger._instance = None
        
        log_dir = tmp_path / "test_logs"
        test_logger = ProductionLogger(log_dir=str(log_dir))
        
        test_logger.info("Test message")
        
        # Verify log file exists
        log_files = list(log_dir.glob("*.log"))
        assert len(log_files) == 1
        
        # Cleanup
        ProductionLogger._initialized = False
        ProductionLogger._instance = None
