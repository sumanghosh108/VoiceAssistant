"""
Main application entry point for the real-time voice assistant.

This module initializes all system components and starts the servers:
- Loads configuration from environment variables and config files
- Initializes structured logging
- Creates circuit breakers for external services
- Initializes ASR, LLM, and TTS services
- Sets up latency tracking and monitoring
- Starts metrics dashboard HTTP server
- Starts health check HTTP server
- Starts WebSocket server for client connections
- Handles graceful shutdown on KeyboardInterrupt

Requirements: 7.1, 7.4, 18.1, 18.2
"""

import asyncio
import signal
import sys
from pathlib import Path
from dotenv import load_dotenv

from aiohttp import web

# Load environment variables from .env file
load_dotenv()

from src.infrastructure.config import ConfigLoader
from src.utils.logger import ProductionLogger, logger
from src.observability.health import SystemHealth, HealthCheckServer
from src.infrastructure.resilience import CircuitBreaker
from src.services.asr import ASRService
from src.services.llm import ReasoningService
from src.services.tts import TTSService
from src.observability.latency import MetricsAggregator, LatencyBudget, LatencyMonitor
from src.session.manager import SessionManager
from src.observability.metrics import MetricsDashboard
from src.api.websocket import WebSocketServer


async def main():
    """Main application entry point.
    
    Initializes all system components and starts the servers. Handles graceful
    shutdown on KeyboardInterrupt or SIGTERM.
    
    Requirements: 7.1, 7.4, 18.1, 18.2
    """
    # Load configuration
    try:
        config = ConfigLoader.load()
    except ValueError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Configure logging with configured log level
    production_logger = ProductionLogger("voice_assistant", level=config.observability.log_level)
    
    logger.info(
        "Starting Real-Time Voice Assistant",
        component="main",
        log_level=config.observability.log_level,
        websocket_port=config.server.websocket_port,
        metrics_port=config.server.metrics_port,
        recording_enabled=config.observability.enable_recording
    )
    
    # Initialize system health tracker
    system_health = SystemHealth()
    
    # Initialize circuit breakers for external services
    circuit_breakers = {
        "asr": CircuitBreaker(
            failure_threshold=config.resilience.circuit_breaker_failure_threshold,
            window_size=config.resilience.circuit_breaker_window_size,
            timeout_seconds=config.resilience.circuit_breaker_timeout_seconds,
            name="asr"
        ),
        "llm": CircuitBreaker(
            failure_threshold=config.resilience.circuit_breaker_failure_threshold,
            window_size=config.resilience.circuit_breaker_window_size,
            timeout_seconds=config.resilience.circuit_breaker_timeout_seconds,
            name="llm"
        ),
        "tts": CircuitBreaker(
            failure_threshold=config.resilience.circuit_breaker_failure_threshold,
            window_size=config.resilience.circuit_breaker_window_size,
            timeout_seconds=config.resilience.circuit_breaker_timeout_seconds,
            name="tts"
        )
    }
    
    logger.info(
        "Circuit breakers initialized",
        component="main",
        failure_threshold=config.resilience.circuit_breaker_failure_threshold,
        window_size=config.resilience.circuit_breaker_window_size,
        timeout_seconds=config.resilience.circuit_breaker_timeout_seconds
    )
    
    # Initialize services
    try:
        asr_service = ASRService(
            api_key=config.api.whisper_api_key,  # Use OpenAI API key
            timeout=config.api.whisper_timeout,
            buffer_duration_ms=config.pipeline.audio_buffer_duration_ms,
            circuit_breaker=circuit_breakers["asr"]
        )
    except Exception as e:
        print(f"Fatal error initializing ASR service: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    llm_service = ReasoningService(
        api_key=config.api.gemini_api_key,
        model=config.api.gemini_model,
        timeout=config.api.gemini_timeout,
        circuit_breaker=circuit_breakers["llm"]
    )
    
    tts_service = TTSService(
        api_key=config.api.elevenlabs_api_key,
        voice_id=config.api.elevenlabs_voice_id,
        timeout=config.api.elevenlabs_timeout,
        phrase_buffer_tokens=config.pipeline.token_buffer_size,
        circuit_breaker=circuit_breakers["tts"]
    )
    
    logger.info(
        "Services initialized",
        component="main",
        asr_timeout=config.api.whisper_timeout,
        llm_model=config.api.gemini_model,
        llm_timeout=config.api.gemini_timeout,
        tts_timeout=config.api.elevenlabs_timeout
    )
    
    # Initialize metrics and latency tracking
    metrics_aggregator = MetricsAggregator()
    latency_budget = LatencyBudget(
        asr_latency_ms=config.observability.latency_budget_asr_ms,
        llm_first_token_ms=config.observability.latency_budget_llm_first_token_ms,
        tts_latency_ms=config.observability.latency_budget_tts_ms,
        end_to_end_ms=config.observability.latency_budget_end_to_end_ms
    )
    latency_monitor = LatencyMonitor(latency_budget, metrics_aggregator)
    
    logger.info(
        "Latency tracking initialized",
        component="main",
        asr_budget_ms=config.observability.latency_budget_asr_ms,
        llm_budget_ms=config.observability.latency_budget_llm_first_token_ms,
        tts_budget_ms=config.observability.latency_budget_tts_ms,
        e2e_budget_ms=config.observability.latency_budget_end_to_end_ms
    )
    
    # Initialize session manager
    session_manager = SessionManager(
        asr_service=asr_service,
        llm_service=llm_service,
        tts_service=tts_service,
        enable_recording=config.observability.enable_recording,
        recording_storage_path=config.observability.recording_storage_path
    )
    
    # Create recordings directory if recording is enabled
    if config.observability.enable_recording:
        recordings_path = Path(config.observability.recording_storage_path)
        recordings_path.mkdir(parents=True, exist_ok=True)
        logger.info(
            "Session recording enabled",
            component="main",
            storage_path=str(recordings_path)
        )
    
    # Create combined HTTP server with metrics dashboard and health check endpoints
    # Both services share the same aiohttp application on the metrics port
    http_app = web.Application()
    
    # Add metrics dashboard routes
    dashboard = MetricsDashboard(metrics_aggregator, latency_monitor)
    http_app.router.add_get('/metrics', dashboard.handle_metrics)
    http_app.router.add_get('/dashboard', dashboard.handle_dashboard)
    
    # Add health check routes
    health_server = HealthCheckServer(system_health, circuit_breakers)
    http_app.router.add_get('/health', health_server.handle_health)
    http_app.router.add_get('/health/ready', health_server.handle_ready)
    http_app.router.add_get('/health/live', health_server.handle_live)
    
    # Start the combined HTTP server
    http_runner = web.AppRunner(http_app)
    await http_runner.setup()
    http_site = web.TCPSite(
        http_runner,
        config.server.metrics_host,
        config.server.metrics_port
    )
    await http_site.start()
    
    logger.info(
        "HTTP server started with metrics and health endpoints",
        component="main",
        host=config.server.metrics_host,
        port=config.server.metrics_port,
        metrics_url=f"http://{config.server.metrics_host}:{config.server.metrics_port}/metrics",
        dashboard_url=f"http://{config.server.metrics_host}:{config.server.metrics_port}/dashboard",
        health_url=f"http://{config.server.metrics_host}:{config.server.metrics_port}/health"
    )
    
    # Start WebSocket server
    websocket_server = WebSocketServer(session_manager)
    websocket_task = asyncio.create_task(
        websocket_server.start(
            host=config.server.websocket_host,
            port=config.server.websocket_port
        )
    )
    
    logger.info(
        "Real-Time Voice Assistant started successfully",
        component="main",
        websocket_url=f"ws://{config.server.websocket_host}:{config.server.websocket_port}",
        metrics_url=f"http://{config.server.metrics_host}:{config.server.metrics_port}/metrics",
        dashboard_url=f"http://{config.server.metrics_host}:{config.server.metrics_port}/dashboard",
        health_url=f"http://{config.server.metrics_host}:{config.server.metrics_port}/health"
    )
    
    # Setup signal handlers for graceful shutdown
    shutdown_event = asyncio.Event()
    
    def signal_handler(sig, frame):
        """Handle shutdown signals."""
        logger.info(
            "Received shutdown signal",
            component="main",
            signal=sig
        )
        shutdown_event.set()
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Wait for shutdown signal
    try:
        await shutdown_event.wait()
    except KeyboardInterrupt:
        logger.info("Received KeyboardInterrupt", component="main")
    
    # Graceful shutdown
    logger.info("Shutting down gracefully...", component="main")
    
    # Cancel WebSocket server task
    websocket_task.cancel()
    try:
        await websocket_task
    except asyncio.CancelledError:
        pass
    
    # Cleanup HTTP server (metrics + health)
    await http_runner.cleanup()
    
    logger.info("Shutdown complete", component="main")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown complete")
        sys.exit(0)
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        sys.exit(1)
