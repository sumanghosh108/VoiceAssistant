"""
Unit tests for resilience patterns.

Tests circuit breaker, retry mechanism, and timeout handling.
"""

import asyncio
import pytest
from datetime import datetime, timedelta

from src.infrastructure.resilience import (
    CircuitBreaker,
    CircuitBreakerOpenError,
    CircuitState,
    RetryConfig,
    with_retry,
    with_timeout
)


# ============================================================================
# Circuit Breaker Tests
# ============================================================================

class TestCircuitBreaker:
    """Tests for CircuitBreaker class."""
    
    @pytest.mark.asyncio
    async def test_circuit_starts_closed(self):
        """Circuit breaker should start in CLOSED state."""
        cb = CircuitBreaker(name="test")
        assert cb.state == CircuitState.CLOSED
        assert cb.failures == 0
        assert cb.successes == 0
        
    @pytest.mark.asyncio
    async def test_successful_calls_stay_closed(self):
        """Successful calls should keep circuit CLOSED."""
        cb = CircuitBreaker(name="test")
        
        async def success_func():
            return "success"
            
        for _ in range(10):
            result = await cb.call(success_func)
            assert result == "success"
            
        assert cb.state == CircuitState.CLOSED
        assert cb.successes == 10
        assert cb.failures == 0
        
    @pytest.mark.asyncio
    async def test_circuit_opens_at_failure_threshold(self):
        """Circuit should open when failure rate exceeds threshold."""
        cb = CircuitBreaker(
            failure_threshold=0.5,
            window_size=10,
            name="test"
        )
        
        async def failing_func():
            raise Exception("API error")
            
        async def success_func():
            return "success"
            
        # Generate 6 failures and 4 successes (60% failure rate)
        # Do successes first, then failures to avoid window sliding
        for i in range(4):
            await cb.call(success_func)
            
        for i in range(6):
            try:
                await cb.call(failing_func)
            except Exception:
                pass
                
        # Circuit should be open now (6/10 = 60% > 50% threshold)
        assert cb.state == CircuitState.OPEN
        
    @pytest.mark.asyncio
    async def test_open_circuit_rejects_calls(self):
        """Open circuit should reject calls immediately."""
        cb = CircuitBreaker(
            failure_threshold=0.5,
            window_size=10,
            name="test"
        )
        
        # Force circuit open
        cb.state = CircuitState.OPEN
        cb.state_changed_at = datetime.now()
        
        async def some_func():
            return "should not execute"
            
        with pytest.raises(CircuitBreakerOpenError) as exc_info:
            await cb.call(some_func)
            
        assert "Circuit test is open" in str(exc_info.value)
        
    @pytest.mark.asyncio
    async def test_circuit_transitions_to_half_open_after_timeout(self):
        """Circuit should transition to HALF_OPEN after timeout."""
        cb = CircuitBreaker(
            timeout_seconds=1,
            name="test"
        )
        
        # Force circuit open with old timestamp
        cb.state = CircuitState.OPEN
        cb.state_changed_at = datetime.now() - timedelta(seconds=2)
        
        async def success_func():
            return "success"
            
        # Should transition to HALF_OPEN and succeed
        result = await cb.call(success_func)
        assert result == "success"
        assert cb.state == CircuitState.CLOSED  # Success in HALF_OPEN closes circuit
        
    @pytest.mark.asyncio
    async def test_half_open_success_closes_circuit(self):
        """Successful call in HALF_OPEN should close circuit."""
        cb = CircuitBreaker(name="test")
        cb.state = CircuitState.HALF_OPEN
        
        async def success_func():
            return "success"
            
        result = await cb.call(success_func)
        assert result == "success"
        assert cb.state == CircuitState.CLOSED
        assert cb.failures == 0
        assert cb.successes == 0  # Counters reset
        
    @pytest.mark.asyncio
    async def test_half_open_failure_reopens_circuit(self):
        """Failed call in HALF_OPEN should reopen circuit."""
        cb = CircuitBreaker(name="test")
        cb.state = CircuitState.HALF_OPEN
        
        async def failing_func():
            raise Exception("Still failing")
            
        with pytest.raises(Exception):
            await cb.call(failing_func)
            
        assert cb.state == CircuitState.OPEN
        
    @pytest.mark.asyncio
    async def test_get_state_returns_metrics(self):
        """get_state should return current state and metrics."""
        cb = CircuitBreaker(name="test_circuit")
        cb.failures = 3
        cb.successes = 7
        
        state = cb.get_state()
        
        assert state["name"] == "test_circuit"
        assert state["state"] == "closed"
        assert state["failures"] == 3
        assert state["successes"] == 7
        assert "state_changed_at" in state


