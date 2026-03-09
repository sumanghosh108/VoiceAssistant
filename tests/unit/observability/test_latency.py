"""
Unit tests for the latency tracking and monitoring system.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from src.observability.latency import (
    LatencyMeasurement,
    LatencyTracker,
    MetricsAggregator,
    LatencyBudget,
    LatencyMonitor
)


class TestLatencyTracker:
    """Tests for LatencyTracker class."""
    
    def test_initialization(self):
        """Test LatencyTracker initialization."""
        tracker = LatencyTracker("session-123")
        assert tracker.session_id == "session-123"
        assert len(tracker.markers) == 0
        assert len(tracker.measurements) == 0
        
    def test_mark_event(self):
        """Test marking event timestamps."""
        tracker = LatencyTracker("session-123")
        
        tracker.mark("event1")
        assert "event1" in tracker.markers
        assert isinstance(tracker.markers["event1"], datetime)
        
        tracker.mark("event2")
        assert "event2" in tracker.markers
        assert len(tracker.markers) == 2
        
    def test_measure_duration(self):
        """Test measuring duration between events."""
        tracker = LatencyTracker("session-123")
        
        # Mark two events with a small delay
        tracker.mark("start")
        # Simulate some processing time
        import time
        time.sleep(0.01)  # 10ms
        tracker.mark("end")
        
        # Measure the duration
        tracker.measure("start", "end", "test_stage")
        
        assert len(tracker.measurements) == 1
        measurement = tracker.measurements[0]
        assert measurement.stage == "test_stage"
        assert measurement.session_id == "session-123"
        assert measurement.duration_ms >= 10  # At least 10ms
        assert measurement.duration_ms < 100  # But not too long
        
    def test_measure_missing_markers(self):
        """Test measuring with missing markers doesn't create measurement."""
        tracker = LatencyTracker("session-123")
        
        tracker.mark("start")
        # Don't mark "end"
        
        tracker.measure("start", "end", "test_stage")
        assert len(tracker.measurements) == 0
        
    def test_get_measurements(self):
        """Test retrieving measurements returns a copy."""
        tracker = LatencyTracker("session-123")
        
        tracker.mark("start")
        tracker.mark("end")
        tracker.measure("start", "end", "stage1")
        
        measurements = tracker.get_measurements()
        assert len(measurements) == 1
        
        # Modify the returned list
        measurements.append(LatencyMeasurement(
            stage="fake",
            duration_ms=100,
            timestamp=datetime.now(),
            session_id="fake"
        ))
        
        # Original should be unchanged
        assert len(tracker.get_measurements()) == 1
        
    def test_multiple_measurements(self):
        """Test tracking multiple measurements."""
        tracker = LatencyTracker("session-123")
        
        tracker.mark("audio_received")
        tracker.mark("transcript_start")
        tracker.mark("llm_start")
        
        tracker.measure("audio_received", "transcript_start", "asr_latency")
        tracker.measure("transcript_start", "llm_start", "llm_first_token_latency")
        
        measurements = tracker.get_measurements()
        assert len(measurements) == 2
        assert measurements[0].stage == "asr_latency"
        assert measurements[1].stage == "llm_first_token_latency"


