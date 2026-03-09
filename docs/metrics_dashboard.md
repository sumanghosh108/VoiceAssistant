# Metrics Dashboard

The MetricsDashboard provides a web interface for monitoring latency statistics and system performance in real-time.

## Overview

The dashboard exposes two HTTP endpoints:
- `/metrics` - JSON API returning statistical data
- `/dashboard` - HTML page with auto-refreshing metrics display

## Features

- **Real-time Monitoring**: Dashboard auto-refreshes every 5 seconds
- **Comprehensive Statistics**: Displays mean, P95, P99 latency for each pipeline stage
- **Violation Tracking**: Highlights metrics exceeding latency budget thresholds
- **Color-coded Alerts**: Red text for violation rates > 10%, green for acceptable rates

## Usage

### Basic Setup

```python
from src.metrics_dashboard import MetricsDashboard
from src.latency import MetricsAggregator, LatencyMonitor, LatencyBudget

# Initialize components
aggregator = MetricsAggregator()
budget = LatencyBudget()
monitor = LatencyMonitor(budget, aggregator)

# Create dashboard
dashboard = MetricsDashboard(aggregator, monitor)

# Start HTTP server
await dashboard.start(host='0.0.0.0', port=8001)
```

### Accessing Metrics

**JSON API Endpoint:**
```bash
curl http://localhost:8001/metrics
```

Response format:
```json
{
  "asr_latency": {
    "count": 100,
    "mean": 285.5,
    "median": 280.0,
    "p95": 450.0,
    "p99": 490.0,
    "min": 150.0,
    "max": 500.0,
    "violation_rate": 5.0
  },
  "llm_first_token_latency": { ... },
  "tts_latency": { ... },
  "end_to_end_latency": { ... }
}
```

**HTML Dashboard:**

Open `http://localhost:8001/dashboard` in a web browser to view the visual dashboard.

## Pipeline Stages Tracked

The dashboard monitors the following pipeline stages:

1. **asr_latency** - Time from audio receipt to transcript emission
2. **llm_first_token_latency** - Time from transcript to first LLM token
3. **llm_generation_latency** - Time from first token to last token
4. **tts_latency** - Time from token receipt to audio emission
5. **end_to_end_latency** - Total time from audio input to audio output
6. **websocket_send_latency** - Network transmission time

## Latency Budgets

Default latency budgets (thresholds):
- ASR: 500ms
- LLM First Token: 300ms
- TTS: 400ms
- End-to-End: 2000ms

Measurements exceeding these thresholds are tracked as violations.

## Integration with Main Application

The dashboard is typically started alongside the main WebSocket server:

```python
# In main.py
async def main():
    # ... initialize services ...
    
    # Start metrics dashboard
    dashboard = MetricsDashboard(aggregator, monitor)
    await dashboard.start(host='0.0.0.0', port=8001)
    
    # Start WebSocket server
    await websocket_server.start(host='0.0.0.0', port=8000)
```

## Example

See `examples/metrics_dashboard_example.py` for a complete working example.

## Requirements Satisfied

This implementation satisfies the following requirements:
- **9.1**: HTTP endpoint exposing latency metrics
- **9.2**: Dashboard displaying latency breakdown by pipeline stage
- **9.3**: Auto-refresh every 5 seconds
- **9.5**: Highlight metrics exceeding latency budget thresholds

## Future Enhancements

Potential improvements for future versions:
- Time-series graphs using Chart.js or similar library
- Active session count and throughput statistics
- Historical data persistence
- Configurable refresh intervals
- Export metrics to Prometheus format
