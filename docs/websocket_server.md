# WebSocket Server

## Overview

The WebSocket server manages bidirectional streaming connections with clients for real-time voice interaction. It handles the complete lifecycle of WebSocket connections, including audio data reception, session management, and audio output streaming.

## Architecture

The WebSocket server operates with two concurrent tasks per connection:

1. **Receive Loop**: Receives audio data from the client and emits AudioFrame events to the session's audio queue
2. **Send Loop**: Consumes TTSAudioEvent objects from the session's TTS queue and sends audio data back to the client

```
Client                WebSocket Server              Session Pipeline
  |                          |                            |
  |--- Connect ------------->|                            |
  |                          |--- Create Session -------->|
  |                          |                            |
  |--- Audio Data ---------->|                            |
  |                          |--- AudioFrame ------------>|
  |                          |                            |
  |                          |<-- TTSAudioEvent ----------|
  |<-- Audio Data -----------|                            |
  |                          |                            |
  |--- Disconnect ---------->|                            |
  |                          |--- Cleanup Session ------->|
```

## Connection Lifecycle

### 1. Connection Establishment

When a client connects:
- WebSocket connection is accepted
- A new Session is created via SessionManager
- Two concurrent tasks are started:
  - `receive_audio_loop`: Handles incoming audio
  - `send_audio_loop`: Handles outgoing audio

### 2. Audio Reception

The receive loop:
- Receives binary messages from the WebSocket
- Parses messages into AudioFrame objects
- Validates timestamp metadata
- Emits AudioFrame to the session's audio queue
- Handles parsing errors gracefully

### 3. Audio Transmission

The send loop:
- Consumes TTSAudioEvent from the session's TTS queue
- Serializes events to binary format
- Sends audio packets to the client
- Includes sequence numbers for ordering
- Handles backpressure by dropping frames when necessary

### 4. Disconnection

When a client disconnects:
- Both receive and send tasks are cancelled
- Session cleanup is triggered via SessionManager
- Resources are released within 5 seconds

## Message Formats

### Incoming Audio Frame (Client → Server)

Binary format:
```
[8 bytes: timestamp (double, seconds since epoch)]
[4 bytes: sequence_number (unsigned int)]
[N bytes: audio data (PCM 16-bit, 16kHz mono)]
```

Example:
```python
import struct
from datetime import datetime

timestamp = datetime.now().timestamp()
sequence_number = 42
audio_data = b'\x00\x01' * 1000  # 2000 bytes of audio

message = struct.pack('!dI', timestamp, sequence_number) + audio_data
await websocket.send(message)
```

### Outgoing Audio Packet (Server → Client)

Binary format:
```
[4 bytes: sequence_number (unsigned int)]
[1 byte: is_final flag (0 or 1)]
[N bytes: audio data (PCM 16-bit, 16kHz mono)]
```

Example:
```python
import struct

# Receive packet
packet = await websocket.recv()

# Parse packet
sequence_number, is_final = struct.unpack('!IB', packet[:5])
audio_data = packet[5:]

print(f"Received packet {sequence_number}, is_final={is_final}")
print(f"Audio data: {len(audio_data)} bytes")
```

## Error Handling

### Validation Errors

The server validates incoming audio frames:
- **Zero timestamp**: Frames with timestamp=0 are rejected and logged
- **Short messages**: Messages shorter than 12 bytes are ignored
- **Non-binary messages**: Text messages are ignored
- **Parsing errors**: Malformed messages are logged as errors

### Network Errors

Network errors are handled gracefully:
- **Connection closed**: Logged and cleanup is triggered
- **Send timeout**: Frame is dropped with warning log (backpressure handling)
- **Network error during send**: Connection is closed immediately

### Backpressure Handling

When the client cannot consume audio fast enough:
- Send operations timeout after 1 second
- Frames are dropped with warning logs
- Connection continues (no disconnection)
- This prevents server-side queue buildup

## Usage Example

### Server Setup

```python
from src.websocket_server import WebSocketServer
from src.session import SessionManager
from src.asr_service import ASRService
from src.reasoning_service import ReasoningService
from src.tts_service import TTSService

# Initialize services
asr_service = ASRService(api_key="...", ...)
llm_service = ReasoningService(api_key="...", ...)
tts_service = TTSService(api_key="...", ...)

# Create session manager
session_manager = SessionManager(
    asr_service=asr_service,
    llm_service=llm_service,
    tts_service=tts_service,
    enable_recording=False
)

# Create WebSocket server
ws_server = WebSocketServer(session_manager)

# Start server
await ws_server.start(host="0.0.0.0", port=8000)
```

### Client Example (Python)

```python
import asyncio
import struct
from datetime import datetime
import websockets

async def client():
    uri = "ws://localhost:8000"
    
    async with websockets.connect(uri) as websocket:
        # Send audio frame
        timestamp = datetime.now().timestamp()
        sequence_number = 1
        audio_data = b'\x00\x01' * 1000  # 2000 bytes
        
        message = struct.pack('!dI', timestamp, sequence_number) + audio_data
        await websocket.send(message)
        
        # Receive audio packet
        packet = await websocket.recv()
        seq_num, is_final = struct.unpack('!IB', packet[:5])
        audio = packet[5:]
        
        print(f"Received {len(audio)} bytes, seq={seq_num}, final={is_final}")

asyncio.run(client())
```

