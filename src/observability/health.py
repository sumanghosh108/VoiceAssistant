"""
System health tracking and degradation monitoring.

This module provides the SystemHealth class for tracking the health status of
system components and determining overall system health.
"""

from datetime import datetime
from typing import Any, Dict

from src.utils.logger import logger


class SystemHealth:
    """Tracks system health and degradation state"""
    
    def __init__(self):
        """Initialize system health tracker with all components healthy."""
        self.components = {
            "asr": True,
            "llm": True,
            "tts": True,
            "latency_tracker": True,
            "recorder": True,
            "dashboard": True
        }
        self.degraded_since: Dict[str, datetime] = {}
        
    def mark_degraded(self, component: str, reason: str) -> None:
        """
        Mark component as degraded.
        
        Args:
            component: Name of the component to mark as degraded
            reason: Reason for degradation
        """
        if self.components.get(component, False):
            self.components[component] = False
            self.degraded_since[component] = datetime.now()
            
            logger.warning(
                f"Component {component} degraded: {reason}",
                component=component,
                reason=reason,
                degraded_at=datetime.now().isoformat()
            )
            
    def mark_healthy(self, component: str) -> None:
        """
        Mark component as healthy.
        
        Args:
            component: Name of the component to mark as healthy
        """
        if not self.components.get(component, True):
            self.components[component] = True
            if component in self.degraded_since:
                duration = datetime.now() - self.degraded_since[component]
                del self.degraded_since[component]
                
                logger.info(
                    f"Component {component} recovered after {duration.total_seconds()}s",
                    component=component,
                    degraded_duration_seconds=duration.total_seconds()
                )
                
    def is_critical_healthy(self) -> bool:
        """
        Check if critical components are healthy.
        
        Critical components are: ASR, LLM, TTS
        
        Returns:
            True if all critical components are healthy, False otherwise
        """
        critical = ["asr", "llm", "tts"]
        return all(self.components.get(c, False) for c in critical)
        
    def is_fully_healthy(self) -> bool:
        """
        Check if all components are healthy.
        
        Returns:
            True if all components are healthy, False otherwise
        """
        return all(self.components.values())
        
    def get_status(self) -> Dict[str, Any]:
        """
        Get current health status.
        
        Returns:
            Dictionary containing:
                - healthy: Whether all components are healthy
                - critical_healthy: Whether critical components are healthy
                - components: Health status of each component
                - degraded_since: Timestamps when components became degraded
        """
        return {
            "healthy": self.is_fully_healthy(),
            "critical_healthy": self.is_critical_healthy(),
            "components": self.components.copy(),
            "degraded_since": {
                k: v.isoformat() for k, v in self.degraded_since.items()
            }
        }


from aiohttp import web
from typing import Dict

from src.infrastructure.resilience import CircuitBreaker, CircuitState


class HealthCheckServer:
    """HTTP server for health check endpoints"""
    
    def __init__(
        self,
        system_health: SystemHealth,
        circuit_breakers: Dict[str, CircuitBreaker]
    ):
        """
        Initialize health check server.
        
        Args:
            system_health: SystemHealth instance for tracking component health
            circuit_breakers: Dictionary mapping service names to CircuitBreaker instances
        """
        self.system_health = system_health
        self.circuit_breakers = circuit_breakers
        self.app = web.Application()
        
        # Register routes
        self.app.router.add_get('/health', self.handle_health)
        self.app.router.add_get('/health/ready', self.handle_ready)
        self.app.router.add_get('/health/live', self.handle_live)
        
    async def handle_health(self, request: web.Request) -> web.Response:
        """
        Detailed health status endpoint.
        
        Returns HTTP 200 when healthy, HTTP 503 when degraded.
        Includes status for each component and circuit breaker states.
        
        Args:
            request: aiohttp request object
            
        Returns:
            JSON response with detailed health status
        """
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
        """
        Readiness probe endpoint for Kubernetes-style orchestration.
        
        Returns HTTP 200 when ready to accept connections, HTTP 503 when not ready.
        Checks critical components (ASR, LLM, TTS) and circuit breaker states.
        
        Args:
            request: aiohttp request object
            
        Returns:
            JSON response with readiness status
        """
        is_ready = self.system_health.is_critical_healthy()
        
        # Check circuit breakers - system is not ready if any circuit is open
        all_circuits_ok = all(
            cb.state != CircuitState.OPEN
            for cb in self.circuit_breakers.values()
        )
        
        if is_ready and all_circuits_ok:
            return web.json_response({"status": "ready"}, status=200)
        else:
            return web.json_response({"status": "not_ready"}, status=503)
            
    async def handle_live(self, request: web.Request) -> web.Response:
        """
        Liveness probe endpoint for Kubernetes-style orchestration.
        
        Simple check that the process is alive and responding.
        Always returns HTTP 200.
        
        Args:
            request: aiohttp request object
            
        Returns:
            JSON response indicating the process is alive
        """
        return web.json_response({"status": "alive"}, status=200)
