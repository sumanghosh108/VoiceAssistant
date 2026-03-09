"""
Unit tests for SystemHealth class.
"""

import pytest
from datetime import datetime, timedelta
from src.observability.health import SystemHealth


class TestSystemHealth:
    """Test suite for SystemHealth class."""
    
    def test_initialization(self):
        """Test that SystemHealth initializes with all components healthy."""
        health = SystemHealth()
        
        assert health.is_fully_healthy()
        assert health.is_critical_healthy()
        assert health.components["asr"] is True
        assert health.components["llm"] is True
        assert health.components["tts"] is True
        assert health.components["latency_tracker"] is True
        assert health.components["recorder"] is True
        assert health.components["dashboard"] is True
        assert len(health.degraded_since) == 0
        
    def test_mark_degraded(self):
        """Test marking a component as degraded."""
        health = SystemHealth()
        
        health.mark_degraded("asr", "API timeout")
        
        assert health.components["asr"] is False
        assert "asr" in health.degraded_since
        assert isinstance(health.degraded_since["asr"], datetime)
        assert not health.is_fully_healthy()
        assert not health.is_critical_healthy()
        
    def test_mark_degraded_non_critical(self):
        """Test marking a non-critical component as degraded."""
        health = SystemHealth()
        
        health.mark_degraded("recorder", "Storage full")
        
        assert health.components["recorder"] is False
        assert "recorder" in health.degraded_since
        assert not health.is_fully_healthy()
        assert health.is_critical_healthy()  # Critical components still healthy
        
    def test_mark_healthy(self):
        """Test marking a degraded component as healthy."""
        health = SystemHealth()
        
        # First degrade it
        health.mark_degraded("llm", "Connection lost")
        assert health.components["llm"] is False
        assert "llm" in health.degraded_since
        
        # Then restore it
        health.mark_healthy("llm")
        assert health.components["llm"] is True
        assert "llm" not in health.degraded_since
        assert health.is_fully_healthy()
        assert health.is_critical_healthy()
        
    def test_mark_healthy_already_healthy(self):
        """Test marking an already healthy component as healthy (no-op)."""
        health = SystemHealth()
        
        # Should not raise an error
        health.mark_healthy("tts")
        assert health.components["tts"] is True
        assert health.is_fully_healthy()
        
    def test_mark_degraded_already_degraded(self):
        """Test marking an already degraded component as degraded."""
        health = SystemHealth()
        
        health.mark_degraded("tts", "First failure")
        first_time = health.degraded_since["tts"]
        
        # Mark degraded again
        health.mark_degraded("tts", "Second failure")
        
        # Should not update the timestamp
        assert health.components["tts"] is False
        assert health.degraded_since["tts"] == first_time
        
    def test_is_critical_healthy_all_critical_healthy(self):
        """Test is_critical_healthy when all critical components are healthy."""
        health = SystemHealth()
        
        # Degrade non-critical components
        health.mark_degraded("recorder", "Storage issue")
        health.mark_degraded("dashboard", "Display error")
        
        assert health.is_critical_healthy()
        assert not health.is_fully_healthy()
        
    def test_is_critical_healthy_one_critical_degraded(self):
        """Test is_critical_healthy when one critical component is degraded."""
        health = SystemHealth()
        
        health.mark_degraded("asr", "Whisper API down")
        
        assert not health.is_critical_healthy()
        
    def test_is_critical_healthy_all_critical_degraded(self):
        """Test is_critical_healthy when all critical components are degraded."""
        health = SystemHealth()
        
        health.mark_degraded("asr", "ASR failure")
        health.mark_degraded("llm", "LLM failure")
        health.mark_degraded("tts", "TTS failure")
        
        assert not health.is_critical_healthy()
        assert not health.is_fully_healthy()
        
    def test_is_fully_healthy_all_healthy(self):
        """Test is_fully_healthy when all components are healthy."""
        health = SystemHealth()
        
        assert health.is_fully_healthy()
        
    def test_is_fully_healthy_one_degraded(self):
        """Test is_fully_healthy when one component is degraded."""
        health = SystemHealth()
        
        health.mark_degraded("latency_tracker", "Metrics collection failed")
        
        assert not health.is_fully_healthy()
        
    def test_get_status_all_healthy(self):
        """Test get_status when all components are healthy."""
        health = SystemHealth()
        
        status = health.get_status()
        
        assert status["healthy"] is True
        assert status["critical_healthy"] is True
        assert all(status["components"].values())
        assert len(status["degraded_since"]) == 0
        
    def test_get_status_with_degraded_components(self):
        """Test get_status with some degraded components."""
        health = SystemHealth()
        
        health.mark_degraded("asr", "API timeout")
        health.mark_degraded("recorder", "Storage full")
        
        status = health.get_status()
        
        assert status["healthy"] is False
        assert status["critical_healthy"] is False
        assert status["components"]["asr"] is False
        assert status["components"]["recorder"] is False
        assert status["components"]["llm"] is True
        assert "asr" in status["degraded_since"]
        assert "recorder" in status["degraded_since"]
        assert isinstance(status["degraded_since"]["asr"], str)  # ISO format
        
    def test_get_status_returns_copy(self):
        """Test that get_status returns a copy, not the original dict."""
        health = SystemHealth()
        
        status1 = health.get_status()
        status1["components"]["asr"] = False  # Modify the returned dict
        
        status2 = health.get_status()
        assert status2["components"]["asr"] is True  # Original unchanged
        
    def test_multiple_components_degraded_and_recovered(self):
        """Test complex scenario with multiple components degrading and recovering."""
        health = SystemHealth()
        
        # Degrade multiple components
        health.mark_degraded("asr", "Timeout")
        health.mark_degraded("llm", "Rate limit")
        health.mark_degraded("recorder", "Disk full")
        
        assert not health.is_critical_healthy()
        assert not health.is_fully_healthy()
        assert len(health.degraded_since) == 3
        
        # Recover one critical component
        health.mark_healthy("asr")
        assert not health.is_critical_healthy()  # LLM still degraded
        assert len(health.degraded_since) == 2
        
        # Recover other critical component
        health.mark_healthy("llm")
        assert health.is_critical_healthy()  # All critical now healthy
        assert not health.is_fully_healthy()  # Recorder still degraded
        assert len(health.degraded_since) == 1
        
        # Recover last component
        health.mark_healthy("recorder")
        assert health.is_fully_healthy()
        assert health.is_critical_healthy()
        assert len(health.degraded_since) == 0
        
    def test_unknown_component_mark_degraded(self):
        """Test marking an unknown component as degraded (should be no-op)."""
        health = SystemHealth()
        
        # Should not raise an error
        health.mark_degraded("unknown_component", "Some error")
        
        # Should not affect health status
        assert health.is_fully_healthy()
        assert health.is_critical_healthy()
        
    def test_unknown_component_mark_healthy(self):
        """Test marking an unknown component as healthy (should be no-op)."""
        health = SystemHealth()
        
        # Should not raise an error
        health.mark_healthy("unknown_component")
        
        # Should not affect health status
        assert health.is_fully_healthy()
        assert health.is_critical_healthy()



