# Logging System Quick Start

## Overview

Production-ready structured logging with:
- ✅ JSON format for easy parsing
- ✅ Timestamp-based log files (one per run)
- ✅ Dual output (console + file)
- ✅ ISO 8601 UTC timestamps
- ✅ Dynamic contextual fields

## Quick Usage

### Basic Logging

```python
from src.infrastructure.logging import logger

logger.info("Application started")
logger.error("Connection failed", error_code=500)
```

### With Context

```python
logger.info(
    "Processing audio",
    session_id="session-123",
    component="asr",
    duration_ms=250
)
```

### Bound Logger

```python
# Create logger with persistent context
session_logger = logger.bind(
    session_id="session-123",
    user_id="user-456"
)

# All logs include the bound context
session_logger.info("Session started")
session_logger.info("Processing request")
```

## Log Files

### Location
```
logs/voice_assistant_YYYYMMDD_HHMMSS.log
```

### Format
Each line is a JSON object:
```json
{
  "timestamp": "2026-03-08T14:30:22.123456Z",
  "level": "info",
  "event": "Processing audio",
  "session_id": "session-123",
  "component": "asr"
}
```

## View Logs

```bash
# View latest log
cat logs/voice_assistant_*.log | tail -20

# Parse JSON (each line separately)
cat logs/voice_assistant_20260308_143022.log | while read line; do echo $line | python -m json.tool; done

# Filter errors
cat logs/*.log | grep '"level": "error"'

# Count by level
cat logs/*.log | grep -o '"level": "[^"]*"' | sort | uniq -c
```

## Examples

Run the logging example:
```bash
python examples/logging_example.py
```

## Documentation

Complete guide: [docs/logging_system.md](docs/logging_system.md)
