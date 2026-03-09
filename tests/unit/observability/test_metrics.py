"""
Unit tests for the MetricsDashboard class.
"""

import pytest
import asyncio
from datetime import datetime
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

from src.observability.metrics import MetricsDashboard
from src.observability.latency import MetricsAggregator, LatencyMonitor, LatencyBudget, LatencyMeasurement


class TestMetricsDashboard(AioHTTPTestCase):
    """Test suite for MetricsDashboard HTTP endpoints."""
    
    async def get_application(self):
        """Create test application."""
        self.aggregator = MetricsAggregator()
        self.budget = LatencyBudget()
        self.monitor = LatencyMonitor(self.budget, self.aggregator)
        self.dashboard = MetricsDashboard(self.aggregator, self.monitor)
        return self.dashboard.app
    
    @unittest_run_loop
    async def test_metrics_endpoint_returns_json(self):
        """Test that /metrics endpoint returns JSON statistics."""
        # Add some test measurements
        measurement = LatencyMeasurement(
            stage="asr_latency",
            duration_ms=250.5,
            timestamp=datetime.now(),
            session_id="test-session"
        )
        await self.aggregator.record(measurement)
        
        # Request metrics endpoint
        resp = await self.client.request("GET", "/metrics")
        assert resp.status == 200
        
        # Verify JSON response
        data = await resp.json()
        assert isinstance(data, dict)
        assert "asr_latency" in data
        assert "mean" in data["asr_latency"]
        assert "violation_rate" in data["asr_latency"]
    
    @unittest_run_loop
    async def test_dashboard_endpoint_returns_html(self):
        """Test that /dashboard endpoint returns HTML page."""
        resp = await self.client.request("GET", "/dashboard")
        assert resp.status == 200
        
        # Verify HTML response
        content_type = resp.headers.get('Content-Type')
        assert 'text/html' in content_type
        
        html = await resp.text()
        assert '<!DOCTYPE html>' in html
        assert 'Voice Assistant Metrics' in html
        assert 'fetch(\'/metrics\')' in html
    
    @unittest_run_loop
    async def test_metrics_includes_violation_rates(self):
        """Test that metrics endpoint includes violation rates."""
        # Add measurements with some violations
        for i in range(10):
            duration = 600.0 if i < 3 else 200.0  # 3 violations out of 10
            measurement = LatencyMeasurement(
                stage="asr_latency",
                duration_ms=duration,
                timestamp=datetime.now(),
                session_id=f"test-session-{i}"
            )
            await self.aggregator.record(measurement)
            self.monitor.check_measurement(measurement)
        
        # Request metrics
        resp = await self.client.request("GET", "/metrics")
        data = await resp.json()
        
        # Verify violation rate is calculated
        assert "violation_rate" in data["asr_latency"]
        violation_rate = data["asr_latency"]["violation_rate"]
        assert violation_rate == 30.0  # 3 out of 10 = 30%
    
    @unittest_run_loop
    async def test_dashboard_html_has_auto_refresh(self):
        """Test that dashboard HTML includes auto-refresh meta tag."""
        resp = await self.client.request("GET", "/dashboard")
        html = await resp.text()
        
        # Verify auto-refresh is configured
        assert 'meta http-equiv="refresh" content="5"' in html
    
    @unittest_run_loop
    async def test_metrics_endpoint_with_empty_data(self):
        """Test that /metrics endpoint works with no measurements."""
        resp = await self.client.request("GET", "/metrics")
        assert resp.status == 200
        
        data = await resp.json()
        # Should return empty stats for all stages
        for stage_stats in data.values():
            assert stage_stats == {} or stage_stats.get("count", 0) == 0


@pytest.mark.asyncio
async def test_dashboard_start_method():
    """Test that dashboard can be started on a specific host and port."""
    aggregator = MetricsAggregator()
    budget = LatencyBudget()
    monitor = LatencyMonitor(budget, aggregator)
    dashboard = MetricsDashboard(aggregator, monitor)
    
    # Start the dashboard (using a high port to avoid conflicts)
    await dashboard.start(host='127.0.0.1', port=18001)
    
    # Verify runner was created
    assert dashboard.runner is not None
    
    # Cleanup
    await dashboard.runner.cleanup()


@pytest.mark.asyncio
async def test_dashboard_initialization():
    """Test that MetricsDashboard initializes correctly."""
    aggregator = MetricsAggregator()
    budget = LatencyBudget()
    monitor = LatencyMonitor(budget, aggregator)
    dashboard = MetricsDashboard(aggregator, monitor)
    
    # Verify dependencies are stored
    assert dashboard.aggregator is aggregator
    assert dashboard.monitor is monitor
    
    # Verify app is created with routes
    assert dashboard.app is not None
    # Check that our routes are registered (aiohttp may add additional internal routes)
    route_paths = [route.resource.canonical for route in dashboard.app.router.routes() if hasattr(route.resource, 'canonical')]
    assert '/metrics' in route_paths
    assert '/dashboard' in route_paths
