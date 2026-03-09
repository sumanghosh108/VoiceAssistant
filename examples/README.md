# Example Client Applications

This directory contains example client applications demonstrating how to integrate with the real-time voice assistant server.

## Voice Client (Python)

The `voice_client.py` script is a complete example of a voice assistant client that:

- Captures audio from your microphone
- Streams audio to the server via WebSocket
- Receives synthesized audio responses
- Plays audio through your speakers
- Handles errors and reconnections automatically

### Requirements

Install the required dependencies:

```bash
pip install pyaudio websockets
```

**Note**: On some systems, you may need to install PortAudio first:

- **macOS**: `brew install portaudio`
- **Ubuntu/Debian**: `sudo apt-get install portaudio19-dev`
- **Windows**: PyAudio wheels are available on PyPI

### Usage

#### Basic Usage

Connect to a local server:

```bash
python examples/voice_client.py --server ws://localhost:8000
```

Connect to a remote server:

```bash
python examples/voice_client.py --server ws://your-server.com:8000
```

#### Advanced Options

```bash
# Custom audio settings
python examples/voice_client.py \
    --server ws://localhost:8000 \
    --sample-rate 16000 \
    --channels 1 \
    --chunk-size 1024

# Custom reconnection settings
python examples/voice_client.py \
    --server ws://localhost:8000 \
    --reconnect-delay 2.0 \
    --max-reconnect-attempts 5

# Enable verbose logging
python examples/voice_client.py \
    --server ws://localhost:8000 \
    --verbose
```

#### List Audio Devices

To see available audio input and output devices:

```bash
python examples/voice_client.py --list-devices
```

### Command-Line Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--server` | `ws://localhost:8000` | WebSocket server URL |
| `--sample-rate` | `16000` | Audio sample rate in Hz |
| `--channels` | `1` | Number of audio channels (1=mono, 2=stereo) |
| `--chunk-size` | `1024` | Audio chunk size in frames |
| `--reconnect-delay` | `2.0` | Delay between reconnection attempts (seconds) |
| `--max-reconnect-attempts` | `5` | Maximum number of reconnection attempts |
| `--list-devices` | - | List available audio devices and exit |
| `--verbose` | - | Enable verbose logging |

### Features

#### Audio Capture

The client captures audio from your default microphone using PyAudio:

- **Sample Rate**: 16kHz (configurable)
- **Format**: 16-bit PCM
- **Channels**: Mono (configurable)
- **Chunk Size**: 1024 frames (configurable)

#### WebSocket Communication

The client implements the server's WebSocket protocol:

**Outgoing Audio Frame Format** (Client → Server):
```
[8 bytes: timestamp (double, seconds since epoch)]
[4 bytes: sequence_number (unsigned int)]
[N bytes: audio data (PCM 16-bit)]
```

**Incoming Audio Packet Format** (Server → Client):
```
[4 bytes: sequence_number (unsigned int)]
[1 byte: is_final flag (0 or 1)]
[N bytes: audio data (PCM 16-bit)]
```

#### Error Handling

The client includes comprehensive error handling:

- **Connection Errors**: Automatic reconnection with exponential backoff
- **Audio Errors**: Graceful handling of microphone/speaker issues
- **Network Errors**: Detection and recovery from connection loss
- **Parsing Errors**: Validation of incoming packets

#### Reconnection Logic

When the connection is lost, the client:

1. Detects the disconnection
2. Waits for the configured delay (default: 2 seconds)
3. Attempts to reconnect
4. Uses exponential backoff for subsequent attempts
5. Gives up after max attempts (default: 5)

### Integration Pattern

The client demonstrates the recommended integration pattern:

1. **Initialize Audio**: Set up PyAudio input and output streams
2. **Connect**: Establish WebSocket connection to server
3. **Concurrent Loops**: Run send and receive loops concurrently
   - **Send Loop**: Capture audio → Format message → Send to server
   - **Receive Loop**: Receive packet → Parse → Play audio
4. **Error Handling**: Detect errors and reconnect as needed
5. **Cleanup**: Stop streams and close connection on exit

### Code Structure

```python
class VoiceClient:
    """Main client class"""
    
    async def connect(self) -> bool:
        """Connect to WebSocket server"""
        
    async def reconnect(self) -> bool:
        """Reconnect with exponential backoff"""
        
    def start_audio_streams(self):
        """Start microphone and speaker streams"""
        
    def create_audio_frame_message(self, audio_data: bytes) -> bytes:
        """Format audio for server"""
        
    def parse_audio_packet(self, packet: bytes) -> tuple:
        """Parse server audio packet"""
        
    async def send_audio_loop(self):
        """Capture and send audio continuously"""
        
    async def receive_audio_loop(self):
        """Receive and play audio continuously"""
        
    async def run(self):
        """Main client loop"""
```

