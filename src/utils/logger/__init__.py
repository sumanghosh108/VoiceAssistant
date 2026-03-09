"""
Production-ready structured logging system.

This module provides structured logging using structlog with:
- JSON formatting for both console and file output
- ISO 8601 UTC timestamps
- Automatic logs/ directory creation
- Timestamp-based log file names for each run
- Support for dynamic contextual fields
- Dual output: console and persistent file logging
"""

from src.utils.logger.logger import ProductionLogger, logger

__all__ = [
    "ProductionLogger",
    "logger",
]
