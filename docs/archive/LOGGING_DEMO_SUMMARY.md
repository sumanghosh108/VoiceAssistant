# Logging System Demonstration Summary

## ✅ What You Can See

### 1. Log Files Created Automatically

Every time the application runs, a new timestamped log file is created:

```
logs/
├── voice_assistant_20260308_060752.log  ← Latest (5,079 bytes)
├── voice_assistant_20260308_060547.log
├── voice_assistant_20260308_060433.log
└── ... (17 log files total)
```

### 2. Structured JSON Logs

Each log entry is a JSON object with:
- **timestamp**: ISO 8601 UTC format
- **level**: info, warning, error
- **event**: What happened
- **Custom fields**: session_id, component, user_id, etc.

Example:
```json
{
  "timestamp": "2026-03-08T06:07:58.569599Z",
  "level": "info",
  "event": "Transcription completed",
  "session_id": "session-real-001",
  "user_id": "user-alice",
  "component": "asr",
  "text": "Hello, how are you?",
  "duration_ms": 150
}
```

### 3. Dual Output

Logs appear in **both**:
- ✅ Console (for development)
- ✅ File (for persistence)

### 4. Rich Context

Each log includes relevant context:
- **Session tracking**: `session_id`, `user_id`
- **Component identification**: `component` (asr, llm, tts)
- **Performance metrics**: `duration_ms`, `audio_size`
- **Error details**: `error_type`, `retry_count`
- **Exception tracebacks**: Full stack traces

## 🎯 Demo Scripts

### 1. Run Full Demonstration
```bash
python test_logging_demo.py
```

**Shows:**
- Basic logging (info, warning, error)
- Contextual fields
- Bound loggers
- Error logging
- Exception with traceback
- Simulated voice assistant session

### 2. View Logs with Filters

**List all log files:**
```bash
python view_logs.py list
```

**View latest log:**
```bash
python view_logs.py latest
```

**View latest 10 entries:**
```bash
python view_logs.py latest --limit 10
```

**View only errors:**
```bash
python view_logs.py latest --level error
```

**View specific session:**
```bash
python view_logs.py latest --session session-real-001
```

**View specific component:**
```bash
python view_logs.py latest --component asr
```

**Combine filters:**
```bash
python view_logs.py latest --level error --limit 5
```

## 📊 What Was Logged in Demo

### Basic Logs
- ✅ Application started
- ✅ Warning message
- ✅ Error message

### Contextual Logs
- ✅ User login (with user_id, ip_address, login_method)
- ✅ Audio processing (with session_id, component, duration)
- ✅ API calls (with service, response_time, token_count)

### Session Logs (with persistent context)
- ✅ Session created
- ✅ Audio streaming started
- ✅ Transcription in progress
- ✅ Response generated
- ✅ Session completed

### Error Logs
- ✅ Service timeout (with retry_count, timeout_ms)
- ✅ API rate limit (with error_code, retry_after)
- ✅ Exception with full traceback

### Real Session Simulation
- ✅ WebSocket connection
- ✅ Audio frame received
- ✅ ASR transcription (started → completed)
- ✅ LLM processing (started → response generated)
- ✅ TTS synthesis (started → completed)
- ✅ Audio response sent
- ✅ Session ended

## 🔍 Filtering Examples

### By Error Level
```bash
python view_logs.py latest --level error
```

**Output:**
```
[ERROR] Service timeout
  • component: tts
  • error_type: TimeoutError
  • retry_count: 3

[ERROR] API rate limit exceeded
  • error_code: 429
  • retry_after_seconds: 60

[ERROR] Division by zero error
  • exception: [Full traceback shown]
```

### By Session ID
```bash
python view_logs.py latest --session session-real-001
```

**Output:**
```
[INFO] WebSocket connection established
[INFO] Audio frame received
[INFO] Transcription started
[INFO] Transcription completed
[INFO] LLM processing started
[INFO] LLM response generated
[INFO] TTS synthesis started
[INFO] TTS synthesis completed
[INFO] Audio response sent
[INFO] Session ended gracefully
```

## 📁 Log File Locations

All logs are stored in:
```
logs/voice_assistant_YYYYMMDD_HHMMSS.log
```

Example:
```
logs/voice_assistant_20260308_060752.log
```

## 🎨 Colored Output

The log viewer shows:
- 🟢 **Green** for INFO
- 🟡 **Yellow** for WARNING
- 🔴 **Red** for ERROR
- 🔵 **Blue** for DEBUG

## 💡 Key Features Demonstrated

1. ✅ **Automatic log file creation** - New file per run
2. ✅ **Structured JSON format** - Easy to parse
3. ✅ **ISO 8601 timestamps** - Standard format
4. ✅ **Dual output** - Console + file
5. ✅ **Rich context** - session_id, component, etc.
6. ✅ **Bound loggers** - Persistent context
7. ✅ **Exception tracking** - Full tracebacks
8. ✅ **Easy filtering** - By level, session, component
9. ✅ **Production-ready** - Ready for log aggregation

## 🚀 Usage in Your Application

```python
from src.utils.logger import logger

# Basic logging
logger.info("Application started")

# With context
logger.info("Processing", session_id="123", component="asr")

# Bound logger
session_logger = logger.bind(session_id="123")
session_logger.info("Event 1")
session_logger.info("Event 2")

# Error with context
logger.error("Failed", error_code=500, retry_count=3)

# Exception
try:
    risky_operation()
except Exception:
    logger.exception("Operation failed", component="service")
```

## 📈 Production Benefits

1. **Debugging**: Trace issues with session_id
2. **Monitoring**: Track performance metrics
3. **Alerting**: Filter errors for alerts
4. **Analytics**: Parse JSON for insights
5. **Compliance**: Audit trail with timestamps
6. **Troubleshooting**: Full exception tracebacks

## ✅ Verification

All systems verified:
- ✅ 17 log files created
- ✅ 25 log entries in demo
- ✅ JSON format valid
- ✅ Timestamps in ISO 8601
- ✅ Filtering works
- ✅ Exception tracking works
- ✅ Session tracking works

## 🎯 Next Steps

1. **Run the demo**: `python test_logging_demo.py`
2. **View the logs**: `python view_logs.py latest`
3. **Filter logs**: `python view_logs.py latest --level error`
4. **Check log files**: Open `logs/` directory
5. **Use in your code**: Import from `src.utils.logger`

---

**Status**: ✅ Production-Ready and Fully Demonstrated!