class TestHealthCheckServer:
    """Test suite for HealthCheckServer class."""
    
    @pytest.fixture
    def system_health(self):
        """Create a SystemHealth instance for testing."""
        return SystemHealth()
        
    @pytest.fixture
    def circuit_breakers(self):
        """Create mock circuit breakers for testing."""
        from src.infrastructure.resilience import CircuitBreaker
        return {
            "asr": CircuitBreaker(name="asr"),
            "llm": CircuitBreaker(name="llm"),
            "tts": CircuitBreaker(name="tts")
        }
        
    @pytest.fixture
    def health_server(self, system_health, circuit_breakers):
        """Create a HealthCheckServer instance for testing."""
        from src.api.health_server import HealthCheckServer
        return HealthCheckServer(system_health, circuit_breakers)
        
    @pytest.mark.asyncio
    async def test_initialization(self, health_server):
        """Test that HealthCheckServer initializes correctly."""
        assert health_server.system_health is not None
        assert health_server.circuit_breakers is not None
        assert health_server.app is not None
        
        # Check routes are registered
        routes = [route.resource.canonical for route in health_server.app.router.routes()]
        assert '/health' in routes
        assert '/health/ready' in routes
        assert '/health/live' in routes
        
    @pytest.mark.asyncio
    async def test_handle_health_all_healthy(self, health_server):
        """Test /health endpoint when all components are healthy."""
        from aiohttp.test_utils import make_mocked_request
        
        request = make_mocked_request('GET', '/health')
        response = await health_server.handle_health(request)
        
        assert response.status == 200
        
        import json
        body = json.loads(response.body)
        assert body["healthy"] is True
        assert body["critical_healthy"] is True
        assert "circuit_breakers" in body
        assert "asr" in body["circuit_breakers"]
        assert "llm" in body["circuit_breakers"]
        assert "tts" in body["circuit_breakers"]
        
    @pytest.mark.asyncio
    async def test_handle_health_degraded(self, health_server, system_health):
        """Test /health endpoint when a component is degraded."""
        from aiohttp.test_utils import make_mocked_request
        
        # Degrade a component
        system_health.mark_degraded("asr", "Test failure")
        
        request = make_mocked_request('GET', '/health')
        response = await health_server.handle_health(request)
        
        assert response.status == 503
        
        import json
        body = json.loads(response.body)
        assert body["healthy"] is False
        assert body["critical_healthy"] is False
        assert body["components"]["asr"] is False
        
    @pytest.mark.asyncio
    async def test_handle_health_includes_circuit_breaker_states(self, health_server):
        """Test that /health endpoint includes circuit breaker states."""
        from aiohttp.test_utils import make_mocked_request
        
        request = make_mocked_request('GET', '/health')
        response = await health_server.handle_health(request)
        
        import json
        body = json.loads(response.body)
        
        assert "circuit_breakers" in body
        for name in ["asr", "llm", "tts"]:
            assert name in body["circuit_breakers"]
            cb_state = body["circuit_breakers"][name]
            assert "state" in cb_state
            assert "failures" in cb_state
            assert "successes" in cb_state
            
    @pytest.mark.asyncio
    async def test_handle_ready_all_ready(self, health_server):
        """Test /health/ready endpoint when system is ready."""
        from aiohttp.test_utils import make_mocked_request
        
        request = make_mocked_request('GET', '/health/ready')
        response = await health_server.handle_ready(request)
        
        assert response.status == 200
        
        import json
        body = json.loads(response.body)
        assert body["status"] == "ready"
        
    @pytest.mark.asyncio
    async def test_handle_ready_critical_component_degraded(self, health_server, system_health):
        """Test /health/ready endpoint when a critical component is degraded."""
        from aiohttp.test_utils import make_mocked_request
        
        # Degrade a critical component
        system_health.mark_degraded("llm", "Test failure")
        
        request = make_mocked_request('GET', '/health/ready')
        response = await health_server.handle_ready(request)
        
        assert response.status == 503
        
        import json
        body = json.loads(response.body)
        assert body["status"] == "not_ready"
        
    @pytest.mark.asyncio
    async def test_handle_ready_non_critical_component_degraded(self, health_server, system_health):
        """Test /health/ready endpoint when a non-critical component is degraded."""
        from aiohttp.test_utils import make_mocked_request
        
        # Degrade a non-critical component
        system_health.mark_degraded("recorder", "Test failure")
        
        request = make_mocked_request('GET', '/health/ready')
        response = await health_server.handle_ready(request)
        
        # Should still be ready since critical components are healthy
        assert response.status == 200
        
        import json
        body = json.loads(response.body)
        assert body["status"] == "ready"
        
    @pytest.mark.asyncio
    async def test_handle_ready_circuit_breaker_open(self, health_server, circuit_breakers):
        """Test /health/ready endpoint when a circuit breaker is open."""
        from aiohttp.test_utils import make_mocked_request
        from src.infrastructure.resilience import CircuitState
        
        # Force circuit breaker to open state
        circuit_breakers["asr"].state = CircuitState.OPEN
        
        request = make_mocked_request('GET', '/health/ready')
        response = await health_server.handle_ready(request)
        
        assert response.status == 503
        
        import json
        body = json.loads(response.body)
        assert body["status"] == "not_ready"
        
    @pytest.mark.asyncio
    async def test_handle_ready_circuit_breaker_half_open(self, health_server, circuit_breakers):
        """Test /health/ready endpoint when a circuit breaker is half-open."""
        from aiohttp.test_utils import make_mocked_request
        from src.infrastructure.resilience import CircuitState
        
        # Force circuit breaker to half-open state
        circuit_breakers["tts"].state = CircuitState.HALF_OPEN
        
        request = make_mocked_request('GET', '/health/ready')
        response = await health_server.handle_ready(request)
        
        # Half-open is acceptable (not OPEN), so should be ready
        assert response.status == 200
        
        import json
        body = json.loads(response.body)
        assert body["status"] == "ready"
        
    @pytest.mark.asyncio
    async def test_handle_live_always_returns_200(self, health_server, system_health):
        """Test /health/live endpoint always returns 200."""
        from aiohttp.test_utils import make_mocked_request
        
        # Even with degraded components
        system_health.mark_degraded("asr", "Test failure")
        system_health.mark_degraded("llm", "Test failure")
        system_health.mark_degraded("tts", "Test failure")
        
        request = make_mocked_request('GET', '/health/live')
        response = await health_server.handle_live(request)
        
        assert response.status == 200
        
        import json
        body = json.loads(response.body)
        assert body["status"] == "alive"
        
    @pytest.mark.asyncio
    async def test_handle_ready_multiple_circuit_breakers_open(self, health_server, circuit_breakers):
        """Test /health/ready endpoint when multiple circuit breakers are open."""
        from aiohttp.test_utils import make_mocked_request
        from src.infrastructure.resilience import CircuitState
        
        # Open multiple circuit breakers
        circuit_breakers["asr"].state = CircuitState.OPEN
        circuit_breakers["llm"].state = CircuitState.OPEN
        
        request = make_mocked_request('GET', '/health/ready')
        response = await health_server.handle_ready(request)
        
        assert response.status == 503
        
        import json
        body = json.loads(response.body)
        assert body["status"] == "not_ready"
        
    @pytest.mark.asyncio
    async def test_handle_health_non_critical_degraded(self, health_server, system_health):
        """Test /health endpoint when only non-critical components are degraded."""
        from aiohttp.test_utils import make_mocked_request
        
        # Degrade non-critical components
        system_health.mark_degraded("recorder", "Storage full")
        system_health.mark_degraded("dashboard", "Display error")
        
        request = make_mocked_request('GET', '/health')
        response = await health_server.handle_health(request)
        
        # Should return 503 because not fully healthy
        assert response.status == 503
        
        import json
        body = json.loads(response.body)
        assert body["healthy"] is False
        assert body["critical_healthy"] is True  # Critical components still healthy