class TestMetricsAggregator:
    """Tests for MetricsAggregator class."""
    
    def test_initialization(self):
        """Test MetricsAggregator initialization."""
        aggregator = MetricsAggregator()
        
        # Check all expected stages are initialized
        expected_stages = [
            "asr_latency",
            "llm_first_token_latency",
            "llm_generation_latency",
            "tts_latency",
            "end_to_end_latency",
            "websocket_send_latency"
        ]
        
        for stage in expected_stages:
            assert stage in aggregator.measurements
            assert aggregator.measurements[stage] == []
            
    @pytest.mark.asyncio
    async def test_record_measurement(self):
        """Test recording a measurement."""
        aggregator = MetricsAggregator()
        
        measurement = LatencyMeasurement(
            stage="asr_latency",
            duration_ms=250.5,
            timestamp=datetime.now(),
            session_id="session-123"
        )
        
        await aggregator.record(measurement)
        
        assert len(aggregator.measurements["asr_latency"]) == 1
        assert aggregator.measurements["asr_latency"][0] == 250.5
        
    @pytest.mark.asyncio
    async def test_record_unknown_stage(self):
        """Test recording measurement for unknown stage is ignored."""
        aggregator = MetricsAggregator()
        
        measurement = LatencyMeasurement(
            stage="unknown_stage",
            duration_ms=100,
            timestamp=datetime.now(),
            session_id="session-123"
        )
        
        await aggregator.record(measurement)
        
        # Should not create new stage
        assert "unknown_stage" not in aggregator.measurements or \
               len(aggregator.measurements.get("unknown_stage", [])) == 0
               
    @pytest.mark.asyncio
    async def test_keep_last_1000_measurements(self):
        """Test that only last 1000 measurements are kept per stage."""
        aggregator = MetricsAggregator()
        
        # Add 1100 measurements
        for i in range(1100):
            measurement = LatencyMeasurement(
                stage="asr_latency",
                duration_ms=float(i),
                timestamp=datetime.now(),
                session_id=f"session-{i}"
            )
            await aggregator.record(measurement)
            
        # Should only keep last 1000
        assert len(aggregator.measurements["asr_latency"]) == 1000
        # Should have the most recent ones (100-1099)
        assert aggregator.measurements["asr_latency"][0] == 100.0
        assert aggregator.measurements["asr_latency"][-1] == 1099.0
        
    def test_get_statistics_empty(self):
        """Test getting statistics for empty stage."""
        aggregator = MetricsAggregator()
        
        stats = aggregator.get_statistics("asr_latency")
        assert stats == {}
        
    @pytest.mark.asyncio
    async def test_get_statistics(self):
        """Test calculating statistics."""
        aggregator = MetricsAggregator()
        
        # Add measurements: 100, 200, 300, 400, 500
        for value in [100, 200, 300, 400, 500]:
            measurement = LatencyMeasurement(
                stage="asr_latency",
                duration_ms=float(value),
                timestamp=datetime.now(),
                session_id="session-123"
            )
            await aggregator.record(measurement)
            
        stats = aggregator.get_statistics("asr_latency")
        
        assert stats["count"] == 5
        assert stats["mean"] == 300.0
        assert stats["median"] == 300.0
        assert stats["min"] == 100.0
        assert stats["max"] == 500.0
        assert stats["p95"] == 500.0  # 95th percentile of 5 items
        assert stats["p99"] == 500.0  # 99th percentile of 5 items
        
    @pytest.mark.asyncio
    async def test_percentile_calculation(self):
        """Test percentile calculation with more data."""
        aggregator = MetricsAggregator()
        
        # Add 100 measurements from 1 to 100
        for value in range(1, 101):
            measurement = LatencyMeasurement(
                stage="asr_latency",
                duration_ms=float(value),
                timestamp=datetime.now(),
                session_id="session-123"
            )
            await aggregator.record(measurement)
            
        stats = aggregator.get_statistics("asr_latency")
        
        assert stats["count"] == 100
        assert stats["mean"] == 50.5
        assert stats["median"] == 50.5
        # p95 at index 95 (int(100 * 0.95)) gives us value at position 95, which is 96
        assert stats["p95"] == 96.0  # 95th percentile
        # p99 at index 99 (int(100 * 0.99)) gives us value at position 99, which is 100
        assert stats["p99"] == 100.0  # 99th percentile
        
    @pytest.mark.asyncio
    async def test_get_all_statistics(self):
        """Test getting statistics for all stages."""
        aggregator = MetricsAggregator()
        
        # Add measurements to multiple stages
        for stage in ["asr_latency", "tts_latency"]:
            measurement = LatencyMeasurement(
                stage=stage,
                duration_ms=100.0,
                timestamp=datetime.now(),
                session_id="session-123"
            )
            await aggregator.record(measurement)
            
        all_stats = aggregator.get_all_statistics()
        
        # Should have stats for all stages (even empty ones)
        assert "asr_latency" in all_stats
        assert "tts_latency" in all_stats
        assert "llm_first_token_latency" in all_stats
        
        # Non-empty stages should have statistics
        assert all_stats["asr_latency"]["count"] == 1
        assert all_stats["tts_latency"]["count"] == 1
        
        # Empty stages should return empty dict
        assert all_stats["llm_first_token_latency"] == {}


class TestLatencyBudget:
    """Tests for LatencyBudget dataclass."""
    
    def test_default_values(self):
        """Test default budget values."""
        budget = LatencyBudget()
        
        assert budget.asr_latency_ms == 500
        assert budget.llm_first_token_ms == 300
        assert budget.tts_latency_ms == 400
        assert budget.end_to_end_ms == 2000
        
    def test_custom_values(self):
        """Test custom budget values."""
        budget = LatencyBudget(
            asr_latency_ms=600,
            llm_first_token_ms=400,
            tts_latency_ms=500,
            end_to_end_ms=2500
        )
        
        assert budget.asr_latency_ms == 600
        assert budget.llm_first_token_ms == 400
        assert budget.tts_latency_ms == 500
        assert budget.end_to_end_ms == 2500