### Client Example (JavaScript)

```javascript
const ws = new WebSocket('ws://localhost:8000');

ws.onopen = () => {
    // Send audio frame
    const timestamp = Date.now() / 1000;  // seconds since epoch
    const sequenceNumber = 1;
    const audioData = new Uint8Array(2000);  // 2000 bytes of audio
    
    const buffer = new ArrayBuffer(12 + audioData.length);
    const view = new DataView(buffer);
    
    view.setFloat64(0, timestamp, false);  // big-endian
    view.setUint32(8, sequenceNumber, false);  // big-endian
    
    const uint8View = new Uint8Array(buffer);
    uint8View.set(audioData, 12);
    
    ws.send(buffer);
};

ws.onmessage = (event) => {
    const reader = new FileReader();
    reader.onload = () => {
        const buffer = reader.result;
        const view = new DataView(buffer);
        
        const sequenceNumber = view.getUint32(0, false);  // big-endian
        const isFinal = view.getUint8(4);
        const audioData = new Uint8Array(buffer, 5);
        
        console.log(`Received ${audioData.length} bytes, seq=${sequenceNumber}, final=${isFinal}`);
    };
    reader.readAsArrayBuffer(event.data);
};
```

## Configuration

The WebSocket server is configured via the `ServerConfig` section:

```yaml
server:
  websocket_host: "0.0.0.0"  # Host to bind to
  websocket_port: 8000       # Port to listen on
```

Environment variables:
```bash
WEBSOCKET_HOST=0.0.0.0
WEBSOCKET_PORT=8000
```

## Monitoring and Observability

### Structured Logging

All WebSocket operations are logged with structured JSON:

```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "INFO",
  "component": "websocket",
  "session_id": "abc-123-def",
  "message": "WebSocket connection established",
  "remote_address": ["127.0.0.1", 12345]
}
```

### Key Log Events

- **Connection established**: When client connects
- **AudioFrame emitted**: When audio is received and queued
- **Audio packet sent**: When audio is sent to client
- **Connection closed**: When client disconnects
- **Validation errors**: When invalid frames are received
- **Network errors**: When send operations fail
- **Backpressure warnings**: When frames are dropped

### Metrics

The WebSocket server contributes to these metrics:
- **WebSocket send latency**: Time to send audio packet to client
- **Active sessions**: Number of concurrent connections
- **Frame drop rate**: Percentage of frames dropped due to backpressure

## Performance Characteristics

### Throughput

- **Audio reception**: Can handle 16kHz mono audio (32 KB/s per session)
- **Concurrent sessions**: Supports 100+ concurrent connections
- **Queue sizes**: 
  - Audio queue: 100 frames (~6 seconds at 1s buffers)
  - TTS queue: 100 audio chunks

### Latency

- **Audio frame processing**: <1ms to parse and queue
- **Audio packet sending**: <1ms to serialize and send
- **Network send timeout**: 1 second (triggers backpressure)

### Resource Usage

- **Memory per session**: ~1-2 MB (queues + buffers)
- **CPU per session**: Minimal (mostly I/O bound)
- **Network bandwidth**: ~32 KB/s per session (audio only)

## Troubleshooting

### Client Cannot Connect

**Symptom**: Connection refused or timeout

**Solutions**:
1. Check server is running: `netstat -an | grep 8000`
2. Check firewall rules allow port 8000
3. Verify host binding (use `0.0.0.0` for all interfaces)
4. Check logs for startup errors

### Audio Not Received

**Symptom**: Server receives messages but doesn't process them

**Solutions**:
1. Check message format matches specification
2. Verify timestamp is non-zero
3. Check logs for validation errors
4. Ensure messages are binary (not text)

### Audio Not Sent to Client

**Symptom**: Client doesn't receive audio packets

**Solutions**:
1. Check TTS service is running and producing audio
2. Verify TTS queue is not empty
3. Check logs for network errors
4. Monitor backpressure warnings (frames being dropped)

### High Frame Drop Rate

**Symptom**: Many "dropping frame" warnings in logs

**Solutions**:
1. Client may be too slow to consume audio
2. Increase client buffer size
3. Reduce audio quality/bitrate
4. Check client network connection
5. Monitor client CPU usage

## Requirements Mapping

This implementation satisfies the following requirements:

- **1.1**: WebSocket server accepts connections on configured port
- **1.2**: Establishes bidirectional streaming channel
- **1.3**: Parses audio data into AudioFrame objects
- **1.4**: Validates AudioFrame timestamp metadata
- **1.5**: Emits AudioFrame to event pipeline
- **1.6**: Maintains connection state per session
- **1.7**: Cleans up session resources within 5 seconds
- **5.1**: Serializes TTS audio data
- **5.2**: Sends audio to correct session client
- **5.3**: Maintains send order
- **5.4**: Handles backpressure
- **5.5**: Logs errors and closes on network failure
- **5.6**: Includes sequence numbers in packets

## Related Documentation

- [Session Management](session_management.md) - Session lifecycle and pipeline
- [Configuration](configuration.md) - Server configuration options
- [Event Schemas](../src/events.py) - AudioFrame and TTSAudioEvent definitions