class TestHealthCheckServerIntegration:
    """Integration tests for HealthCheckServer with actual HTTP server."""
    
    @pytest.mark.asyncio
    async def test_health_check_server_integration(self):
        """Test HealthCheckServer with actual aiohttp server."""
        from src.observability.health import SystemHealth, HealthCheckServer
        from src.infrastructure.resilience import CircuitBreaker
        from aiohttp import web
        from aiohttp.test_utils import TestClient, TestServer
        
        # Create dependencies
        system_health = SystemHealth()
        circuit_breakers = {
            "asr": CircuitBreaker(name="asr"),
            "llm": CircuitBreaker(name="llm"),
            "tts": CircuitBreaker(name="tts")
        }
        
        # Create server
        health_server = HealthCheckServer(system_health, circuit_breakers)
        
        # Test with aiohttp test client
        async with TestClient(TestServer(health_server.app)) as client:
            # Test /health endpoint
            resp = await client.get('/health')
            assert resp.status == 200
            data = await resp.json()
            assert data["healthy"] is True
            
            # Test /health/ready endpoint
            resp = await client.get('/health/ready')
            assert resp.status == 200
            data = await resp.json()
            assert data["status"] == "ready"
            
            # Test /health/live endpoint
            resp = await client.get('/health/live')
            assert resp.status == 200
            data = await resp.json()
            assert data["status"] == "alive"
            
            # Degrade a component and test again
            system_health.mark_degraded("asr", "Test failure")
            
            resp = await client.get('/health')
            assert resp.status == 503
            data = await resp.json()
            assert data["healthy"] is False
            
            resp = await client.get('/health/ready')
            assert resp.status == 503
            data = await resp.json()
            assert data["status"] == "not_ready"
            
            # /health/live should still return 200
            resp = await client.get('/health/live')
            assert resp.status == 200
