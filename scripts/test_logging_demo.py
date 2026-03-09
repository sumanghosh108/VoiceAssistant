"""
Manual logging demonstration script.

This script demonstrates the production logging system with various
logging scenarios so you can see the logs being created in real-time.
"""

import time
from src.utils.logger import logger

def main():
    """Run logging demonstration."""
    
    print("=" * 70)
    print("PRODUCTION LOGGING SYSTEM DEMONSTRATION")
    print("=" * 70)
    print()
    print(f"📁 Log file location: {logger.log_file}")
    print(f"📊 Log level: {logger.level}")
    print()
    print("Watch the console output AND check the log file!")
    print("=" * 70)
    print()
    
    # 1. Basic logging
    print("1️⃣  Basic Logging Examples:")
    print("-" * 70)
    logger.info("Application started successfully")
    logger.debug("Debug information (may not show if level is INFO)")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    print()
    time.sleep(1)
    
    # 2. Logging with context
    print("2️⃣  Logging with Contextual Fields:")
    print("-" * 70)
    logger.info(
        "User logged in",
        user_id="user-12345",
        ip_address="192.168.1.100",
        login_method="oauth",
        timestamp_ms=1234567890
    )
    logger.info(
        "Processing audio",
        session_id="session-abc-123",
        component="asr",
        audio_duration_ms=500,
        sample_rate=16000
    )
    logger.info(
        "API call completed",
        component="llm",
        service="gemini",
        response_time_ms=850,
        token_count=120
    )
    print()
    time.sleep(1)
    
    # 3. Bound logger with persistent context
    print("3️⃣  Bound Logger (Persistent Context):")
    print("-" * 70)
    session_logger = logger.bind(
        session_id="session-xyz-789",
        user_id="user-67890",
        component="session_manager"
    )
    
    session_logger.info("Session created")
    session_logger.info("Audio streaming started")
    session_logger.info("Transcription in progress")
    session_logger.info("Response generated")
    session_logger.info("Session completed successfully")
    print()
    time.sleep(1)
    
    # 4. Error logging
    print("4️⃣  Error Logging:")
    print("-" * 70)
    logger.error(
        "Service timeout",
        component="tts",
        service="elevenlabs",
        error_type="TimeoutError",
        timeout_ms=3000,
        retry_count=3
    )
    logger.error(
        "API rate limit exceeded",
        component="asr",
        service="whisper",
        error_code=429,
        retry_after_seconds=60
    )
    print()
    time.sleep(1)
    
    # 5. Exception logging
    print("5️⃣  Exception Logging with Traceback:")
    print("-" * 70)
    try:
        # Simulate an error
        result = 10 / 0
    except ZeroDivisionError as e:
        logger.exception(
            "Division by zero error",
            component="calculator",
            operation="divide",
            error_type=type(e).__name__
        )
    print()
    time.sleep(1)
    
    # 6. Simulating a real session
    print("6️⃣  Simulating Real Voice Assistant Session:")
    print("-" * 70)
    
    # Create session-specific logger
    real_session = logger.bind(
        session_id="session-real-001",
        user_id="user-alice",
        client_ip="203.0.113.42"
    )
    
    real_session.info("WebSocket connection established")
    time.sleep(0.2)
    
    real_session.info("Audio frame received", frame_size=1024, sequence=1)
    time.sleep(0.1)
    
    real_session.info("Transcription started", component="asr", audio_duration_ms=500)
    time.sleep(0.3)
    
    real_session.info("Transcription completed", component="asr", text="Hello, how are you?", duration_ms=150)
    time.sleep(0.1)
    
    real_session.info("LLM processing started", component="llm", prompt_length=20)
    time.sleep(0.4)
    
    real_session.info("LLM response generated", component="llm", response="I'm doing well, thank you!", tokens=8, duration_ms=800)
    time.sleep(0.1)
    
    real_session.info("TTS synthesis started", component="tts", text_length=30)
    time.sleep(0.3)
    
    real_session.info("TTS synthesis completed", component="tts", audio_size=16384, duration_ms=200)
    time.sleep(0.1)
    
    real_session.info("Audio response sent to client", bytes_sent=16384)
    time.sleep(0.1)
    
    real_session.info("Session ended gracefully", total_duration_ms=2500)
    print()
    
    # Final summary
    print("=" * 70)
    print("✅ DEMONSTRATION COMPLETE!")
    print("=" * 70)
    print()
    print(f"📁 Check your log file: {logger.log_file}")
    print()
    print("To view the log file:")
    print(f"  Windows: type {logger.log_file}")
    print(f"  Linux/Mac: cat {logger.log_file}")
    print()
    print("To view formatted JSON (one entry at a time):")
    print(f"  Get-Content {logger.log_file} | ForEach-Object {{ $_ | ConvertFrom-Json | ConvertTo-Json }}")
    print()
    print("=" * 70)


if __name__ == "__main__":
    main()