# ============================================================================
# Retry Mechanism Tests
# ============================================================================

class TestRetryMechanism:
    """Tests for retry mechanism with exponential backoff."""
    
    @pytest.mark.asyncio
    async def test_successful_call_no_retry(self):
        """Successful call should not trigger retries."""
        config = RetryConfig(max_attempts=3)
        call_count = 0
        
        @with_retry(config)
        async def success_func():
            nonlocal call_count
            call_count += 1
            return "success"
            
        result = await success_func()
        assert result == "success"
        assert call_count == 1
        
    @pytest.mark.asyncio
    async def test_retry_on_failure(self):
        """Failed calls should be retried up to max_attempts."""
        config = RetryConfig(
            max_attempts=3,
            initial_delay_ms=10,  # Short delay for testing
            retryable_exceptions=(ValueError,)
        )
        call_count = 0
        
        @with_retry(config)
        async def failing_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("API error")
            
        with pytest.raises(ValueError):
            await failing_func()
            
        assert call_count == 3  # Should try 3 times
        
    @pytest.mark.asyncio
    async def test_exponential_backoff_timing(self):
        """Retry delays should follow exponential backoff."""
        config = RetryConfig(
            max_attempts=3,
            initial_delay_ms=100,
            exponential_base=2.0
        )
        
        call_times = []
        
        @with_retry(config)
        async def failing_func():
            call_times.append(datetime.now())
            raise Exception("Fail")
            
        with pytest.raises(Exception):
            await failing_func()
            
        # Check delays between attempts
        assert len(call_times) == 3
        
        # First retry delay: ~100ms
        delay1 = (call_times[1] - call_times[0]).total_seconds() * 1000
        assert 90 < delay1 < 150  # Allow some variance
        
        # Second retry delay: ~200ms
        delay2 = (call_times[2] - call_times[1]).total_seconds() * 1000
        assert 180 < delay2 < 250
        
    @pytest.mark.asyncio
    async def test_max_delay_cap(self):
        """Retry delay should not exceed max_delay_ms."""
        config = RetryConfig(
            max_attempts=5,
            initial_delay_ms=1000,
            max_delay_ms=2000,
            exponential_base=2.0
        )
        
        call_times = []
        
        @with_retry(config)
        async def failing_func():
            call_times.append(datetime.now())
            raise Exception("Fail")
            
        with pytest.raises(Exception):
            await failing_func()
            
        # Third retry would be 4000ms without cap, should be capped at 2000ms
        if len(call_times) >= 4:
            delay3 = (call_times[3] - call_times[2]).total_seconds() * 1000
            assert delay3 < 2500  # Should be around 2000ms, not 4000ms
            
    @pytest.mark.asyncio
    async def test_eventual_success_after_retries(self):
        """Function should succeed if it works on a retry."""
        config = RetryConfig(
            max_attempts=3,
            initial_delay_ms=10
        )
        call_count = 0
        
        @with_retry(config)
        async def eventually_succeeds():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Not yet")
            return "success"
            
        result = await eventually_succeeds()
        assert result == "success"
        assert call_count == 3
        
    @pytest.mark.asyncio
    async def test_non_retryable_exception_not_retried(self):
        """Non-retryable exceptions should not trigger retries."""
        config = RetryConfig(
            max_attempts=3,
            retryable_exceptions=(ValueError,)
        )
        call_count = 0
        
        @with_retry(config)
        async def raises_type_error():
            nonlocal call_count
            call_count += 1
            raise TypeError("Not retryable")
            
        with pytest.raises(TypeError):
            await raises_type_error()
            
        assert call_count == 1  # Should not retry