### Troubleshooting

#### No Audio Input

**Problem**: Client starts but doesn't capture audio

**Solutions**:
1. Check microphone permissions
2. List devices with `--list-devices` and verify default input
3. Try a different sample rate (e.g., `--sample-rate 44100`)
4. Check microphone is not in use by another application

#### No Audio Output

**Problem**: Client receives data but no sound plays

**Solutions**:
1. Check speaker/headphone connection
2. Verify system volume is not muted
3. List devices with `--list-devices` and verify default output
4. Try a different chunk size (e.g., `--chunk-size 2048`)

#### Connection Refused

**Problem**: Cannot connect to server

**Solutions**:
1. Verify server is running: `curl http://localhost:8000/health`
2. Check server URL is correct
3. Verify firewall allows connection
4. Check server logs for errors

#### Frequent Disconnections

**Problem**: Client keeps disconnecting and reconnecting

**Solutions**:
1. Check network stability
2. Increase reconnection delay: `--reconnect-delay 5.0`
3. Check server logs for errors
4. Monitor server resource usage

#### Audio Glitches

**Problem**: Audio playback has gaps or stutters

**Solutions**:
1. Increase chunk size: `--chunk-size 2048`
2. Check CPU usage (both client and server)
3. Check network latency
4. Reduce other system load

### Example Session

```bash
$ python examples/voice_client.py --server ws://localhost:8000 --verbose

2024-01-15 10:30:00 - __main__ - INFO - Connecting to ws://localhost:8000...
2024-01-15 10:30:00 - __main__ - INFO - Connected to server successfully
2024-01-15 10:30:00 - __main__ - INFO - Audio input started: 16000Hz, 1 channel(s)
2024-01-15 10:30:00 - __main__ - INFO - Audio output started: 16000Hz, 1 channel(s)
2024-01-15 10:30:00 - __main__ - INFO - Voice client running. Press Ctrl+C to stop.
2024-01-15 10:30:00 - __main__ - INFO - Starting audio send loop...
2024-01-15 10:30:00 - __main__ - INFO - Starting audio receive loop...
2024-01-15 10:30:05 - __main__ - DEBUG - Sent frame 100
2024-01-15 10:30:08 - __main__ - DEBUG - Received packet 50, is_final=False
2024-01-15 10:30:10 - __main__ - INFO - Received final audio packet for response
^C
2024-01-15 10:30:15 - __main__ - INFO - Interrupted by user
2024-01-15 10:30:15 - __main__ - INFO - Stopping voice client...
2024-01-15 10:30:15 - __main__ - INFO - Disconnected from server
2024-01-15 10:30:15 - __main__ - INFO - Audio input stopped
2024-01-15 10:30:15 - __main__ - INFO - Audio output stopped
2024-01-15 10:30:15 - __main__ - INFO - Audio system terminated
2024-01-15 10:30:15 - __main__ - INFO - Voice client stopped
```

## Metrics Dashboard Example

The `metrics_dashboard_example.py` script demonstrates how to query and display metrics from the server's metrics endpoint.

See the script for usage details.

## Logging Example

The `logging_example.py` script demonstrates the production logging system:

```bash
python examples/logging_example.py
```

Features demonstrated:
- Basic logging at different levels
- Contextual fields (session_id, component, user_id)
- Bound loggers with persistent context
- Exception logging with tracebacks
- Async logging
- Service logging patterns

See [docs/logging_system.md](../docs/logging_system.md) for complete logging documentation.

## Creating Your Own Client

To create your own client in any language:

1. **Establish WebSocket Connection**: Connect to `ws://server:8000`

2. **Send Audio Frames**: Format messages as:
   ```
   [8 bytes: timestamp (double, big-endian)]
   [4 bytes: sequence_number (uint32, big-endian)]
   [N bytes: PCM audio data (16-bit, 16kHz, mono)]
   ```

3. **Receive Audio Packets**: Parse messages as:
   ```
   [4 bytes: sequence_number (uint32, big-endian)]
   [1 byte: is_final flag (0 or 1)]
   [N bytes: PCM audio data (16-bit, 16kHz, mono)]
   ```

4. **Handle Errors**: Implement reconnection logic for network failures

5. **Manage Audio**: Capture from microphone and play to speakers

See `voice_client.py` for a complete reference implementation.

## Related Documentation

- [WebSocket Server Documentation](../docs/websocket_server.md) - Protocol details
- [Running the Application](../docs/running_the_application.md) - Server setup
- [API Documentation](../README.md#api-documentation) - Complete API reference

