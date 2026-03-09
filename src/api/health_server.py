"""
Health check HTTP server.

Provides Kubernetes-style health check endpoints:
- /health: Detailed health status
- /health/ready: Readiness probe
- /health/live: Liveness probe
"""

from aiohttp import web
from typing import Dict

from src.observability.health import SystemHealth
from src.infrastructure.resilience.circuit_breaker import CircuitBreaker, CircuitState


class HealthCheckServer:
    """HTTP server for health check endpoints."""
    
    def __init__(
        self,
        system_health: SystemHealth,
        circuit_breakers: Dict[str, CircuitBreaker]
    ):
        """Initialize health check server."""
        self.system_health = system_health
        self.circuit_breakers = circuit_breakers
        self.app = web.Application()
        
        # Register routes
        self.app.router.add_get('/health', self.handle_health)
        self.app.router.add_get('/health/ready', self.handle_ready)
        self.app.router.add_get('/health/live', self.handle_live)
        
    async def handle_health(self, request: web.Request) -> web.Response:
        """Detailed health status endpoint."""
        status = self.system_health.get_status()
        
        # Add circuit breaker states
        status["circuit_breakers"] = {
            name: cb.get_state()
            for name, cb in self.circuit_breakers.items()
        }
        
        # Return 200 if healthy, 503 if degraded
        http_status = 200 if status["healthy"] else 503
        return web.json_response(status, status=http_status)
        
    async def handle_ready(self, request: web.Request) -> web.Response:
        """Readiness probe endpoint."""
        is_ready = self.system_health.is_critical_healthy()
        
        # Check circuit breakers
        all_circuits_ok = all(
            cb.state != CircuitState.OPEN
            for cb in self.circuit_breakers.values()
        )
        
        if is_ready and all_circuits_ok:
            return web.json_response({"status": "ready"}, status=200)
        else:
            return web.json_response({"status": "not_ready"}, status=503)
            
    async def handle_live(self, request: web.Request) -> web.Response:
        """Liveness probe endpoint."""
        return web.json_response({"status": "alive"}, status=200)
