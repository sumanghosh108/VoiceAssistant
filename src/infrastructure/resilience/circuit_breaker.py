"""
Circuit breaker pattern implementation.

Prevents cascading failures by opening when failure rate exceeds threshold,
rejecting requests while open, and testing recovery in half-open state.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Optional

from src.utils.logger import logger


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass


class CircuitBreaker:
    """
    Implements circuit breaker pattern for external API calls.
    
    The circuit breaker prevents cascading failures by:
    - Opening when failure rate exceeds threshold
    - Rejecting requests while open
    - Testing recovery in half-open state
    - Closing when service recovers
    """
    
    def __init__(
        self,
        failure_threshold: float = 0.5,  # 50% failure rate
        window_size: int = 10,  # Over 10 requests
        timeout_seconds: int = 30,  # Open for 30 seconds
        name: str = "circuit"
    ):
        """Initialize circuit breaker."""
        self.failure_threshold = failure_threshold
        self.window_size = window_size
        self.timeout_seconds = timeout_seconds
        self.name = name
        
        self.state = CircuitState.CLOSED
        self.failures = 0
        self.successes = 0
        self.last_failure_time: Optional[datetime] = None
        self.state_changed_at = datetime.now()
        
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""
        # Check if circuit should transition from OPEN to HALF_OPEN
        if self.state == CircuitState.OPEN:
            if datetime.now() - self.state_changed_at > timedelta(seconds=self.timeout_seconds):
                self._transition_to(CircuitState.HALF_OPEN)
            else:
                raise CircuitBreakerOpenError(f"Circuit {self.name} is open")
                
        try:
            result = await func(*args, **kwargs)
            self._record_success()
            return result
        except Exception as e:
            self._record_failure()
            raise
            
    def _record_success(self) -> None:
        """Record successful call and handle state transitions."""
        self.successes += 1
        
        if self.state == CircuitState.HALF_OPEN:
            # Test request succeeded, close circuit
            self._transition_to(CircuitState.CLOSED)
            self.failures = 0
            self.successes = 0
            
    def _record_failure(self) -> None:
        """Record failed call and handle state transitions."""
        self.failures += 1
        self.last_failure_time = datetime.now()
        
        if self.state == CircuitState.HALF_OPEN:
            # Test request failed, reopen circuit
            self._transition_to(CircuitState.OPEN)
            return
            
        # Check if we should open the circuit
        total_requests = self.failures + self.successes
        if total_requests >= self.window_size:
            failure_rate = self.failures / total_requests
            if failure_rate >= self.failure_threshold:
                self._transition_to(CircuitState.OPEN)
                
        # Slide window to keep recent history
        if total_requests >= self.window_size:
            self.failures = int(self.failures * 0.5)
            self.successes = int(self.successes * 0.5)
            
    def _transition_to(self, new_state: CircuitState) -> None:
        """Transition to new state and emit event."""
        old_state = self.state
        self.state = new_state
        self.state_changed_at = datetime.now()
        
        logger.info(
            f"Circuit breaker {self.name} transitioned from {old_state.value} to {new_state.value}",
            circuit_name=self.name,
            old_state=old_state.value,
            new_state=new_state.value,
            failures=self.failures,
            successes=self.successes
        )
        
    def get_state(self) -> dict:
        """Get current circuit breaker state and metrics."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failures": self.failures,
            "successes": self.successes,
            "last_failure": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "state_changed_at": self.state_changed_at.isoformat()
        }
