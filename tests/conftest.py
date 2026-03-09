"""
Pytest configuration and shared fixtures for all tests.

This file is automatically loaded by pytest and provides:
- Shared fixtures available to all tests
- Test configuration
- Common test utilities
"""

import pytest
import sys
from pathlib import Path

# Add src directory to Python path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


# Import shared fixtures from fixtures module
pytest_plugins = ["tests.fixtures.mocks"]


@pytest.fixture(scope="session")
def test_data_dir():
    """Return path to test data directory."""
    return Path(__file__).parent / "data"


@pytest.fixture(scope="session")
def temp_recordings_dir(tmp_path_factory):
    """Create temporary directory for test recordings."""
    return tmp_path_factory.mktemp("recordings")


@pytest.fixture(autouse=True)
def reset_logging():
    """Reset logging configuration between tests."""
    import logging
    # Clear all handlers
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    yield
    # Cleanup after test
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
