#!/usr/bin/env python3
"""
Example Voice Assistant Client

This client demonstrates how to integrate with the real-time voice assistant server.
It captures audio from the microphone, streams it to the server via WebSocket,
and plays back the synthesized audio responses.

Features:
- WebSocket connection with automatic reconnection
- Audio capture from microphone using pyaudio
- Audio streaming to server with proper message formatting
- Receiving and playing synthesized audio
- Comprehensive error handling
- Command-line configuration

Requirements:
- pyaudio: pip install pyaudio
- websockets: pip install websockets

Usage:
    python voice_client.py --server ws://localhost:8000
    python voice_client.py --server ws://localhost:8000 --sample-rate 16000 --chunk-size 1024
"""

import asyncio
import argparse
import struct
import sys
from datetime import datetime
from typing import Optional
import logging

try:
    import pyaudio
except ImportError:
    print("Error: pyaudio is not installed. Install it with: pip install pyaudio")
    sys.exit(1)

try:
    import websockets
    from websockets.exceptions import ConnectionClosed, WebSocketException
except ImportError:
    print("Error: websockets is not installed. Install it with: pip install websockets")
    sys.exit(1)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class VoiceClient:
    """
    Real-time voice assistant client.
    
    Handles audio capture, WebSocket communication, and audio playback.
    """
    
    def __init__(
        self,
        server_url: str,
        sample_rate: int = 16000,
        channels: int = 1,
        chunk_size: int = 1024,
        audio_format: int = pyaudio.paInt16,
        reconnect_delay: float = 2.0,
        max_reconnect_attempts: int = 5
    ):
        """
        Initialize the voice client.
        
        Args:
            server_url: WebSocket server URL (e.g., ws://localhost:8000)
            sample_rate: Audio sample rate in Hz (default: 16000)
            channels: Number of audio channels (default: 1 for mono)
            chunk_size: Audio chunk size in frames (default: 1024)
            audio_format: PyAudio format (default: paInt16 for 16-bit PCM)
            reconnect_delay: Delay between reconnection attempts in seconds
            max_reconnect_attempts: Maximum number of reconnection attempts
        """
        self.server_url = server_url
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.audio_format = audio_format
        self.reconnect_delay = reconnect_delay
        self.max_reconnect_attempts = max_reconnect_attempts
        
        # Audio components
        self.audio = pyaudio.PyAudio()
        self.input_stream: Optional[pyaudio.Stream] = None
        self.output_stream: Optional[pyaudio.Stream] = None
        
        # WebSocket connection
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.connected = False
        
        # Sequence tracking
        self.send_sequence = 0
        self.recv_sequence = 0
        
        # Control flags
        self.running = False
        self.reconnecting = False
        
    async def connect(self) -> bool:
        """
        Connect to the WebSocket server.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            logger.info(f"Connecting to {self.server_url}...")
            self.websocket = await websockets.connect(
                self.server_url,
                ping_interval=20,
                ping_timeout=10
            )
            self.connected = True
            self.send_sequence = 0
            self.recv_sequence = 0
            logger.info("Connected to server successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            self.connected = False
            return False
            
    async def disconnect(self):
        """Disconnect from the WebSocket server."""
        if self.websocket:
            try:
                await self.websocket.close()
                logger.info("Disconnected from server")
            except Exception as e:
                logger.error(f"Error during disconnect: {e}")
            finally:
                self.websocket = None
                self.connected = False
                
    async def reconnect(self) -> bool:
        """
        Attempt to reconnect to the server with exponential backoff.
        
        Returns:
            True if reconnection successful, False otherwise
        """
        if self.reconnecting:
            return False
            
        self.reconnecting = True
        attempt = 0
        
        while attempt < self.max_reconnect_attempts and self.running:
            attempt += 1
            delay = self.reconnect_delay * (2 ** (attempt - 1))  # Exponential backoff
            
            logger.info(f"Reconnection attempt {attempt}/{self.max_reconnect_attempts} in {delay}s...")
            await asyncio.sleep(delay)
            
            if await self.connect():
                self.reconnecting = False
                return True
                
        logger.error("Max reconnection attempts reached. Giving up.")
        self.reconnecting = False
        return False
        
    def start_audio_streams(self):
        """Start audio input and output streams."""
        try:
            # Input stream (microphone)
            self.input_stream = self.audio.open(
                format=self.audio_format,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size,
                stream_callback=None
            )
            logger.info(f"Audio input started: {self.sample_rate}Hz, {self.channels} channel(s)")
            
            # Output stream (speakers)
            self.output_stream = self.audio.open(
                format=self.audio_format,
                channels=self.channels,
                rate=self.sample_rate,
                output=True,
                frames_per_buffer=self.chunk_size
            )
            logger.info(f"Audio output started: {self.sample_rate}Hz, {self.channels} channel(s)")
            
        except Exception as e:
            logger.error(f"Failed to start audio streams: {e}")
            raise
            
    def stop_audio_streams(self):
        """Stop and close audio streams."""
        if self.input_stream:
            try:
                self.input_stream.stop_stream()
                self.input_stream.close()
                logger.info("Audio input stopped")
            except Exception as e:
                logger.error(f"Error stopping input stream: {e}")
            finally:
                self.input_stream = None
                
        if self.output_stream:
            try:
                self.output_stream.stop_stream()
                self.output_stream.close()
                logger.info("Audio output stopped")
            except Exception as e:
                logger.error(f"Error stopping output stream: {e}")
            finally:
                self.output_stream = None
                
    def create_audio_frame_message(self, audio_data: bytes) -> bytes:
        """
        Create a properly formatted audio frame message for the server.
        
        Message format:
        [8 bytes: timestamp (double, seconds since epoch)]
        [4 bytes: sequence_number (unsigned int)]
        [N bytes: audio data (PCM 16-bit)]
        
        Args:
            audio_data: Raw PCM audio data
            
        Returns:
            Formatted message bytes
        """
        timestamp = datetime.now().timestamp()
        self.send_sequence += 1
        
        # Pack timestamp and sequence number (big-endian)
        header = struct.pack('!dI', timestamp, self.send_sequence)
        
        return header + audio_data
        
    def parse_audio_packet(self, packet: bytes) -> tuple[int, bool, bytes]:
        """
        Parse an audio packet from the server.
        
        Packet format:
        [4 bytes: sequence_number (unsigned int)]
        [1 byte: is_final flag (0 or 1)]
        [N bytes: audio data (PCM 16-bit)]
        
        Args:
            packet: Raw packet bytes
            
        Returns:
            Tuple of (sequence_number, is_final, audio_data)
        """
        if len(packet) < 5:
            raise ValueError(f"Packet too short: {len(packet)} bytes")
            
        # Unpack header (big-endian)
        sequence_number, is_final_byte = struct.unpack('!IB', packet[:5])
        is_final = bool(is_final_byte)
        audio_data = packet[5:]
        
        return sequence_number, is_final, audio_data
        
    async def send_audio_loop(self):
        """
        Continuously capture audio from microphone and send to server.
        
        This loop runs until the client is stopped or connection is lost.
        """
        logger.info("Starting audio send loop...")
        
        while self.running:
            try:
                if not self.connected or not self.websocket:
                    await asyncio.sleep(0.1)
                    continue
                    
                # Read audio from microphone (non-blocking with timeout)
                try:
                    audio_data = self.input_stream.read(
                        self.chunk_size,
                        exception_on_overflow=False
                    )
                except Exception as e:
                    logger.warning(f"Error reading audio: {e}")
                    await asyncio.sleep(0.01)
                    continue
                    
                # Create and send message
                message = self.create_audio_frame_message(audio_data)
                
                try:
                    await self.websocket.send(message)
                    
                    # Log periodically (every 100 frames)
                    if self.send_sequence % 100 == 0:
                        logger.debug(f"Sent frame {self.send_sequence}")
                        
                except ConnectionClosed:
                    logger.warning("Connection closed while sending audio")
                    self.connected = False
                    if self.running:
                        await self.reconnect()
                        
                except Exception as e:
                    logger.error(f"Error sending audio: {e}")
                    await asyncio.sleep(0.1)
                    
            except Exception as e:
                logger.error(f"Unexpected error in send loop: {e}")
                await asyncio.sleep(0.1)
                
        logger.info("Audio send loop stopped")
        
    async def receive_audio_loop(self):
        """
        Continuously receive audio from server and play through speakers.
        
        This loop runs until the client is stopped or connection is lost.
        """
        logger.info("Starting audio receive loop...")
        
        while self.running:
            try:
                if not self.connected or not self.websocket:
                    await asyncio.sleep(0.1)
                    continue
                    
                # Receive packet from server
                try:
                    packet = await asyncio.wait_for(
                        self.websocket.recv(),
                        timeout=1.0
                    )
                    
                except asyncio.TimeoutError:
                    # No data received, continue
                    continue
                    
                except ConnectionClosed:
                    logger.warning("Connection closed while receiving audio")
                    self.connected = False
                    if self.running:
                        await self.reconnect()
                    continue
                    
                # Parse packet
                try:
                    sequence_number, is_final, audio_data = self.parse_audio_packet(packet)
                    
                    # Check sequence order
                    if sequence_number != self.recv_sequence + 1:
                        logger.warning(
                            f"Out of order packet: expected {self.recv_sequence + 1}, "
                            f"got {sequence_number}"
                        )
                    self.recv_sequence = sequence_number
                    
                    # Play audio
                    if audio_data and self.output_stream:
                        self.output_stream.write(audio_data)
                        
                    # Log periodically
                    if sequence_number % 50 == 0:
                        logger.debug(f"Received packet {sequence_number}, is_final={is_final}")
                        
                    if is_final:
                        logger.info("Received final audio packet for response")
                        
                except ValueError as e:
                    logger.error(f"Error parsing packet: {e}")
                    
            except Exception as e:
                logger.error(f"Unexpected error in receive loop: {e}")
                await asyncio.sleep(0.1)
                
        logger.info("Audio receive loop stopped")
        
    async def run(self):
        """
        Run the voice client.
        
        This starts the audio streams, connects to the server, and runs
        the send and receive loops concurrently.
        """
        self.running = True
        
        try:
            # Start audio streams
            self.start_audio_streams()
            
            # Connect to server
            if not await self.connect():
                logger.error("Failed to connect to server")
                return
                
            logger.info("Voice client running. Press Ctrl+C to stop.")
            
            # Run send and receive loops concurrently
            send_task = asyncio.create_task(self.send_audio_loop())
            receive_task = asyncio.create_task(self.receive_audio_loop())
            
            # Wait for both tasks (or until interrupted)
            await asyncio.gather(send_task, receive_task, return_exceptions=True)
            
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
            
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            
        finally:
            await self.stop()
            
    async def stop(self):
        """Stop the voice client and clean up resources."""
        logger.info("Stopping voice client...")
        self.running = False
        
        # Disconnect from server
        await self.disconnect()
        
        # Stop audio streams
        self.stop_audio_streams()
        
        # Terminate PyAudio
        try:
            self.audio.terminate()
            logger.info("Audio system terminated")
        except Exception as e:
            logger.error(f"Error terminating audio: {e}")
            
        logger.info("Voice client stopped")


def list_audio_devices():
    """List available audio input and output devices."""
    audio = pyaudio.PyAudio()
    
    print("\n=== Available Audio Devices ===\n")
    
    for i in range(audio.get_device_count()):
        info = audio.get_device_info_by_index(i)
        print(f"Device {i}: {info['name']}")
        print(f"  Max Input Channels: {info['maxInputChannels']}")
        print(f"  Max Output Channels: {info['maxOutputChannels']}")
        print(f"  Default Sample Rate: {info['defaultSampleRate']}")
        print()
        
    audio.terminate()


def main():
    """Main entry point for the voice client."""
    parser = argparse.ArgumentParser(
        description="Real-time voice assistant client",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --server ws://localhost:8000
  %(prog)s --server ws://localhost:8000 --sample-rate 16000 --chunk-size 1024
  %(prog)s --list-devices
        """
    )
    
    parser.add_argument(
        '--server',
        type=str,
        default='ws://localhost:8000',
        help='WebSocket server URL (default: ws://localhost:8000)'
    )
    
    parser.add_argument(
        '--sample-rate',
        type=int,
        default=16000,
        help='Audio sample rate in Hz (default: 16000)'
    )
    
    parser.add_argument(
        '--channels',
        type=int,
        default=1,
        help='Number of audio channels (default: 1 for mono)'
    )
    
    parser.add_argument(
        '--chunk-size',
        type=int,
        default=1024,
        help='Audio chunk size in frames (default: 1024)'
    )
    
    parser.add_argument(
        '--reconnect-delay',
        type=float,
        default=2.0,
        help='Delay between reconnection attempts in seconds (default: 2.0)'
    )
    
    parser.add_argument(
        '--max-reconnect-attempts',
        type=int,
        default=5,
        help='Maximum number of reconnection attempts (default: 5)'
    )
    
    parser.add_argument(
        '--list-devices',
        action='store_true',
        help='List available audio devices and exit'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        
    # List devices if requested
    if args.list_devices:
        list_audio_devices()
        return
        
    # Create and run client
    client = VoiceClient(
        server_url=args.server,
        sample_rate=args.sample_rate,
        channels=args.channels,
        chunk_size=args.chunk_size,
        reconnect_delay=args.reconnect_delay,
        max_reconnect_attempts=args.max_reconnect_attempts
    )
    
    try:
        asyncio.run(client.run())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
