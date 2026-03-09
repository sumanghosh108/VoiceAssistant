# Production Logging System

## Overview

The Real-Time Voice Assistant uses a production-ready structured logging system built on `structlog` that provides:

- **Structured JSON logging** for easy parsing and analysis
- **Dual output**: Console and persistent file logging
- **Timestamp-based log files** for each application run
- **ISO 8601 UTC timestamps** for consistency
- **Dynamic contextual fields** (session_id, component, user_id, etc.)
- **Automatic logs/ directory creation**

## Quick Start

### Basic Usage

```python
from src.infrastructure.logging import logger

# Simple logging
logger.info("Application started")
logger.error("Connection failed", error_code=500)
```

### With Context

```python
# Add context to individual log calls
logger.info(
    "Processing audio",
    session_id="session-123",
    component="asr",
    duration_ms=250
)
```

### Bound Logger (Persistent Context)

```python
# Create a logger with persistent context
session_logger = logger.bind(
    session_id="session-123",
    user_id="user-456"
)

# All subsequent logs include the bound context
session_logger.info("Session started")
session_logger.info("Processing request")
session_logger.error("Request failed")
```

## Log File Management

### File Naming

Each application run creates a new log file with timestamp:

```
logs/
├── voice_assistant_20260308_143022.log
├── voice_assistant_20260308_150145.log
└── voice_assistant_20260308_162330.log
```

Format: `voice_assistant_YYYYMMDD_HHMMSS.log`

### Directory Structure

```
project/
├── logs/                          # Auto-created on first run
│   ├── voice_assistant_*.log      # Timestamped log files
│   └── ...
└── src/
    └── infrastructure/
        └── logging.py             # Logger implementation
```

## Log Format

### JSON Structure

Each log entry is a single-line JSON object:

```json
{
  "timestamp": "2026-03-08T14:30:22.123456Z",
  "level": "info",
  "event": "Processing audio",
  "session_id": "session-123",
  "component": "asr",
  "duration_ms": 250
}
```

### Required Fields

- `timestamp`: ISO 8601 UTC timestamp
- `level`: Log level (debug, info, warning, error)
- `event`: Log message

### Optional Fields

Any additional fields passed as kwargs:
- `session_id`: Session identifier
- `component`: Component name (asr, llm, tts, etc.)
- `user_id`: User identifier
- `error`: Error details
- `filename`: File being processed
- Custom metadata fields

## Usage Examples

### Service Logging

```python
from src.infrastructure.logging import logger

class ASRService:
    def __init__(self):
        self.logger = logger.bind(component="asr")
    
    async def transcribe(self, audio_data: bytes, session_id: str):
        self.logger.info(
            "Starting transcription",
            session_id=session_id,
            audio_size=len(audio_data)
        )
        
        try:
            result = await self._call_api(audio_data)
            self.logger.info(
                "Transcription complete",
                session_id=session_id,
                text_length=len(result)
            )
            return result
        except Exception as e:
            self.logger.error(
                "Transcription failed",
                session_id=session_id,
                error=str(e)
            )
            raise
```

### Session Logging

```python
from src.infrastructure.logging import logger

class SessionManager:
    async def create_session(self, websocket):
        session_id = str(uuid.uuid4())
        
        # Create session-specific logger
        session_logger = logger.bind(
            session_id=session_id,
            component="session"
        )
        
        session_logger.info("Session created")
        
        # Pass to other components
        await self.process_audio(session_logger)
        
        session_logger.info("Session ended")
```

### Error Logging with Exception

```python
from src.infrastructure.logging import logger

try:
    result = await risky_operation()
except Exception as e:
    logger.exception(
        "Operation failed",
        component="service",
        operation="risky_operation",
        error_type=type(e).__name__
    )
    raise
```

## Configuration

### Log Level

Set log level via environment variable or config:

```python
# In config or environment
LOG_LEVEL=DEBUG  # DEBUG, INFO, WARNING, ERROR

# Or programmatically
logger = ProductionLogger(log_dir="logs", level="DEBUG")
```

### Custom Log Directory

```python
from src.infrastructure.logging import ProductionLogger

# Use custom directory
logger = ProductionLogger(log_dir="custom_logs")
```

## Log Analysis

### Reading Logs

```bash
# View latest log file
tail -f logs/voice_assistant_*.log | tail -1

# Parse JSON logs with jq
cat logs/voice_assistant_20260308_143022.log | jq '.'

# Filter by level
cat logs/*.log | jq 'select(.level == "error")'

# Filter by session
cat logs/*.log | jq 'select(.session_id == "session-123")'

# Count errors
cat logs/*.log | jq 'select(.level == "error")' | wc -l
```

