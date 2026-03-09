"""
Production-ready structured logging system with file and console output.

This module provides structured logging using structlog with:
- JSON formatting for both console and file output
- ISO 8601 UTC timestamps
- Automatic logs/ directory creation
- Timestamp-based log file names for each run
- Support for dynamic contextual fields (session_id, component, user_id, etc.)
- Dual output: console and persistent file logging
"""

import os
import structlog
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


class ProductionLogger:
    """
    Production-ready structured logger with file and console output.
    
    Features:
    - Structured JSON logging using structlog
    - Automatic logs/ directory creation
    - Timestamp-based log files for each run
    - ISO 8601 UTC timestamps
    - Console and file output simultaneously
    - Dynamic contextual fields support
    """
    
    _instance: Optional['ProductionLogger'] = None
    _initialized: bool = False
    
    def __new__(cls, log_dir: str = "logs", level: str = "INFO"):
        """Singleton pattern to ensure single logger instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, log_dir: str = "logs", level: str = "INFO"):
        """
        Initialize production logger.
        
        Args:
            log_dir: Directory for log files (default: "logs")
            level: Log level (DEBUG, INFO, WARNING, ERROR)
        """
        # Only initialize once
        if ProductionLogger._initialized:
            return
            
        self.log_dir = Path(log_dir)
        self.level = level.upper()
        self.log_file = self._create_log_file()
        
        # Configure structlog
        self._configure_structlog()
        
        # Get logger instance
        self.logger = structlog.get_logger("voice_assistant")
        
        ProductionLogger._initialized = True
        
        # Log initialization
        self.logger.info(
            "Logger initialized",
            log_file=str(self.log_file),
            log_level=self.level
        )
    
    def _create_log_file(self) -> Path:
        """
        Create logs directory and generate timestamp-based log file.
        
        Returns:
            Path to the log file
        """
        # Create logs directory if it doesn't exist
        self.log_dir.mkdir(exist_ok=True)
        
        # Generate timestamp-based filename
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        log_file = self.log_dir / f"voice_assistant_{timestamp}.log"
        
        return log_file
    
    def _configure_structlog(self) -> None:
        """Configure structlog with processors and output handlers."""
        import logging
        
        # Map string level to logging constant
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR
        }
        log_level = level_map.get(self.level, logging.INFO)
        
        # Shared processors for both console and file
        shared_processors = [
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
        ]
        
        # Configure structlog
        structlog.configure(
            processors=[
                *shared_processors,
                structlog.processors.JSONRenderer()
            ],
            wrapper_class=structlog.make_filtering_bound_logger(log_level),
            context_class=dict,
            logger_factory=self._create_logger_factory(),
            cache_logger_on_first_use=True,
        )
    
    def _create_logger_factory(self):
        """
        Create a logger factory that outputs to both console and file.
        
        Returns:
            Logger factory function
        """
        import logging
        import sys
        
        # Create file handler
        file_handler = logging.FileHandler(str(self.log_file), encoding='utf-8')
        file_handler.setLevel(getattr(logging, self.level))
        
        # Create console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, self.level))
        
        # Create logger factory
        def factory(*args):
            """Factory function for creating loggers."""
            logger = logging.getLogger(*args)
            logger.setLevel(getattr(logging, self.level))
            logger.handlers.clear()
            logger.addHandler(file_handler)
            logger.addHandler(console_handler)
            logger.propagate = False
            return logger
        
        return factory
    
    def bind(self, **kwargs) -> structlog.BoundLogger:
        """
        Bind contextual fields to logger.
        
        Args:
            **kwargs: Context fields (e.g., session_id, component, user_id)
            
        Returns:
            Bound logger with context
        """
        return self.logger.bind(**kwargs)
    
    def debug(self, message: str, **kwargs) -> None:
        """
        Log debug message.
        
        Args:
            message: Log message
            **kwargs: Extra fields (session_id, component, user_id, etc.)
        """
        self.logger.debug(message, **kwargs)
    
    def info(self, message: str, **kwargs) -> None:
        """
        Log info message.
        
        Args:
            message: Log message
            **kwargs: Extra fields (session_id, component, user_id, etc.)
        """
        self.logger.info(message, **kwargs)
    
    def warning(self, message: str, **kwargs) -> None:
        """
        Log warning message.
        
        Args:
            message: Log message
            **kwargs: Extra fields (session_id, component, user_id, etc.)
        """
        self.logger.warning(message, **kwargs)
    
    def error(self, message: str, **kwargs) -> None:
        """
        Log error message.
        
        Args:
            message: Log message
            **kwargs: Extra fields (session_id, component, user_id, etc.)
        """
        self.logger.error(message, **kwargs)
    
    def exception(self, message: str, **kwargs) -> None:
        """
        Log exception with traceback.
        
        Args:
            message: Log message
            **kwargs: Extra fields (session_id, component, user_id, etc.)
        """
        self.logger.exception(message, **kwargs)


# Global logger instance
logger = ProductionLogger()
