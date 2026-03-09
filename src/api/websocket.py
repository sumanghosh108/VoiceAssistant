"""
WebSocket server for real-time voice assistant.

This module implements the WebSocket server that manages bidirectional streaming
connections with clients. It handles:
- Accepting WebSocket connections and managing session lifecycle
- Receiving audio data from clients and parsing into AudioFrame events
- Sending synthesized audio from TTS service back to clients
- Connection error handling and graceful cleanup

Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 5.1, 5.2, 5.3, 5.4, 5.5, 5.6
"""

import asyncio
import struct
from datetime import datetime
from typing import Optional

import websockets
from websockets.server import WebSocketServerProtocol

from src.core.events import AudioFrame, TTSAudioEvent, ErrorEvent, ErrorType
from src.utils.logger import logger
from src.core.models import Session
from src.session.manager import SessionManager


class WebSocketServer:
    """Manages WebSocket connections and session lifecycle.
    
    The WebSocketServer accepts client connections, creates sessions for each
    connection, and manages bidirectional audio streaming. It runs two concurrent
    tasks per connection:
    - receive_audio_loop: Receives audio from client and emits AudioFrame events
    - send_audio_loop: Consumes TTSAudioEvent and sends audio to client
    
    Requirements: 1.1, 1.2, 1.6, 1.7
    """
    
    def __init__(self, session_manager: SessionManager):
        """Initialize WebSocket server.
        
        Args:
            session_manager: SessionManager instance for creating and managing sessions
        """
        self.session_manager = session_manager
        self.server: Optional[websockets.WebSocketServer] = None
        
        logger.info(
            "WebSocketServer initialized",
            component="websocket"
        )
        
    async def start(self, host: str, port: int) -> None:
        """Start the WebSocket server.
        
        Starts the WebSocket server on the specified host and port. This method
        will run indefinitely, accepting connections until the server is stopped.
        
        Args:
            host: Host address to bind to (e.g., "0.0.0.0", "localhost")
            port: Port number to listen on (e.g., 8000)
            
        Requirements: 1.1, 1.2
        """
        logger.info(
            "Starting WebSocket server",
            component="websocket",
            host=host,
            port=port
        )
        
        self.server = await websockets.serve(
            self.handle_connection,
            host,
            port
        )
        
        logger.info(
            "WebSocket server started",
            component="websocket",
            host=host,
            port=port
        )
        
        # Keep server running
        await asyncio.Future()  # Run forever
        
    async def handle_connection(
        self,
        websocket: WebSocketServerProtocol
    ) -> None:
        """Handle a single WebSocket connection.
        
        Manages the complete lifecycle of a WebSocket connection:
        1. Create session using SessionManager
        2. Start audio receive loop
        3. Start audio send loop
        4. Wait for disconnect
        5. Cleanup session
        
        Args:
            websocket: WebSocket connection object
            path: WebSocket path (unused but required by websockets library)
            
        Requirements: 1.2, 1.6, 1.7
        """
        session: Optional[Session] = None
        
        try:
            # Create session
            session = await self.session_manager.create_session(websocket)
            session_id = session.session_id
            
            logger.info(
                "WebSocket connection established",
                component="websocket",
                session_id=session_id,
                remote_address=websocket.remote_address
            )
            
            # Start receive and send loops concurrently
            receive_task = asyncio.create_task(
                self.receive_audio_loop(websocket, session),
                name=f"ws_receive_{session_id}"
            )
            send_task = asyncio.create_task(
                self.send_audio_loop(websocket, session),
                name=f"ws_send_{session_id}"
            )
            
            # Wait for either task to complete (disconnect or error)
            done, pending = await asyncio.wait(
                [receive_task, send_task],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # Cancel remaining tasks
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                    
            logger.info(
                "WebSocket connection closed",
                component="websocket",
                session_id=session_id
            )
            
        except Exception as e:
            logger.error(
                "Error in WebSocket connection handler",
                component="websocket",
                session_id=session.session_id if session else "unknown",
                error=str(e),
                error_type=type(e).__name__
            )
            
        finally:
            # Cleanup session
            if session:
                await self.session_manager.cleanup_session(session.session_id)
                
    async def receive_audio_loop(
        self,
        websocket: WebSocketServerProtocol,
        session: Session
    ) -> None:
        """Receive audio from client and emit AudioFrame events.
        
        Continuously receives audio data from the WebSocket client, parses it
        into AudioFrame objects, validates the frames, and emits them to the
        session's audio queue for processing by the ASR service.
        
        Audio data format (binary):
        - 8 bytes: timestamp (double, seconds since epoch)
        - 4 bytes: sequence_number (unsigned int)
        - Remaining bytes: audio data (PCM 16-bit, 16kHz mono)
        
        Args:
            websocket: WebSocket connection object
            session: Session instance for this connection
            
        Requirements: 1.3, 1.4, 1.5
        """
        session_id = session.session_id
        sequence_number = 0
        
        logger.debug(
            "Starting audio receive loop",
            component="websocket",
            session_id=session_id
        )
        
        try:
            async for message in websocket:
                try:
                    # Expect binary messages
                    if not isinstance(message, bytes):
                        logger.warning(
                            "Received non-binary message, ignoring",
                            component="websocket",
                            session_id=session_id,
                            message_type=type(message).__name__
                        )
                        continue
                    
                    # Parse message: timestamp (8 bytes) + sequence (4 bytes) + audio data
                    if len(message) < 12:
                        logger.warning(
                            "Received message too short, ignoring",
                            component="websocket",
                            session_id=session_id,
                            message_length=len(message)
                        )
                        continue
                    
                    # Unpack timestamp and sequence number
                    timestamp_seconds, seq_num = struct.unpack('!dI', message[:12])
                    audio_data = message[12:]
                    
                    # Create timestamp from seconds since epoch
                    timestamp = datetime.fromtimestamp(timestamp_seconds)
                    
                    # Validate timestamp exists (not None or zero)
                    if timestamp_seconds == 0:
                        logger.warning(
                            "Received AudioFrame with zero timestamp",
                            component="websocket",
                            session_id=session_id,
                            sequence_number=seq_num
                        )
                        # Emit error event
                        error_event = ErrorEvent(
                            session_id=session_id,
                            component="websocket",
                            error_type=ErrorType.VALIDATION_ERROR,
                            message="AudioFrame missing timestamp",
                            timestamp=datetime.now(),
                            retryable=False
                        )
                        # Note: We don't have an error queue in the current design
                        # Just log the error
                        continue
                    
                    # Create AudioFrame
                    audio_frame = AudioFrame(
                        session_id=session_id,
                        data=audio_data,
                        timestamp=timestamp,
                        sequence_number=seq_num,
                        sample_rate=16000,
                        channels=1
                    )
                    
                    # Emit to audio queue
                    try:
                        await asyncio.wait_for(
                            session.audio_queue.put(audio_frame),
                            timeout=1.0
                        )
                        
                        sequence_number = seq_num
                        
                        logger.debug(
                            "AudioFrame emitted to queue",
                            component="websocket",
                            session_id=session_id,
                            sequence_number=seq_num,
                            audio_bytes=len(audio_data)
                        )
                        
                    except asyncio.TimeoutError:
                        logger.warning(
                            "Audio queue full, dropping frame",
                            component="websocket",
                            session_id=session_id,
                            sequence_number=seq_num
                        )
                        
                except struct.error as e:
                    logger.error(
                        "Failed to parse audio frame",
                        component="websocket",
                        session_id=session_id,
                        error=str(e),
                        error_type="parsing_error"
                    )
                    # Emit error event
                    error_event = ErrorEvent(
                        session_id=session_id,
                        component="websocket",
                        error_type=ErrorType.VALIDATION_ERROR,
                        message=f"Failed to parse audio frame: {str(e)}",
                        timestamp=datetime.now(),
                        retryable=False
                    )
                    
                except Exception as e:
                    logger.error(
                        "Error processing audio frame",
                        component="websocket",
                        session_id=session_id,
                        error=str(e),
                        error_type=type(e).__name__
                    )
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info(
                "WebSocket connection closed by client",
                component="websocket",
                session_id=session_id
            )
        except Exception as e:
            logger.error(
                "Error in audio receive loop",
                component="websocket",
                session_id=session_id,
                error=str(e),
                error_type=type(e).__name__
            )
            
    async def send_audio_loop(
        self,
        websocket: WebSocketServerProtocol,
        session: Session
    ) -> None:
        """Consume TTSAudioEvent and send to client.
        
        Continuously consumes TTSAudioEvent objects from the session's TTS queue,
        serializes them to binary format, and sends them to the WebSocket client.
        Handles backpressure by dropping frames when the client cannot consume
        audio fast enough, and handles network errors by closing the connection.
        
        Audio packet format (binary):
        - 4 bytes: sequence_number (unsigned int)
        - 1 byte: is_final flag (0 or 1)
        - Remaining bytes: audio data (PCM 16-bit, 16kHz mono)
        
        Args:
            websocket: WebSocket connection object
            session: Session instance for this connection
            
        Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6
        """
        session_id = session.session_id
        
        logger.debug(
            "Starting audio send loop",
            component="websocket",
            session_id=session_id
        )
        
        try:
            while True:
                try:
                    # Get TTS audio event from queue with timeout for backpressure
                    tts_event = await asyncio.wait_for(
                        session.tts_queue.get(),
                        timeout=0.1  # 100ms timeout for responsiveness
                    )
                    
                    logger.info(
                        "Got TTS audio event from queue",
                        component="websocket",
                        session_id=session_id,
                        sequence_number=tts_event.sequence_number,
                        is_final=tts_event.is_final,
                        audio_bytes=len(tts_event.audio_data)
                    )
                    
                    # Serialize TTSAudioEvent to bytes
                    # Format: sequence_number (4 bytes) + is_final (1 byte) + audio_data
                    is_final_byte = 1 if tts_event.is_final else 0
                    packet = struct.pack(
                        '!IB',
                        tts_event.sequence_number,
                        is_final_byte
                    ) + tts_event.audio_data
                    
                    logger.info(
                        "Sending audio packet to client",
                        component="websocket",
                        session_id=session_id,
                        packet_size=len(packet)
                    )
                    
                    # Send to client
                    try:
                        await asyncio.wait_for(
                            websocket.send(packet),
                            timeout=1.0  # 1 second timeout for network send
                        )
                        
                        logger.info(
                            "Audio packet sent to client",
                            component="websocket",
                            session_id=session_id,
                            sequence_number=tts_event.sequence_number,
                            is_final=tts_event.is_final,
                            audio_bytes=len(tts_event.audio_data)
                        )
                        
                    except asyncio.TimeoutError:
                        # Network send timeout - client may be slow
                        logger.warning(
                            "Network send timeout, dropping frame",
                            component="websocket",
                            session_id=session_id,
                            sequence_number=tts_event.sequence_number
                        )
                        # Continue to next frame (backpressure handling)
                        
                except asyncio.TimeoutError:
                    # Queue get timeout - no audio available, continue waiting
                    continue
                    
                except websockets.exceptions.ConnectionClosed:
                    logger.info(
                        "WebSocket connection closed during send",
                        component="websocket",
                        session_id=session_id
                    )
                    break
                    
                except Exception as e:
                    # Network error - log and close connection
                    logger.error(
                        "Network error during audio send",
                        component="websocket",
                        session_id=session_id,
                        error=str(e),
                        error_type=type(e).__name__
                    )
                    # Close connection
                    await websocket.close()
                    break
                    
        except Exception as e:
            logger.error(
                "Error in audio send loop",
                component="websocket",
                session_id=session_id,
                error=str(e),
                error_type=type(e).__name__
            )
