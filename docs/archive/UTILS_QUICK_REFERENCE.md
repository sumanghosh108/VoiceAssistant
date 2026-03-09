# Utils Package Quick Reference

## Import Patterns

```python
# Direct import (recommended)
from src.utils.logger import logger

# Via infrastructure (backward compatible)
from src.infrastructure import logger

# Via main package
from src import logger
```

## Basic Usage

```python
# Simple logging
logger.info("Application started")
logger.error("Error occurred", error_code=500)

# With context
logger.info("Processing", session_id="123", component="asr")

# Bound logger
session_logger = logger.bind(session_id="123")
session_logger.info("Event 1")
session_logger.info("Event 2")
```

## Log Files

**Location**: `logs/voice_assistant_YYYYMMDD_HHMMSS.log`

**Format**: JSON (one object per line)
```json
{"timestamp": "2026-03-08T14:30:22.123456Z", "level": "info", "event": "Message", "session_id": "123"}
```

## View Logs

```bash
# Latest log
cat logs/voice_assistant_*.log | tail -20

# Filter errors
cat logs/*.log | grep '"level": "error"'

# Specific session
cat logs/*.log | grep '"session_id": "session-123"'
```

## Test

```bash
# Run tests
pytest tests/unit/utils/ -v

# Run example
python examples/logging_example.py
```

## Documentation

- **Complete Guide**: [docs/logging_system.md](docs/logging_system.md)
- **Utils Package**: [src/utils/README.md](src/utils/README.md)
- **Quick Start**: [LOGGING_QUICK_START.md](LOGGING_QUICK_START.md)