class TestLatencyMonitor:
    """Tests for LatencyMonitor class."""
    
    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test LatencyMonitor initialization."""
        budget = LatencyBudget()
        aggregator = MetricsAggregator()
        monitor = LatencyMonitor(budget, aggregator)
        
        assert monitor.budget == budget
        assert monitor.aggregator == aggregator
        assert len(monitor.violations) == 0
        
    @pytest.mark.asyncio
    async def test_check_measurement_within_budget(self):
        """Test checking measurement within budget."""
        budget = LatencyBudget()
        aggregator = MetricsAggregator()
        monitor = LatencyMonitor(budget, aggregator)
        
        measurement = LatencyMeasurement(
            stage="asr_latency",
            duration_ms=250.0,  # Under 500ms budget
            timestamp=datetime.now(),
            session_id="session-123"
        )
        
        result = monitor.check_measurement(measurement)
        
        assert result is True
        assert len(monitor.violations) == 0
        
    @pytest.mark.asyncio
    async def test_check_measurement_exceeds_budget(self):
        """Test checking measurement that exceeds budget."""
        budget = LatencyBudget()
        aggregator = MetricsAggregator()
        monitor = LatencyMonitor(budget, aggregator)
        
        measurement = LatencyMeasurement(
            stage="asr_latency",
            duration_ms=750.0,  # Exceeds 500ms budget
            timestamp=datetime.now(),
            session_id="session-123"
        )
        
        result = monitor.check_measurement(measurement)
        
        assert result is False
        assert len(monitor.violations) == 1
        
        violation = monitor.violations[0]
        assert violation["stage"] == "asr_latency"
        assert violation["duration_ms"] == 750.0
        assert violation["threshold_ms"] == 500
        assert violation["session_id"] == "session-123"
        
    @pytest.mark.asyncio
    async def test_check_measurement_unknown_stage(self):
        """Test checking measurement for stage without budget."""
        budget = LatencyBudget()
        aggregator = MetricsAggregator()
        monitor = LatencyMonitor(budget, aggregator)
        
        measurement = LatencyMeasurement(
            stage="unknown_stage",
            duration_ms=1000.0,
            timestamp=datetime.now(),
            session_id="session-123"
        )
        
        result = monitor.check_measurement(measurement)
        
        # Should return True (no budget to violate)
        assert result is True
        assert len(monitor.violations) == 0
        
    @pytest.mark.asyncio
    async def test_get_violation_rate_no_measurements(self):
        """Test violation rate with no measurements."""
        budget = LatencyBudget()
        aggregator = MetricsAggregator()
        monitor = LatencyMonitor(budget, aggregator)
        
        rate = monitor.get_violation_rate("asr_latency")
        assert rate == 0.0
        
    @pytest.mark.asyncio
    async def test_get_violation_rate(self):
        """Test calculating violation rate."""
        budget = LatencyBudget()
        aggregator = MetricsAggregator()
        monitor = LatencyMonitor(budget, aggregator)
        
        # Add 10 measurements, 3 exceed budget
        for i in range(10):
            duration = 600.0 if i < 3 else 400.0  # First 3 exceed 500ms budget
            measurement = LatencyMeasurement(
                stage="asr_latency",
                duration_ms=duration,
                timestamp=datetime.now(),
                session_id=f"session-{i}"
            )
            
            await aggregator.record(measurement)
            monitor.check_measurement(measurement)
            
        rate = monitor.get_violation_rate("asr_latency")
        
        # 3 violations out of 10 measurements = 30%
        assert rate == 30.0
        
    @pytest.mark.asyncio
    async def test_multiple_stage_violations(self):
        """Test tracking violations across multiple stages."""
        budget = LatencyBudget()
        aggregator = MetricsAggregator()
        monitor = LatencyMonitor(budget, aggregator)
        
        # Add violations to different stages
        measurements = [
            LatencyMeasurement("asr_latency", 600.0, datetime.now(), "s1"),
            LatencyMeasurement("llm_first_token_latency", 400.0, datetime.now(), "s2"),
            LatencyMeasurement("tts_latency", 500.0, datetime.now(), "s3"),
        ]
        
        for m in measurements:
            await aggregator.record(m)
            monitor.check_measurement(m)
            
        # All three should violate their budgets
        assert len(monitor.violations) == 3
        
        # Check violation rates
        assert monitor.get_violation_rate("asr_latency") == 100.0
        assert monitor.get_violation_rate("llm_first_token_latency") == 100.0
        assert monitor.get_violation_rate("tts_latency") == 100.0
