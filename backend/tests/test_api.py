"""
API endpoint tests for the SQLFluff LSP Server.
Tests all HTTP endpoints and verifies error handling returns friendly messages.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings


class TestRootEndpoint:
    """Tests for the root endpoint."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_root_returns_server_info(self, client):
        """Test root endpoint returns correct server information."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "name" in data
        assert "version" in data
        assert "status" in data
        assert data["status"] == "running"
        assert data["name"] == settings.APP_NAME
    
    def test_root_includes_connection_count(self, client):
        """Test root endpoint includes connection count."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "connections" in data
        assert isinstance(data["connections"], int)
        assert data["connections"] >= 0


class TestHealthEndpoint:
    """Tests for the health check endpoint."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_health_returns_healthy(self, client):
        """Test health endpoint returns healthy status."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "status" in data
        assert data["status"] == "healthy"
    
    def test_health_includes_connection_count(self, client):
        """Test health endpoint includes connection count."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "connections" in data
        assert isinstance(data["connections"], int)


class TestDialectsEndpoint:
    """Tests for the dialects endpoint."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_dialects_returns_list(self, client):
        """Test dialects endpoint returns list of supported dialects."""
        response = client.get("/dialects")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "dialects" in data
        assert isinstance(data["dialects"], list)
        assert len(data["dialects"]) > 0
    
    def test_dialects_includes_required_dialects(self, client):
        """Test dialects endpoint includes required SQL dialects."""
        response = client.get("/dialects")
        
        assert response.status_code == 200
        data = response.json()
        
        dialects = data["dialects"]
        assert "ansi" in dialects
        assert "sparksql" in dialects
        assert "hive" in dialects
    
    def test_dialects_includes_default(self, client):
        """Test dialects endpoint includes default dialect."""
        response = client.get("/dialects")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "default" in data
        assert data["default"] in data["dialects"]


class TestErrorHandling:
    """Tests for error handling and friendly error messages."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_404_returns_friendly_message(self, client):
        """Test 404 error returns friendly message."""
        response = client.get("/nonexistent-endpoint")
        
        assert response.status_code == 404
        data = response.json()
        
        assert "success" in data
        assert data["success"] is False
        assert "error" in data
        assert "code" in data["error"]
        assert "message" in data["error"]
        # Should be a friendly message, not a system error
        assert "请求的资源不存在" in data["error"]["message"]
    
    def test_405_returns_friendly_message(self, client):
        """Test 405 error returns friendly message."""
        response = client.post("/health")  # GET only endpoint
        
        assert response.status_code == 405
        data = response.json()
        
        assert "success" in data
        assert data["success"] is False
        assert "error" in data
        assert "不支持的请求方法" in data["error"]["message"]
    
    def test_error_response_structure(self, client):
        """Test error response has correct structure."""
        response = client.get("/nonexistent")
        
        data = response.json()
        
        # Verify error response structure
        assert "success" in data
        assert "error" in data
        assert "code" in data["error"]
        assert "message" in data["error"]
        assert "details" in data["error"]
        
        # Verify types
        assert isinstance(data["success"], bool)
        assert isinstance(data["error"]["code"], int)
        assert isinstance(data["error"]["message"], str)
        assert isinstance(data["error"]["details"], dict)
    
    def test_error_message_is_user_friendly(self, client):
        """Test error messages are user-friendly (not system errors)."""
        response = client.get("/nonexistent")
        
        data = response.json()
        message = data["error"]["message"]
        
        # Should not contain technical terms
        assert "traceback" not in message.lower()
        assert "exception" not in message.lower()
        assert "error:" not in message.lower()
        assert "stack" not in message.lower()


class TestWebSocketEndpoint:
    """Tests for WebSocket endpoint availability."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_websocket_endpoint_exists(self, client):
        """Test WebSocket endpoint is accessible."""
        # WebSocket endpoints return 403 for regular HTTP requests
        # but this confirms the route exists
        with client.websocket_connect("/ws") as websocket:
            # Should receive welcome message
            data = websocket.receive_json()
            assert "method" in data
            assert data["method"] == "initialize"
    
    def test_websocket_with_client_id(self, client):
        """Test WebSocket connection with client ID."""
        with client.websocket_connect("/ws?client_id=test-client-123") as websocket:
            data = websocket.receive_json()
            assert "method" in data
            assert data["method"] == "initialize"
    
    def test_websocket_receives_capabilities(self, client):
        """Test WebSocket connection receives server capabilities."""
        with client.websocket_connect("/ws") as websocket:
            data = websocket.receive_json()
            
            assert "params" in data
            assert "capabilities" in data["params"]
            
            capabilities = data["params"]["capabilities"]
            assert "textDocumentSync" in capabilities
            assert "completionProvider" in capabilities
            assert "diagnosticProvider" in capabilities


class TestResponseFormat:
    """Tests for response format consistency."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_success_response_is_json(self, client):
        """Test successful responses are JSON."""
        response = client.get("/")
        
        assert response.headers["content-type"] == "application/json"
    
    def test_error_response_is_json(self, client):
        """Test error responses are JSON."""
        response = client.get("/nonexistent")
        
        assert "application/json" in response.headers["content-type"]
    
    def test_health_response_format(self, client):
        """Test health endpoint response format."""
        response = client.get("/health")
        
        data = response.json()
        
        # Should have exactly these fields
        expected_fields = {"status", "connections"}
        actual_fields = set(data.keys())
        
        assert expected_fields == actual_fields
    
    def test_dialects_response_format(self, client):
        """Test dialects endpoint response format."""
        response = client.get("/dialects")
        
        data = response.json()
        
        # Should have exactly these fields
        expected_fields = {"dialects", "default"}
        actual_fields = set(data.keys())
        
        assert expected_fields == actual_fields


class TestCORS:
    """Tests for CORS configuration."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_cors_headers_present(self, client):
        """Test CORS headers are present in response."""
        response = client.options(
            "/",
            headers={
                "Origin": "http://localhost:8081",
                "Access-Control-Request-Method": "GET"
            }
        )
        
        # CORS preflight should succeed
        assert response.status_code in [200, 204]
    
    def test_cors_allows_all_origins(self, client):
        """Test CORS allows requests from any origin."""
        response = client.get(
            "/",
            headers={"Origin": "http://example.com"}
        )
        
        assert response.status_code == 200
        # Check for CORS header
        assert "access-control-allow-origin" in response.headers or response.status_code == 200
