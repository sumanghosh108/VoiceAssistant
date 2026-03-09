"""
API layer for the real-time voice assistant.

This package provides:
- WebSocket server for real-time audio streaming
- HTTP endpoints for health checks
"""

from src.api.websocket import WebSocketServer
from src.api.health_server import HealthCheckServer

__all__ = [
    "WebSocketServer",
    "HealthCheckServer",
]
