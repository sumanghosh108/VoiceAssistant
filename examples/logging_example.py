"""
Example demonstrating the production logging system.

This example shows how to use the ProductionLogger with:
- Basic logging
- Contextual fields
- Bound loggers
- Exception logging
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.logger import logger, ProductionLogger


def basic_logging_example():
    """Demonstrate basic logging."""
    print("\n=== Basic Logging Example ===\n")
    
    logger.debug("Debug message - detailed diagnostic info")
    logger.info("Info message - general information")
    logger.warning("Warning message - potential issue")
    logger.error("Error message - something went wrong")


def contextual_logging_example():
    """Demonstrate logging with contextual fields."""
    print("\n=== Contextual Logging Example ===\n")
    
    # Log with various context fields
    logger.info(
        "User logged in",
        user_id="user-123",
        ip_address="192.168.1.100",
        login_method="oauth"
    )
    
    logger.info(
        "Processing request",
        session_id="session-456",
        component="asr",
        audio_duration_ms=500,
        sample_rate=16000
    )
    
    logger.error(
        "API call failed",
        component="tts",
        service="elevenlabs",
        error_code=429,
        retry_count=3
    )


def bound_logger_example():
    """Demonstrate bound logger with persistent context."""
    print("\n=== Bound Logger Example ===\n")
    
    # Create logger with persistent context
    session_logger = logger.bind(
        session_id="session-789",
        user_id="user-456",
        component="session"
    )
    
    # All logs automatically include the bound context
    session_logger.info("Session created")
    session_logger.info("Audio streaming started")
    session_logger.info("Transcription in progress")
    session_logger.info("Response generated")
    session_logger.info("Session ended")


def exception_logging_example():
    """Demonstrate exception logging with traceback."""
    print("\n=== Exception Logging Example ===\n")
    
    try:
        # Simulate an error
        result = 10 / 0
    except ZeroDivisionError as e:
        logger.exception(
            "Division error occurred",
            component="calculator",
            operation="divide",
            error_type=type(e).__name__
        )


async def async_logging_example():
    """Demonstrate logging in async context."""
    print("\n=== Async Logging Example ===\n")
    
    async_logger = logger.bind(component="async_worker")
    
    async_logger.info("Async task started")
    await asyncio.sleep(0.1)
    async_logger.info("Async task processing")
    await asyncio.sleep(0.1)
    async_logger.info("Async task completed")


def service_simulation_example():
    """Simulate service logging pattern."""
    print("\n=== Service Simulation Example ===\n")
    
    # Simulate ASR service
    asr_logger = logger.bind(component="asr", service="whisper")
    asr_logger.info("Transcription started", audio_size=8192)
    asr_logger.info("Transcription completed", text="Hello world", duration_ms=150)
    
    # Simulate LLM service
    llm_logger = logger.bind(component="llm", service="gemini")
    llm_logger.info("Generating response", prompt_length=50)
    llm_logger.info("Response generated", token_count=120, duration_ms=800)
    
    # Simulate TTS service
    tts_logger = logger.bind(component="tts", service="elevenlabs")
    tts_logger.info("Synthesizing speech", text_length=120)
    tts_logger.info("Speech synthesized", audio_size=16384, duration_ms=200)


def main():
    """Run all logging examples."""
    print("=" * 60)
    print("Production Logging System Examples")
    print("=" * 60)
    
    # Show log file location
    print(f"\nLog file: {logger.log_file}")
    print(f"Log level: {logger.level}")
    print("\nAll logs are written to both console and file.\n")
    
    # Run examples
    basic_logging_example()
    contextual_logging_example()
    bound_logger_example()
    exception_logging_example()
    asyncio.run(async_logging_example())
    service_simulation_example()
    
    print("\n" + "=" * 60)
    print(f"✅ Examples complete! Check log file: {logger.log_file}")
    print("=" * 60)
    print("\nTo view logs:")
    print(f"  cat {logger.log_file}")
    print(f"  cat {logger.log_file} | python -m json.tool")
    print("\n")


if __name__ == "__main__":
    main()
