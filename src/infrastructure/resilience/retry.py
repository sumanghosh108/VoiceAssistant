"""
Retry mechanism with exponential backoff.

Provides decorator for adding retry logic to async functions with
configurable backoff strategy and exception handling.
"""

import asyncio
from dataclasses import dataclass
from functools import wraps
from typing import Callable, Tuple, Type

from src.utils.logger import logger


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    initial_delay_ms: int = 100
    max_delay_ms: int = 5000
    exponential_base: float = 2.0
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,)


def with_retry(config: RetryConfig):
    """
    Decorator for adding retry logic with exponential backoff to async functions.
    
    Args:
        config: RetryConfig specifying retry behavior
        
    Returns:
        Decorator function
        
    Example:
        retry_config = RetryConfig(max_attempts=3, initial_delay_ms=100)
        
        @with_retry(retry_config)
        async def call_api():
            # API call that may fail
            pass
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(config.max_attempts):
                try:
                    return await func(*args, **kwargs)
                except config.retryable_exceptions as e:
                    last_exception = e
                    
                    if attempt < config.max_attempts - 1:
                        # Calculate delay with exponential backoff
                        delay_ms = min(
                            config.initial_delay_ms * (config.exponential_base ** attempt),
                            config.max_delay_ms
                        )
                        
                        logger.warning(
                            f"Attempt {attempt + 1} failed, retrying in {delay_ms}ms",
                            function=func.__name__,
                            attempt=attempt + 1,
                            max_attempts=config.max_attempts,
                            delay_ms=delay_ms,
                            error=str(e)
                        )
                        
                        await asyncio.sleep(delay_ms / 1000)
                    else:
                        logger.error(
                            f"All {config.max_attempts} attempts failed",
                            function=func.__name__,
                            error=str(e)
                        )
                        
            raise last_exception
            
        return wrapper
    return decorator