# ============================================================================
# Timeout Handling Tests
# ============================================================================

class TestTimeoutHandling:
    """Tests for timeout handling utilities."""
    
    @pytest.mark.asyncio
    async def test_successful_call_within_timeout(self):
        """Call completing within timeout should succeed."""
        async def quick_func():
            await asyncio.sleep(0.1)
            return "success"
            
        result = await with_timeout(
            quick_func(),
            timeout_seconds=1.0,
            operation_name="quick_operation"
        )
        assert result == "success"
        
    @pytest.mark.asyncio
    async def test_timeout_raises_error(self):
        """Call exceeding timeout should raise TimeoutError."""
        async def slow_func():
            await asyncio.sleep(2.0)
            return "too slow"
            
        with pytest.raises(TimeoutError) as exc_info:
            await with_timeout(
                slow_func(),
                timeout_seconds=0.1,
                operation_name="slow_operation"
            )
            
        assert "slow_operation" in str(exc_info.value)
        assert "timed out" in str(exc_info.value)
        
    @pytest.mark.asyncio
    async def test_timeout_error_message_includes_details(self):
        """Timeout error should include operation name and duration."""
        async def slow_func():
            await asyncio.sleep(1.0)
            
        with pytest.raises(TimeoutError) as exc_info:
            await with_timeout(
                slow_func(),
                timeout_seconds=0.05,
                operation_name="test_operation"
            )
            
        error_msg = str(exc_info.value)
        assert "test_operation" in error_msg
        assert "0.05" in error_msg
        
    @pytest.mark.asyncio
    async def test_timeout_with_exception_in_coroutine(self):
        """Exceptions in coroutine should propagate before timeout."""
        async def failing_func():
            await asyncio.sleep(0.01)
            raise ValueError("Internal error")
            
        with pytest.raises(ValueError) as exc_info:
            await with_timeout(
                failing_func(),
                timeout_seconds=1.0,
                operation_name="failing_operation"
            )
            
        assert "Internal error" in str(exc_info.value)


# ============================================================================
# Integration Tests
# ============================================================================

class TestResilienceIntegration:
    """Integration tests combining multiple resilience patterns."""
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_with_retry(self):
        """Circuit breaker and retry can work together."""
        cb = CircuitBreaker(
            failure_threshold=0.5,
            window_size=4,
            name="test"
        )
        
        config = RetryConfig(
            max_attempts=2,
            initial_delay_ms=10
        )
        
        call_count = 0
        
        @with_retry(config)
        async def api_call():
            nonlocal call_count
            call_count += 1
            
            async def inner():
                raise Exception("API error")
                
            return await cb.call(inner)
            
        # Make calls that will fail and eventually open circuit
        for _ in range(3):
            try:
                await api_call()
            except Exception:
                pass
                
        # Circuit should be open after enough failures
        # (3 calls × 2 retries = 6 failures)
        assert cb.state == CircuitState.OPEN
        
    @pytest.mark.asyncio
    async def test_timeout_with_retry(self):
        """Timeout and retry can work together."""
        config = RetryConfig(
            max_attempts=2,
            initial_delay_ms=10
        )
        
        call_count = 0
        
        @with_retry(config)
        async def slow_api_call():
            nonlocal call_count
            call_count += 1
            
            async def slow():
                await asyncio.sleep(1.0)
                return "too slow"
                
            return await with_timeout(
                slow(),
                timeout_seconds=0.05,
                operation_name="api_call"
            )
            
        with pytest.raises(TimeoutError):
            await slow_api_call()
            
        # Should have tried twice
        assert call_count == 2