### Python Analysis

```python
import json
from pathlib import Path

# Read and parse log file
log_file = Path("logs/voice_assistant_20260308_143022.log")
with open(log_file) as f:
    logs = [json.loads(line) for line in f]

# Filter errors
errors = [log for log in logs if log['level'] == 'error']

# Group by session
from collections import defaultdict
by_session = defaultdict(list)
for log in logs:
    if 'session_id' in log:
        by_session[log['session_id']].append(log)
```

## Best Practices

### 1. Use Bound Loggers for Context

```python
# Good: Bind context once
session_logger = logger.bind(session_id=session_id)
session_logger.info("Event 1")
session_logger.info("Event 2")

# Avoid: Repeating context
logger.info("Event 1", session_id=session_id)
logger.info("Event 2", session_id=session_id)
```

### 2. Include Relevant Context

```python
# Good: Rich context
logger.info(
    "Request processed",
    session_id=session_id,
    duration_ms=duration,
    status="success"
)

# Avoid: Minimal context
logger.info("Request processed")
```

### 3. Use Appropriate Log Levels

- `DEBUG`: Detailed diagnostic information
- `INFO`: General informational messages
- `WARNING`: Warning messages for potentially harmful situations
- `ERROR`: Error messages for serious problems

### 4. Structure Error Logs

```python
logger.error(
    "Service call failed",
    component="asr",
    service="whisper",
    error_type="TimeoutError",
    retry_count=3,
    session_id=session_id
)
```

## Integration with Existing Code

The new `ProductionLogger` is backward compatible with the existing logging interface:

```python
# Old way (still works)
from src.infrastructure.logging import logger
logger.info("Message", session_id="123")

# New way (same interface)
from src.infrastructure.logging import logger
logger.info("Message", session_id="123")
```

All existing code continues to work without changes.

## Log Rotation

For production deployments, consider using log rotation:

### Using logrotate (Linux)

```bash
# /etc/logrotate.d/voice-assistant
/path/to/project/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0644 user group
    sharedscripts
}
```

### Using Python logging.handlers

```python
from logging.handlers import RotatingFileHandler

# Add to ProductionLogger if needed
handler = RotatingFileHandler(
    log_file,
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
```

## Monitoring and Alerting

### Log Aggregation

Send logs to centralized systems:

- **ELK Stack**: Elasticsearch, Logstash, Kibana
- **Splunk**: Enterprise log management
- **CloudWatch**: AWS log aggregation
- **Datadog**: Application monitoring

### Example: Filebeat Configuration

```yaml
filebeat.inputs:
- type: log
  enabled: true
  paths:
    - /path/to/logs/voice_assistant_*.log
  json.keys_under_root: true
  json.add_error_key: true

output.elasticsearch:
  hosts: ["localhost:9200"]
```

## Performance Considerations

### Async Logging

For high-throughput scenarios, consider async logging:

```python
# structlog supports async processors
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.JSONRenderer(),
    ],
    logger_factory=structlog.PrintLoggerFactory(),
)
```

### Log Sampling

For very high-volume logs, implement sampling:

```python
import random

def should_log_debug():
    return random.random() < 0.1  # Log 10% of debug messages

if should_log_debug():
    logger.debug("High-volume debug message")
```

## Troubleshooting

### Issue: Logs directory not created

**Solution**: Check write permissions in project directory

```bash
# Linux/macOS
chmod 755 .

# Windows
icacls . /grant Users:F
```

### Issue: Log file not found

**Solution**: Logger creates file on first log call

```python
# Ensure at least one log is written
logger.info("Application started")
```

### Issue: Duplicate log entries

**Solution**: Singleton pattern prevents this, but if you see duplicates:

```python
# Reset logger instance
ProductionLogger._initialized = False
ProductionLogger._instance = None
logger = ProductionLogger()
```

## Testing

Run the logging tests:

```bash
pytest tests/unit/infrastructure/test_production_logging.py -v
```

## Migration from Old Logger

The new logger is a drop-in replacement:

```python
# Before
from src.infrastructure.logging import logger, StructuredLogger

# After
from src.infrastructure.logging import logger, ProductionLogger
```

All method signatures remain the same, so no code changes needed.

## Summary

The production logging system provides:

✅ Structured JSON logs for easy parsing
✅ Persistent file storage with timestamps
✅ Console output for development
✅ Rich contextual information
✅ ISO 8601 UTC timestamps
✅ Exception tracking with tracebacks
✅ Singleton pattern for consistency
✅ Backward compatible interface

Perfect for production deployments with centralized log aggregation and monitoring systems.
