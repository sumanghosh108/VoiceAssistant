"""
Example demonstrating the MetricsDashboard usage.

This example shows how to:
1. Create a MetricsAggregator and LatencyMonitor
2. Record some sample latency measurements
3. Start the MetricsDashboard HTTP server
4. Access the metrics via HTTP endpoints
"""

import asyncio
from datetime import datetime
from src.metrics_dashboard import MetricsDashboard
from src.latency import MetricsAggregator, LatencyMonitor, LatencyBudget, LatencyMeasurement


async def main():
    """Run the metrics dashboard example."""
    # Initialize components
    aggregator = MetricsAggregator()
    budget = LatencyBudget()
    monitor = LatencyMonitor(budget, aggregator)
    dashboard = MetricsDashboard(aggregator, monitor)
    
    # Add some sample measurements
    print("Adding sample latency measurements...")
    sample_measurements = [
        LatencyMeasurement("asr_latency", 250.5, datetime.now(), "session-1"),
        LatencyMeasurement("asr_latency", 320.0, datetime.now(), "session-2"),
        LatencyMeasurement("llm_first_token_latency", 180.0, datetime.now(), "session-1"),
        LatencyMeasurement("llm_first_token_latency", 290.0, datetime.now(), "session-2"),
        LatencyMeasurement("tts_latency", 350.0, datetime.now(), "session-1"),
        LatencyMeasurement("tts_latency", 420.0, datetime.now(), "session-2"),
        LatencyMeasurement("end_to_end_latency", 1800.0, datetime.now(), "session-1"),
        LatencyMeasurement("end_to_end_latency", 2100.0, datetime.now(), "session-2"),
    ]
    
    for measurement in sample_measurements:
        await aggregator.record(measurement)
        monitor.check_measurement(measurement)
    
    # Start the dashboard server
    print("Starting metrics dashboard on http://localhost:8001")
    await dashboard.start(host='127.0.0.1', port=8001)
    
    print("\nMetrics Dashboard is running!")
    print("- View JSON metrics: http://localhost:8001/metrics")
    print("- View HTML dashboard: http://localhost:8001/dashboard")
    print("\nPress Ctrl+C to stop...")
    
    try:
        # Keep the server running
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        if dashboard.runner:
            await dashboard.runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
