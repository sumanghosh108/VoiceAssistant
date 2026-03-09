# Event Pipeline Architecture

## Overview

The real-time voice assistant uses an **asyncio.Queue-based event pipeline** to process voice interactions. This document describes the architecture, design decisions, and verification results for task 14.1.

## Architecture Components

### 1. Event Pipeline Structure

```
WebSocket → audio_queue → ASR Service → transcript_queue → LLM Service 
  → token_queue → TTS Service → tts_queue → WebSocket
```

Each arrow represents an `asyncio.Queue` that connects pipeline stages.

### 2. Queue-Based Design

**Why asyncio.Queue?**

Python's `asyncio.Queue` provides all required event pipeline properties:

- **Non-blocking delivery**: Async `put()` and `get()` operations yield control to the event loop
- **FIFO ordering**: Events are retrieved in the exact order they were inserted
- **Session isolation**: Each session gets its own queue instances
- **Backpressure**: `maxsize` parameter limits queue growth and applies backpressure
- **Thread-safe**: Safe for concurrent access from multiple coroutines

### 3. Queue Sizing

Queue sizes are tuned for each pipeline stage:

| Queue | Size | Rationale |
|-------|------|-----------|
| `audio_queue` | 100 | ~6 seconds of audio at 1s buffer size, handles bursts |
| `transcript_queue` | 50 | Moderate buffering for ASR→LLM handoff |
| `token_queue` | 200 | Large buffer for high-throughput streaming tokens |
| `tts_queue` | 100 | Audio chunk buffering for smooth playback |

## Requirements Verification

### Requirement 6.1: Asynchronous Message Passing

**Requirement**: "THE Event_Pipeline SHALL use asynchronous message passing between all components"

**Implementation**: 
- All queue operations use `await queue.put()` and `await queue.get()`
- Services are implemented as async coroutines
- No blocking I/O operations in the pipeline

**Verification**: Test suite confirms async operations complete without blocking the event loop.

### Requirement 6.2: Concurrent Session Processing

**Requirement**: "THE Event_Pipeline SHALL support concurrent processing of multiple Sessions"

**Implementation**:
- Each session gets its own set of queue instances
- SessionManager maintains a dictionary of active sessions
- Multiple sessions can be processed simultaneously on a single thread

**Verification**: Tests confirm multiple sessions can run concurrently with isolated queues.

### Requirement 6.3: Non-Blocking Event Delivery

**Requirement**: "WHEN a component emits an event, THE Event_Pipeline SHALL deliver it to subscribed components without blocking the emitter"

**Implementation**:
- `await queue.put()` suspends the coroutine but doesn't block the event loop
- Other coroutines continue executing while one is suspended
- When queue has space, put() completes immediately

**Verification**: Tests confirm producers can emit events while consumers process at different rates.

### Requirement 6.4: Event Ordering Within Sessions

**Requirement**: "THE Event_Pipeline SHALL maintain event ordering within each Session"

**Implementation**:
- `asyncio.Queue` guarantees FIFO ordering
- Events are retrieved in insertion order
- Sequence numbers in events provide additional verification

**Verification**: Tests confirm events maintain order through all pipeline stages.

### Requirement 6.5: Session Failure Isolation

**Requirement**: "THE Event_Pipeline SHALL isolate failures in one Session from affecting other Sessions"

**Implementation**:
- Each session has separate queue instances
- Exceptions in one session's tasks don't propagate to other sessions
- Session cleanup only affects that session's resources

**Verification**: Tests confirm exceptions in one session don't affect others.

### Requirement 6.6: Backpressure Mechanisms

**Requirement**: "THE Event_Pipeline SHALL provide backpressure mechanisms when consumers cannot keep pace"

**Implementation**:
- Queue `maxsize` parameter enforces backpressure
- When queue is full, `put()` blocks until space is available
- Prevents unbounded memory growth

**Verification**: Tests confirm producers block when queues are full.

### Requirement 6.7: Event Logging

**Requirement**: "THE Event_Pipeline SHALL log all events with Session identifiers and timestamps"

**Implementation**:
- All event types include `session_id` field
- All event types include `timestamp` field
- StructuredLogger logs events with session context

**Verification**: Tests confirm all event types have required fields.

## Test Results

All 15 tests in `tests/test_event_pipeline.py` pass:

### Non-Blocking Delivery (3 tests)
✅ Queue put operations don't block when space available  
✅ Producers can buffer events ahead of slow consumers  
✅ Async operations yield control to event loop  

### Session Isolation (3 tests)
✅ Each session has separate queue instances  
✅ Events in one session don't appear in another  
✅ Exceptions in one session don't affect others  

### FIFO Ordering (4 tests)
✅ Queue maintains insertion order  
✅ Ordering preserved with timestamps  
✅ Ordering maintained under concurrent access  
✅ Ordering preserved through pipeline stages  

### Backpressure (2 tests)
✅ Queue blocks when full  
✅ Maxsize enforces backpressure on producers  

### Event Logging (2 tests)
✅ All events have session_id field  
✅ All events have timestamp field  

### Integration (1 test)
✅ End-to-end event flow through complete pipeline  

## Code Documentation

Comprehensive documentation has been added to:

1. **`src/session.py` module docstring**: Explains event pipeline architecture, non-blocking delivery, session isolation, FIFO ordering, backpressure, and event logging.

2. **`Session` dataclass docstring**: Documents the four event queues, their purpose, and the processing tasks.

3. **Queue creation code comments**: Inline documentation explaining queue sizing rationale and requirements mapping.

## Conclusion

The asyncio.Queue-based event pipeline successfully meets all requirements:

- ✅ **6.1**: Asynchronous message passing
- ✅ **6.2**: Concurrent session processing  
- ✅ **6.3**: Non-blocking event delivery
- ✅ **6.4**: Event ordering within sessions
- ✅ **6.5**: Session failure isolation
- ✅ **6.6**: Backpressure mechanisms
- ✅ **6.7**: Event logging with session IDs and timestamps

The implementation is verified by a comprehensive test suite with 15 passing tests covering all aspects of the event pipeline architecture.
