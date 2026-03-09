"""
Timeout handling utilities.

Provides async timeout enforcement with proper error logging.
"""

import asyncio
from typing import Any, Coroutine, TypeVar

from src.utils.logger import logger


T = TypeVar('T')


async def with_timeout(
    coro: Coroutine[Any, Any, T],
    timeout_seconds: float,
    operation_name: str
) -> T:
    """
    Execute coroutine with timeout.
    
    Args:
        coro: Coroutine to execute
        timeout_seconds: Timeout in seconds
        operation_name: Name of operation for logging
        
    Returns:
        Result from coroutine
        
    Raises:
        TimeoutError: If operation exceeds timeout
        
    Example:
        result = await with_timeout(
            api_call(),
            timeout_seconds=3.0,
            operation_name="whisper_transcription"
        )
    """
    try:
        return await asyncio.wait_for(coro, timeout=timeout_seconds)
    except asyncio.TimeoutError:
        logger.error(
            f"Operation {operation_name} timed out after {timeout_seconds}s",
            operation=operation_name,
            timeout_seconds=timeout_seconds
        )
        raise TimeoutError(f"{operation_name} timed out after {timeout_seconds}s")
