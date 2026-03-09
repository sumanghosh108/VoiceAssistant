# API Documentation

## Overview

This document provides comprehensive API reference documentation for the Real-Time Voice Assistant system. The system exposes two primary interfaces:

1. **WebSocket API** - Bidirectional streaming audio interface for real-time voice interaction
2. **HTTP API** - Health check, metrics, and monitoring endpoints

## Table of Contents

- [WebSocket Protocol](#websocket-protocol)
- [Event Schemas](#event-schemas)
- [HTTP Endpoints](#http-endpoints)
- [Error Handling](#error-handling)
- [Examples](#examples)

---

## WebSocket Protocol

### Connection

**Endpoint:** `ws://<host>:<port>/`

**Default Port:** 8000

**Protocol:** WebSocket (RFC 6455)

### Connection Lifecycle

1. **Connect** - Client establishes WebSocket connection
2. **Stream Audio** - Client sends audio frames, receives synthesized audio
3. **Disconnect** - Client closes connection, server cleans up session

### Message Format

All WebSocket messages are **binary** (not text/JSON).

#### Client → Server: Audio Frame

Binary format for sending audio data to the server:

```
┌─────────────────────────────────────────────────────────────┐
│ Timestamp (8 bytes, double, network byte order)             │
├─────────────────────────────────────────────────────────────┤
│ Sequence Number (4 bytes, unsigned int, network byte order) │
├─────────────────────────────────────────────────────────────┤
│ Audio Data (variable length, PCM 16-bit, 16kHz mono)        │
└─────────────────────────────────────────────────────────────┘
```

**Field Descriptions:**

- **Timestamp** (8 bytes): Unix timestamp in seconds (double precision float)
  - Format: IEEE 754 double, network byte order (big-endian)
  - Example: `1704067200.123456` (seconds since epoch)
  

- **Sequence Number** (4 bytes): Monotonically increasing frame counter
  - Format: Unsigned 32-bit integer, network byte order (big-endian)
  - Used for ordering and detecting dropped frames
  - Example: `0, 1, 2, 3, ...`

- **Audio Data** (variable): Raw PCM audio samples
  - Format: PCM 16-bit signed integers, little-endian
  - Sample Rate: 16,000 Hz (16 kHz)
  - Channels: 1 (mono)
  - Typical chunk size: 1-2 seconds of audio (32,000-64,000 bytes)

**Python Example:**

```python
import struct
import time

# Prepare audio frame
timestamp = time.time()
sequence_number = 0
audio_data = b'\x00\x01\x02\x03...'  # PCM audio bytes

# Pack into binary format
message = struct.pack('!dI', timestamp, sequence_number) + audio_data

# Send via WebSocket
await websocket.send(message)
```

**JavaScript Example:**

```javascript
// Prepare audio frame
const timestamp = Date.now() / 1000;  // Convert to seconds
const sequenceNumber = 0;
const audioData = new Uint8Array([...]); // PCM audio bytes

// Pack into binary format
const buffer = new ArrayBuffer(12 + audioData.length);
const view = new DataView(buffer);
view.setFloat64(0, timestamp, false);  // Big-endian
view.setUint32(8, sequenceNumber, false);  // Big-endian

// Copy audio data
const uint8View = new Uint8Array(buffer);
uint8View.set(audioData, 12);

// Send via WebSocket
websocket.send(buffer);
```


#### Server → Client: Audio Packet

Binary format for receiving synthesized audio from the server:

```
┌─────────────────────────────────────────────────────────────┐
│ Sequence Number (4 bytes, unsigned int, network byte order) │
├─────────────────────────────────────────────────────────────┤
│ Is Final Flag (1 byte, 0 or 1)                              │
├─────────────────────────────────────────────────────────────┤
│ Audio Data (variable length, PCM 16-bit, 16kHz mono)        │
└─────────────────────────────────────────────────────────────┘
```

**Field Descriptions:**

- **Sequence Number** (4 bytes): Packet sequence for ordering
  - Format: Unsigned 32-bit integer, network byte order (big-endian)
  - Ensures correct playback order
  - Example: `0, 1, 2, 3, ...`

- **Is Final Flag** (1 byte): Indicates last packet of response
  - Format: Single byte, 0 = not final, 1 = final
  - Used to detect end of response for UI updates
  - Example: `0` for intermediate packets, `1` for last packet

- **Audio Data** (variable): Synthesized PCM audio samples
  - Format: PCM 16-bit signed integers, little-endian
  - Sample Rate: 16,000 Hz (16 kHz)
  - Channels: 1 (mono)
  - Typical chunk size: 100-500ms of audio

**Python Example:**

```python
import struct

# Receive from WebSocket
message = await websocket.recv()

# Unpack binary format
sequence_number, is_final = struct.unpack('!IB', message[:5])
audio_data = message[5:]

print(f"Received packet {sequence_number}, final={is_final}")
# Play audio_data...
```


**JavaScript Example:**

```javascript
// Receive from WebSocket
websocket.onmessage = (event) => {
  const buffer = event.data;
  const view = new DataView(buffer);
  
  // Unpack binary format
  const sequenceNumber = view.getUint32(0, false);  // Big-endian
  const isFinal = view.getUint8(4);
  const audioData = new Uint8Array(buffer, 5);
  
  console.log(`Received packet ${sequenceNumber}, final=${isFinal}`);
  // Play audioData...
};
```

### Connection Management

#### Backpressure Handling

If the client cannot consume audio fast enough:
- Server will drop frames and log warnings
- Client should implement buffering to handle bursts
- Monitor for gaps in sequence numbers

#### Error Handling

Network errors result in connection closure:
- Server logs error and closes WebSocket
- Client should implement reconnection logic with exponential backoff
- Session state is not preserved across reconnections

#### Session Cleanup

When client disconnects:
- Server cleans up session resources within 5 seconds
- All queued events are discarded
- Conversation context is lost

---

## Event Schemas

The system uses strongly-typed events internally. While these are not directly exposed via the WebSocket protocol, understanding them helps with integration and debugging.

### AudioFrame

Represents raw audio input from the client.

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `session_id` | string | Unique session identifier (UUID) |
| `data` | bytes | Raw PCM audio data (16-bit, 16kHz mono) |
| `timestamp` | datetime | When audio was captured |
| `sequence_number` | int | Frame sequence number for ordering |
| `sample_rate` | int | Audio sample rate in Hz (default: 16000) |
| `channels` | int | Number of audio channels (default: 1) |


### TranscriptEvent

Speech recognition result from ASR service.

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `session_id` | string | Unique session identifier |
| `text` | string | Transcribed text from audio |
| `partial` | bool | `true` for interim results, `false` for final |
| `confidence` | float | Confidence score (0.0 to 1.0) |
| `timestamp` | datetime | When transcription completed |
| `audio_duration_ms` | int | Duration of transcribed audio in milliseconds |

**Example:**

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "text": "Hello, how are you?",
  "partial": false,
  "confidence": 0.95,
  "timestamp": "2024-01-01T12:00:00.123Z",
  "audio_duration_ms": 1500
}
```

### LLMTokenEvent

Streaming token from language model.

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `session_id` | string | Unique session identifier |
| `token` | string | Single token from LLM response |
| `is_first` | bool | `true` for first token (latency tracking) |
| `is_last` | bool | `true` for final token |
| `timestamp` | datetime | When token was generated |
| `token_index` | int | Position in response sequence (0-based) |

**Example:**

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "token": "Hello",
  "is_first": true,
  "is_last": false,
  "timestamp": "2024-01-01T12:00:00.456Z",
  "token_index": 0
}
```


### TTSAudioEvent

Synthesized audio chunk from TTS service.

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `session_id` | string | Unique session identifier |
| `audio_data` | bytes | PCM audio data (16-bit, 16kHz mono) |
| `timestamp` | datetime | When audio was synthesized |
| `sequence_number` | int | Packet sequence for ordering |
| `is_final` | bool | `true` for last chunk of response |

### ErrorEvent

Error notification from any component.

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `session_id` | string | Unique session identifier |
| `component` | string | Component that encountered error (`asr`, `llm`, `tts`, `websocket`) |
| `error_type` | ErrorType | Error classification (see below) |
| `message` | string | Human-readable error description |
| `timestamp` | datetime | When error occurred |
| `retryable` | bool | Whether operation should be retried |

**ErrorType Enum:**

| Value | Description |
|-------|-------------|
| `timeout` | Operation exceeded timeout threshold |
| `api_error` | External API returned error |
| `network_error` | Network connectivity issue |
| `validation_error` | Invalid input data |

**Example:**

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "component": "asr",
  "error_type": "timeout",
  "message": "Whisper API call timed out after 3.0s",
  "timestamp": "2024-01-01T12:00:03.000Z",
  "retryable": true
}
```

---


## HTTP Endpoints

All HTTP endpoints are served on the metrics port (default: 8001).

### GET /health

Detailed health status endpoint.

**Purpose:** Comprehensive health check including all components and circuit breaker states.

**Response Codes:**
- `200 OK` - System is fully healthy
- `503 Service Unavailable` - System is degraded

**Response Format:** JSON

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `healthy` | bool | `true` if all components are healthy |
| `critical_healthy` | bool | `true` if critical components (ASR, LLM, TTS) are healthy |
| `components` | object | Health status of each component |
| `degraded_since` | object | ISO timestamps when components became degraded |
| `circuit_breakers` | object | State of each circuit breaker |

**Example Request:**

```bash
curl http://localhost:8001/health
```

**Example Response (Healthy):**

```json
{
  "healthy": true,
  "critical_healthy": true,
  "components": {
    "asr": true,
    "llm": true,
    "tts": true,
    "latency_tracker": true,
    "recorder": true,
    "dashboard": true
  },
  "degraded_since": {},
  "circuit_breakers": {
    "asr": {
      "name": "asr",
      "state": "closed",
      "failures": 0,
      "successes": 42,
      "last_failure": null,
      "state_changed_at": "2024-01-01T12:00:00.000Z"
    },
    "llm": {
      "name": "llm",
      "state": "closed",
      "failures": 0,
      "successes": 38,
      "last_failure": null,
      "state_changed_at": "2024-01-01T12:00:00.000Z"
    },
    "tts": {
      "name": "tts",
      "state": "closed",
      "failures": 0,
      "successes": 40,
      "last_failure": null,
      "state_changed_at": "2024-01-01T12:00:00.000Z"
    }
  }
}
```


**Example Response (Degraded):**

```json
{
  "healthy": false,
  "critical_healthy": false,
  "components": {
    "asr": false,
    "llm": true,
    "tts": true,
    "latency_tracker": true,
    "recorder": true,
    "dashboard": true
  },
  "degraded_since": {
    "asr": "2024-01-01T12:05:30.123Z"
  },
  "circuit_breakers": {
    "asr": {
      "name": "asr",
      "state": "open",
      "failures": 6,
      "successes": 4,
      "last_failure": "2024-01-01T12:05:30.100Z",
      "state_changed_at": "2024-01-01T12:05:30.123Z"
    },
    "llm": {
      "name": "llm",
      "state": "closed",
      "failures": 0,
      "successes": 38,
      "last_failure": null,
      "state_changed_at": "2024-01-01T12:00:00.000Z"
    },
    "tts": {
      "name": "tts",
      "state": "closed",
      "failures": 0,
      "successes": 40,
      "last_failure": null,
      "state_changed_at": "2024-01-01T12:00:00.000Z"
    }
  }
}
```

**Circuit Breaker States:**

| State | Description |
|-------|-------------|
| `closed` | Normal operation, requests pass through |
| `open` | Failing, requests are rejected immediately |
| `half_open` | Testing recovery, one request allowed through |

---

### GET /health/ready

Readiness probe for orchestration platforms (Kubernetes, Docker Compose).

**Purpose:** Indicates whether the system is ready to accept new connections.

**Response Codes:**
- `200 OK` - Ready to accept connections
- `503 Service Unavailable` - Not ready (critical components down or circuit breakers open)

**Response Format:** JSON

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | `"ready"` or `"not_ready"` |


**Example Request:**

```bash
curl http://localhost:8001/health/ready
```

**Example Response (Ready):**

```json
{
  "status": "ready"
}
```

**Example Response (Not Ready):**

```json
{
  "status": "not_ready"
}
```

**Use Cases:**
- Kubernetes readiness probe
- Load balancer health check
- Deployment verification

---

### GET /health/live

Liveness probe for orchestration platforms.

**Purpose:** Simple check that the process is alive and responding.

**Response Codes:**
- `200 OK` - Process is alive

**Response Format:** JSON

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | Always `"alive"` |

**Example Request:**

```bash
curl http://localhost:8001/health/live
```

**Example Response:**

```json
{
  "status": "alive"
}
```

**Use Cases:**
- Kubernetes liveness probe
- Process monitoring
- Container health check

---


### GET /metrics

JSON metrics endpoint exposing latency statistics.

**Purpose:** Programmatic access to latency metrics for monitoring and alerting.

**Response Codes:**
- `200 OK` - Metrics available

**Response Format:** JSON

**Response Structure:**

The response is an object with keys for each pipeline stage. Each stage contains statistical metrics.

**Pipeline Stages:**

| Stage | Description |
|-------|-------------|
| `asr_latency` | Time from audio receipt to transcript emission |
| `llm_first_token_latency` | Time from transcript to first LLM token |
| `llm_generation_latency` | Time from first token to last token |
| `tts_latency` | Time from token receipt to audio emission |
| `end_to_end_latency` | Total time from audio input to audio output |
| `websocket_send_latency` | Network transmission time |

**Metrics Per Stage:**

| Field | Type | Description |
|-------|------|-------------|
| `count` | int | Number of measurements |
| `mean` | float | Average latency in milliseconds |
| `median` | float | Median latency (p50) in milliseconds |
| `p95` | float | 95th percentile latency in milliseconds |
| `p99` | float | 99th percentile latency in milliseconds |
| `min` | float | Minimum latency in milliseconds |
| `max` | float | Maximum latency in milliseconds |
| `violation_rate` | float | Percentage of measurements exceeding budget |

**Example Request:**

```bash
curl http://localhost:8001/metrics
```

**Example Response:**

```json
{
  "asr_latency": {
    "count": 150,
    "mean": 342.5,
    "median": 320.0,
    "p95": 480.0,
    "p99": 495.0,
    "min": 250.0,
    "max": 500.0,
    "violation_rate": 2.0
  },
  "llm_first_token_latency": {
    "count": 145,
    "mean": 245.8,
    "median": 230.0,
    "p95": 290.0,
    "p99": 298.0,
    "min": 180.0,
    "max": 300.0,
    "violation_rate": 0.7
  },
  "tts_latency": {
    "count": 148,
    "mean": 325.0,
    "median": 310.0,
    "p95": 390.0,
    "p99": 398.0,
    "min": 200.0,
    "max": 400.0,
    "violation_rate": 1.4
  },
  "end_to_end_latency": {
    "count": 142,
    "mean": 1850.0,
    "median": 1820.0,
    "p95": 1980.0,
    "p99": 1995.0,
    "min": 1500.0,
    "max": 2000.0,
    "violation_rate": 0.0
  }
}
```


**Latency Budgets (Default):**

| Stage | Budget (ms) |
|-------|-------------|
| ASR | 500 |
| LLM First Token | 300 |
| TTS | 400 |
| End-to-End | 2000 |

**Use Cases:**
- Prometheus scraping
- Custom monitoring dashboards
- Performance alerting
- SLA tracking

---

### GET /dashboard

HTML dashboard with auto-refreshing metrics display.

**Purpose:** Human-readable visualization of system performance.

**Response Codes:**
- `200 OK` - Dashboard HTML

**Response Format:** HTML

**Features:**
- Auto-refreshes every 5 seconds
- Color-coded violation rates (red if >10%, green otherwise)
- Displays mean, p95, p99 latencies for each stage
- Shows violation rate percentage

**Example Request:**

```bash
# Open in browser
open http://localhost:8001/dashboard

# Or with curl
curl http://localhost:8001/dashboard
```

**Screenshot Description:**

The dashboard displays a simple HTML page with:
- Title: "Real-Time Voice Assistant Metrics"
- Metric cards for each pipeline stage showing:
  - Stage name (e.g., "asr_latency")
  - Mean latency in milliseconds
  - P95 latency in milliseconds
  - P99 latency in milliseconds
  - Violation rate (color-coded)

**Use Cases:**
- Real-time performance monitoring
- Debugging latency issues
- Operator dashboards
- Demo and presentations

---


## Error Handling

### Client-Side Error Handling

Clients should implement robust error handling for production use:

#### Connection Errors

```python
import asyncio
import websockets

async def connect_with_retry(url, max_retries=5):
    """Connect to WebSocket with exponential backoff."""
    retry_delay = 1.0
    
    for attempt in range(max_retries):
        try:
            websocket = await websockets.connect(url)
            print(f"Connected on attempt {attempt + 1}")
            return websocket
        except Exception as e:
            print(f"Connection failed: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                raise
```

#### Message Validation

```python
import struct

def validate_audio_packet(message):
    """Validate received audio packet."""
    if len(message) < 5:
        raise ValueError("Packet too short")
    
    sequence_number, is_final = struct.unpack('!IB', message[:5])
    audio_data = message[5:]
    
    if len(audio_data) == 0:
        raise ValueError("Empty audio data")
    
    return sequence_number, is_final, audio_data
```

#### Sequence Gap Detection

```python
class SequenceTracker:
    """Track sequence numbers and detect gaps."""
    
    def __init__(self):
        self.last_sequence = -1
        self.gaps = []
    
    def check_sequence(self, sequence_number):
        """Check for gaps in sequence."""
        if self.last_sequence >= 0:
            expected = self.last_sequence + 1
            if sequence_number != expected:
                gap = (expected, sequence_number - 1)
                self.gaps.append(gap)
                print(f"Gap detected: {gap}")
        
        self.last_sequence = sequence_number
```


### Server-Side Error Behavior

#### Timeout Errors

When external API calls timeout:
- ASR: 3 second timeout → retry up to 3 times
- LLM: 5 second timeout → retry up to 3 times
- TTS: 3 second timeout → no retry, emit error

#### Circuit Breaker Behavior

When circuit breaker opens (>50% failure rate):
- Requests fail immediately without calling API
- Circuit remains open for 30 seconds
- After 30 seconds, transitions to half-open
- One test request allowed in half-open state
- Success → close circuit, failure → reopen for 30 seconds

#### Validation Errors

Invalid audio frames are rejected:
- Missing timestamp → log warning, drop frame
- Malformed binary data → log error, drop frame
- Invalid sequence → log warning, continue processing

---

## Examples

### Complete Python Client

```python
import asyncio
import struct
import time
import websockets

async def voice_assistant_client():
    """Complete example client for voice assistant."""
    uri = "ws://localhost:8000"
    
    async with websockets.connect(uri) as websocket:
        print("Connected to voice assistant")
        
        # Start receive task
        receive_task = asyncio.create_task(receive_audio(websocket))
        
        # Send audio frames
        sequence_number = 0
        for i in range(10):
            # Simulate audio capture
            audio_data = b'\x00\x01' * 8000  # 1 second of silence
            timestamp = time.time()
            
            # Pack and send
            message = struct.pack('!dI', timestamp, sequence_number) + audio_data
            await websocket.send(message)
            
            print(f"Sent frame {sequence_number}")
            sequence_number += 1
            
            await asyncio.sleep(1.0)  # Send every second
        
        # Wait for remaining audio
        await asyncio.sleep(5.0)
        receive_task.cancel()

async def receive_audio(websocket):
    """Receive and process audio from server."""
    sequence_tracker = SequenceTracker()
    
    try:
        async for message in websocket:
            # Unpack audio packet
            sequence_number, is_final = struct.unpack('!IB', message[:5])
            audio_data = message[5:]
            
            # Check sequence
            sequence_tracker.check_sequence(sequence_number)
            
            print(f"Received packet {sequence_number}, "
                  f"final={is_final}, bytes={len(audio_data)}")
            
            # Play audio_data here...
            
    except asyncio.CancelledError:
        pass

if __name__ == "__main__":
    asyncio.run(voice_assistant_client())
```


### JavaScript/Browser Client

```javascript
class VoiceAssistantClient {
  constructor(url) {
    this.url = url;
    this.websocket = null;
    this.sequenceNumber = 0;
    this.lastReceivedSequence = -1;
  }

  async connect() {
    return new Promise((resolve, reject) => {
      this.websocket = new WebSocket(this.url);
      this.websocket.binaryType = 'arraybuffer';
      
      this.websocket.onopen = () => {
        console.log('Connected to voice assistant');
        resolve();
      };
      
      this.websocket.onerror = (error) => {
        console.error('WebSocket error:', error);
        reject(error);
      };
      
      this.websocket.onmessage = (event) => {
        this.handleAudioPacket(event.data);
      };
      
      this.websocket.onclose = () => {
        console.log('Disconnected from voice assistant');
      };
    });
  }

  sendAudioFrame(audioData) {
    // Create binary message
    const timestamp = Date.now() / 1000;
    const buffer = new ArrayBuffer(12 + audioData.length);
    const view = new DataView(buffer);
    
    // Pack timestamp and sequence number
    view.setFloat64(0, timestamp, false);  // Big-endian
    view.setUint32(8, this.sequenceNumber, false);  // Big-endian
    
    // Copy audio data
    const uint8View = new Uint8Array(buffer);
    uint8View.set(new Uint8Array(audioData), 12);
    
    // Send
    this.websocket.send(buffer);
    console.log(`Sent frame ${this.sequenceNumber}`);
    this.sequenceNumber++;
  }

  handleAudioPacket(buffer) {
    const view = new DataView(buffer);
    
    // Unpack sequence number and final flag
    const sequenceNumber = view.getUint32(0, false);  // Big-endian
    const isFinal = view.getUint8(4);
    const audioData = new Uint8Array(buffer, 5);
    
    // Check for gaps
    if (this.lastReceivedSequence >= 0) {
      const expected = this.lastReceivedSequence + 1;
      if (sequenceNumber !== expected) {
        console.warn(`Gap detected: expected ${expected}, got ${sequenceNumber}`);
      }
    }
    this.lastReceivedSequence = sequenceNumber;
    
    console.log(`Received packet ${sequenceNumber}, final=${isFinal}, bytes=${audioData.length}`);
    
    // Play audio here...
    this.playAudio(audioData);
  }

  playAudio(audioData) {
    // Implement audio playback using Web Audio API
    // This is a placeholder
    console.log('Playing audio...');
  }

  disconnect() {
    if (this.websocket) {
      this.websocket.close();
    }
  }
}

// Usage
const client = new VoiceAssistantClient('ws://localhost:8000');
await client.connect();

// Send audio from microphone
navigator.mediaDevices.getUserMedia({ audio: true })
  .then(stream => {
    const audioContext = new AudioContext({ sampleRate: 16000 });
    const source = audioContext.createMediaStreamSource(stream);
    // Process and send audio...
  });
```


### Health Check Integration

#### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: voice-assistant
spec:
  replicas: 3
  selector:
    matchLabels:
      app: voice-assistant
  template:
    metadata:
      labels:
        app: voice-assistant
    spec:
      containers:
      - name: voice-assistant
        image: voice-assistant:latest
        ports:
        - containerPort: 8000
          name: websocket
        - containerPort: 8001
          name: metrics
        env:
        - name: WHISPER_API_KEY
          valueFrom:
            secretKeyRef:
              name: api-keys
              key: whisper
        - name: GEMINI_API_KEY
          valueFrom:
            secretKeyRef:
              name: api-keys
              key: gemini
        - name: ELEVENLABS_API_KEY
          valueFrom:
            secretKeyRef:
              name: api-keys
              key: elevenlabs
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8001
          initialDelaySeconds: 10
          periodSeconds: 30
          timeoutSeconds: 3
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8001
          initialDelaySeconds: 5
          periodSeconds: 10
          timeoutSeconds: 3
          failureThreshold: 3
```

#### Docker Compose Health Check

```yaml
version: '3.8'

services:
  voice-assistant:
    build: .
    ports:
      - "8000:8000"
      - "8001:8001"
    environment:
      - WHISPER_API_KEY=${WHISPER_API_KEY}
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - ELEVENLABS_API_KEY=${ELEVENLABS_API_KEY}
      - ELEVENLABS_VOICE_ID=${ELEVENLABS_VOICE_ID}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health/ready"]
      interval: 30s
      timeout: 3s
      retries: 3
      start_period: 10s
    restart: unless-stopped
```


#### Prometheus Metrics Scraping

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'voice-assistant'
    scrape_interval: 15s
    metrics_path: '/metrics'
    static_configs:
      - targets: ['localhost:8001']
```

**Example Prometheus Queries:**

```promql
# Average ASR latency
avg(voice_assistant_asr_latency_mean)

# P95 end-to-end latency
voice_assistant_end_to_end_latency_p95

# Violation rate alert
voice_assistant_asr_latency_violation_rate > 10
```

---

## Rate Limits and Quotas

The system does not impose rate limits at the application level. However, be aware of:

### External API Limits

- **Whisper API**: Check OpenAI rate limits for your tier
- **Gemini API**: Check Google Cloud quotas
- **ElevenLabs API**: Check character/request limits for your plan

### Resource Limits

- **Concurrent Sessions**: Limited by available memory and CPU
- **Queue Sizes**: 
  - Audio queue: 100 frames per session
  - Transcript queue: 50 events per session
  - Token queue: 200 events per session
  - TTS queue: 100 events per session
- **Session Cleanup**: 5 second timeout for cleanup operations

### Recommended Limits

For production deployment:
- **Max concurrent sessions**: 100 per instance (on 4 CPU, 8GB RAM)
- **Audio chunk size**: 1-2 seconds (16,000-32,000 samples)
- **Send frequency**: 1 frame per second minimum

---

## Security Considerations

### Authentication

The current implementation does not include authentication. For production:

1. **Add WebSocket authentication**:
   - Token-based authentication in connection headers
   - Session validation on each message
   - Rate limiting per authenticated user

2. **Secure HTTP endpoints**:
   - Add API key authentication for /metrics
   - Restrict /health endpoints to internal networks
   - Use HTTPS/TLS for all connections


### Network Security

**Recommendations:**

- Deploy behind reverse proxy (nginx, Traefik)
- Use TLS/SSL for WebSocket connections (wss://)
- Implement firewall rules to restrict access
- Use VPC/private networks for internal communication

**Example nginx configuration:**

```nginx
upstream voice_assistant {
    server localhost:8000;
}

server {
    listen 443 ssl;
    server_name voice.example.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://voice_assistant;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Data Privacy

**Audio Data:**
- Audio is processed in memory, not persisted by default
- Enable recording only for debugging (set `ENABLE_RECORDING=false` in production)
- Implement data retention policies if recording is enabled
- Ensure compliance with privacy regulations (GDPR, CCPA)

**API Keys:**
- Store API keys in environment variables or secrets management
- Never commit API keys to version control
- Rotate keys regularly
- Use separate keys for development and production

---

## Troubleshooting

### Common Issues

#### Connection Refused

**Symptom:** Cannot connect to WebSocket

**Solutions:**
1. Check server is running: `curl http://localhost:8001/health/live`
2. Verify port is correct (default: 8000)
3. Check firewall rules
4. Review server logs for startup errors

#### Audio Not Playing

**Symptom:** Connected but no audio received

**Solutions:**
1. Check sequence numbers for gaps
2. Verify audio format (PCM 16-bit, 16kHz mono)
3. Check client audio playback implementation
4. Review server logs for TTS errors
5. Check circuit breaker state: `curl http://localhost:8001/health`


#### High Latency

**Symptom:** Slow response times

**Solutions:**
1. Check metrics: `curl http://localhost:8001/metrics`
2. Identify bottleneck stage (ASR, LLM, TTS)
3. Review circuit breaker states
4. Check external API status
5. Monitor system resources (CPU, memory, network)

#### Circuit Breaker Open

**Symptom:** `/health/ready` returns 503

**Solutions:**
1. Check which circuit is open: `curl http://localhost:8001/health`
2. Review error logs for root cause
3. Verify API keys are valid
4. Check external API status pages
5. Wait 30 seconds for automatic recovery attempt
6. If persistent, investigate network connectivity

### Debug Mode

Enable debug logging for detailed troubleshooting:

```bash
export LOG_LEVEL=DEBUG
python -m src.main
```

Debug logs include:
- Every audio frame received/sent
- All event emissions
- Circuit breaker state transitions
- Detailed error stack traces

### Log Analysis

Logs are structured JSON for easy parsing:

```bash
# Filter by component
cat logs.json | jq 'select(.component == "asr")'

# Find errors
cat logs.json | jq 'select(.level == "ERROR")'

# Track session
cat logs.json | jq 'select(.session_id == "550e8400-e29b-41d4-a716-446655440000")'

# Latency analysis
cat logs.json | jq 'select(.message | contains("latency"))'
```

---

## API Versioning

**Current Version:** 1.0

The API is currently unversioned. Breaking changes will be communicated via:
- Major version bump in documentation
- Deprecation notices in release notes
- Migration guides for clients

**Stability Guarantees:**
- WebSocket binary protocol format is stable
- HTTP endpoint paths are stable
- Event schema fields will not be removed (only added)

---

## Support and Resources

### Additional Documentation

- [Architecture Overview](./event_pipeline_architecture.md)
- [WebSocket Server Implementation](./websocket_server.md)
- [Health System](./health_system.md)
- [Metrics Dashboard](./metrics_dashboard.md)
- [Running the Application](./running_the_application.md)

### Example Implementations

- [Python Client Example](../examples/voice_client.py)
- [Protocol Test Client](../examples/test_client_protocol.py)
- [Metrics Dashboard Example](../examples/metrics_dashboard_example.py)

### Getting Help

For issues and questions:
1. Check this documentation
2. Review example implementations
3. Check server logs with DEBUG level
4. Consult architecture documentation

---

**Document Version:** 1.0  
**Last Updated:** 2024-01-01  
**Requirements Validated:** 20.1, 20.2, 20.4
