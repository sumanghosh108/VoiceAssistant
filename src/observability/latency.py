"""
Latency tracking and monitoring system for the real-time voice assistant.

This module provides comprehensive latency instrumentation across the pipeline,
including measurement tracking, statistics aggregation, and budget monitoring.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime
import asyncio
import statistics


@dataclass
class LatencyMeasurement:
    """Single latency measurement for a pipeline stage."""
    stage: str
    duration_ms: float
    timestamp: datetime
    session_id: str


class LatencyTracker:
    """Tracks latency metrics for a single session.
    
    The LatencyTracker records timestamps for key events in the pipeline
    and calculates durations between events to measure latency at each stage.
    """
    
    def __init__(self, session_id: str):
        """Initialize latency tracker for a session.
        
        Args:
            session_id: Unique identifier for the session being tracked
        """
        self.session_id = session_id
        self.markers: Dict[str, datetime] = {}
        self.measurements: List[LatencyMeasurement] = []
        
    def mark(self, event_name: str) -> None:
        """Record timestamp for an event.
        
        Args:
            event_name: Name of the event to mark (e.g., "audio_received", "transcript_start")
        """
        self.markers[event_name] = datetime.now()
        
    def measure(self, start_event: str, end_event: str, stage_name: str) -> None:
        """Calculate and record latency between two events.
        
        Args:
            start_event: Name of the starting event marker
            end_event: Name of the ending event marker
            stage_name: Name of the pipeline stage being measured
        """
        if start_event in self.markers and end_event in self.markers:
            start = self.markers[start_event]
            end = self.markers[end_event]
            duration_ms = (end - start).total_seconds() * 1000
            
            measurement = LatencyMeasurement(
                stage=stage_name,
                duration_ms=duration_ms,
                timestamp=end,
                session_id=self.session_id
            )
            self.measurements.append(measurement)
            
    def get_measurements(self) -> List[LatencyMeasurement]:
        """Get all measurements for this session.
        
        Returns:
            Copy of the measurements list
        """
        return self.measurements.copy()


class MetricsAggregator:
    """Aggregates latency metrics across all sessions.
    
    The MetricsAggregator collects measurements from multiple sessions and
    calculates statistical summaries (mean, median, percentiles) for each
    pipeline stage.
    """
    
    def __init__(self):
        """Initialize metrics aggregator with empty measurement storage."""
        self.measurements: Dict[str, List[float]] = {
            "asr_latency": [],
            "llm_first_token_latency": [],
            "llm_generation_latency": [],
            "tts_latency": [],
            "end_to_end_latency": [],
            "websocket_send_latency": []
        }
        self.lock = asyncio.Lock()
        
    async def record(self, measurement: LatencyMeasurement) -> None:
        """Record a measurement with thread-safe access.
        
        Args:
            measurement: The latency measurement to record
        """
        async with self.lock:
            if measurement.stage in self.measurements:
                self.measurements[measurement.stage].append(measurement.duration_ms)
                
                # Keep only last 1000 measurements per stage
                if len(self.measurements[measurement.stage]) > 1000:
                    self.measurements[measurement.stage] = \
                        self.measurements[measurement.stage][-1000:]
                        
    def get_statistics(self, stage: str) -> Dict[str, float]:
        """Calculate percentile statistics for a stage.
        
        Args:
            stage: Name of the pipeline stage
            
        Returns:
            Dictionary containing count, mean, median, p95, p99, min, max
        """
        if stage not in self.measurements or not self.measurements[stage]:
            return {}
            
        data = self.measurements[stage]
        return {
            "count": len(data),
            "mean": statistics.mean(data),
            "median": statistics.median(data),
            "p95": self._percentile(data, 0.95),
            "p99": self._percentile(data, 0.99),
            "min": min(data),
            "max": max(data)
        }
        
    def _percentile(self, data: List[float], percentile: float) -> float:
        """Calculate percentile value.
        
        Args:
            data: List of numeric values
            percentile: Percentile to calculate (0.0 to 1.0)
            
        Returns:
            The value at the specified percentile
        """
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile)
        return sorted_data[min(index, len(sorted_data) - 1)]
        
    def get_all_statistics(self) -> Dict[str, Dict[str, float]]:
        """Get statistics for all stages.
        
        Returns:
            Dictionary mapping stage names to their statistics
        """
        return {
            stage: self.get_statistics(stage)
            for stage in self.measurements.keys()
        }


@dataclass
class LatencyBudget:
    """Defines acceptable latency thresholds for pipeline stages."""
    asr_latency_ms: float = 500
    llm_first_token_ms: float = 300
    tts_latency_ms: float = 400
    end_to_end_ms: float = 2000


class LatencyMonitor:
    """Monitors latency against budgets and alerts on violations.
    
    The LatencyMonitor checks measurements against defined thresholds and
    tracks violations to calculate violation rates for each stage.
    """
    
    def __init__(self, budget: LatencyBudget, aggregator: MetricsAggregator):
        """Initialize latency monitor.
        
        Args:
            budget: Latency budget thresholds
            aggregator: Metrics aggregator for accessing statistics
        """
        self.budget = budget
        self.aggregator = aggregator
        self.violations: List[Dict] = []
        
    def check_measurement(self, measurement: LatencyMeasurement) -> bool:
        """Check if measurement exceeds budget.
        
        Args:
            measurement: The latency measurement to check
            
        Returns:
            True if measurement is within budget, False if it exceeds threshold
        """
        budget_map = {
            "asr_latency": self.budget.asr_latency_ms,
            "llm_first_token_latency": self.budget.llm_first_token_ms,
            "tts_latency": self.budget.tts_latency_ms,
            "end_to_end_latency": self.budget.end_to_end_ms
        }
        
        if measurement.stage in budget_map:
            threshold = budget_map[measurement.stage]
            if measurement.duration_ms > threshold:
                self.violations.append({
                    "stage": measurement.stage,
                    "duration_ms": measurement.duration_ms,
                    "threshold_ms": threshold,
                    "timestamp": measurement.timestamp,
                    "session_id": measurement.session_id
                })
                return False
        return True
        
    def get_violation_rate(self, stage: str) -> float:
        """Calculate percentage of measurements exceeding budget.
        
        Args:
            stage: Name of the pipeline stage
            
        Returns:
            Violation rate as a percentage (0.0 to 100.0)
        """
        stats = self.aggregator.get_statistics(stage)
        if not stats or stats["count"] == 0:
            return 0.0
            
        violations = [v for v in self.violations if v["stage"] == stage]
        return (len(violations) / stats["count"]) * 100
