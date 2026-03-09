"""
Metrics dashboard HTTP server for the real-time voice assistant.

This module provides a web interface for viewing latency statistics and
monitoring system performance through HTTP endpoints.
"""

from aiohttp import web
from typing import Optional
from src.observability.latency import MetricsAggregator, LatencyMonitor


class MetricsDashboard:
    """HTTP server exposing latency metrics via web interface.
    
    The MetricsDashboard provides two endpoints:
    - /metrics: JSON API returning statistical data
    - /dashboard: HTML page with auto-refreshing metrics display
    """
    
    def __init__(self, aggregator: MetricsAggregator, monitor: LatencyMonitor):
        """Initialize metrics dashboard.
        
        Args:
            aggregator: MetricsAggregator instance for accessing statistics
            monitor: LatencyMonitor instance for violation rates
        """
        self.aggregator = aggregator
        self.monitor = monitor
        self.app = web.Application()
        self.app.router.add_get('/metrics', self.handle_metrics)
        self.app.router.add_get('/dashboard', self.handle_dashboard)
        self.runner: Optional[web.AppRunner] = None
        
    async def start(self, host: str = '0.0.0.0', port: int = 8001) -> None:
        """Start the metrics HTTP server.
        
        Args:
            host: Host address to bind to (default: 0.0.0.0)
            port: Port number to listen on (default: 8001)
        """
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, host, port)
        await site.start()
        
    async def handle_metrics(self, request: web.Request) -> web.Response:
        """Return JSON metrics endpoint.
        
        Args:
            request: The HTTP request object
            
        Returns:
            JSON response containing statistics for all pipeline stages
        """
        stats = self.aggregator.get_all_statistics()
        
        # Add violation rates to each stage
        for stage in stats.keys():
            stats[stage]["violation_rate"] = self.monitor.get_violation_rate(stage)
            
        return web.json_response(stats)
        
    async def handle_dashboard(self, request: web.Request) -> web.Response:
        """Return HTML dashboard endpoint.
        
        Args:
            request: The HTTP request object
            
        Returns:
            HTML response with auto-refreshing metrics display
        """
        html = self._generate_dashboard_html()
        return web.Response(text=html, content_type='text/html')
        
    def _generate_dashboard_html(self) -> str:
        """Generate simple HTML dashboard with auto-refresh.
        
        The dashboard automatically refreshes every 5 seconds and displays
        latency statistics with color-coded violation rates.
        
        Returns:
            Complete HTML page as a string
        """
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Voice Assistant Metrics</title>
            <meta http-equiv="refresh" content="5">
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .metric { margin: 20px 0; padding: 15px; border: 1px solid #ddd; }
                .metric h3 { margin-top: 0; }
                .violation { color: red; font-weight: bold; }
                .ok { color: green; }
            </style>
        </head>
        <body>
            <h1>Real-Time Voice Assistant Metrics</h1>
            <div id="metrics">Loading...</div>
            <script>
                fetch('/metrics')
                    .then(r => r.json())
                    .then(data => {
                        let html = '';
                        for (const [stage, stats] of Object.entries(data)) {
                            const violation = stats.violation_rate > 10;
                            html += `
                                <div class="metric">
                                    <h3>${stage}</h3>
                                    <p>Mean: ${stats.mean?.toFixed(2)}ms</p>
                                    <p>P95: ${stats.p95?.toFixed(2)}ms</p>
                                    <p>P99: ${stats.p99?.toFixed(2)}ms</p>
                                    <p class="${violation ? 'violation' : 'ok'}">
                                        Violation Rate: ${stats.violation_rate?.toFixed(1)}%
                                    </p>
                                </div>
                            `;
                        }
                        document.getElementById('metrics').innerHTML = html;
                    });
            </script>
        </body>
        </html>
        """
