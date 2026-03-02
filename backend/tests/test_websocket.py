"""
Unit and integration tests for WebSocket functionality.
"""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient
from fastapi.websockets import WebSocket

from app.main import app
from app.websocket.manager import ConnectionManager
from app.websocket.protocol import LSPProtocol
from app.websocket.handler import WebSocketHandler
from app.models import LSPRequest, LSPResponse


class TestConnectionManager:
    """Tests for ConnectionManager class."""
    
    @pytest.fixture
    def manager(self):
        """Create a fresh ConnectionManager instance."""
        return ConnectionManager()
    
    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket."""
        ws = AsyncMock(spec=WebSocket)
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()
        ws.close = AsyncMock()
        return ws
    
    @pytest.mark.asyncio
    async def test_connect_success(self, manager, mock_websocket):
        """Test successful connection."""
        result = await manager.connect(mock_websocket, "client-1")
        
        assert result is True
        assert manager.active_count == 1
        mock_websocket.accept.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_connect_multiple_clients(self, manager, mock_websocket):
        """Test connecting multiple clients."""
        ws1 = AsyncMock(spec=WebSocket)
        ws1.accept = AsyncMock()
        ws2 = AsyncMock(spec=WebSocket)
        ws2.accept = AsyncMock()
        
        await manager.connect(ws1, "client-1")
        await manager.connect(ws2, "client-2")
        
        assert manager.active_count == 2
    
    @pytest.mark.asyncio
    async def test_disconnect(self, manager, mock_websocket):
        """Test disconnection."""
        await manager.connect(mock_websocket, "client-1")
        assert manager.active_count == 1
        
        await manager.disconnect("client-1")
        assert manager.active_count == 0
    
    @pytest.mark.asyncio
    async def test_disconnect_nonexistent(self, manager):
        """Test disconnecting non-existent client."""
        # Should not raise
        await manager.disconnect("nonexistent")
        assert manager.active_count == 0
    
    @pytest.mark.asyncio
    async def test_get_connection(self, manager, mock_websocket):
        """Test getting connection by ID."""
        await manager.connect(mock_websocket, "client-1")
        
        conn = manager.get_connection("client-1")
        assert conn == mock_websocket
        
        conn = manager.get_connection("nonexistent")
        assert conn is None
    
    @pytest.mark.asyncio
    async def test_send_message(self, manager):
        """Test sending message to client."""
        ws = MagicMock()
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()
        
        await manager.connect(ws, "client-1")
        
        # Verify connection exists
        assert manager.get_connection("client-1") is not None
        
        message = {"test": "data"}
        result = await manager.send_message("client-1", message)
        
        assert result is True
        ws.send_json.assert_called_once_with(message)
    
    @pytest.mark.asyncio
    async def test_send_message_nonexistent(self, manager):
        """Test sending message to non-existent client."""
        result = await manager.send_message("nonexistent", {"test": "data"})
        assert result is False
    
    @pytest.mark.asyncio
    async def test_broadcast(self, manager):
        """Test broadcasting to all clients."""
        ws1 = MagicMock()
        ws1.accept = AsyncMock()
        ws1.send_json = AsyncMock()
        ws2 = MagicMock()
        ws2.accept = AsyncMock()
        ws2.send_json = AsyncMock()
        
        await manager.connect(ws1, "client-1")
        await manager.connect(ws2, "client-2")
        
        message = {"broadcast": "test"}
        count = await manager.broadcast(message)
        
        assert count == 2
        ws1.send_json.assert_called_once_with(message)
        ws2.send_json.assert_called_once_with(message)
    
    @pytest.mark.asyncio
    async def test_broadcast_with_exclude(self, manager):
        """Test broadcasting with exclusion."""
        ws1 = MagicMock()
        ws1.accept = AsyncMock()
        ws1.send_json = AsyncMock()
        ws2 = MagicMock()
        ws2.accept = AsyncMock()
        ws2.send_json = AsyncMock()
        
        await manager.connect(ws1, "client-1")
        await manager.connect(ws2, "client-2")
        
        message = {"broadcast": "test"}
        count = await manager.broadcast(message, exclude={"client-1"})
        
        assert count == 1
        ws1.send_json.assert_not_called()
        ws2.send_json.assert_called_once_with(message)
    
    @pytest.mark.asyncio
    async def test_close_all(self, manager):
        """Test closing all connections."""
        ws1 = AsyncMock(spec=WebSocket)
        ws1.accept = AsyncMock()
        ws1.close = AsyncMock()
        ws2 = AsyncMock(spec=WebSocket)
        ws2.accept = AsyncMock()
        ws2.close = AsyncMock()
        
        await manager.connect(ws1, "client-1")
        await manager.connect(ws2, "client-2")
        
        await manager.close_all()
        
        assert manager.active_count == 0
    
    def test_get_dialect_default(self, manager):
        """Test getting default dialect."""
        dialect = manager.get_dialect("nonexistent")
        assert dialect == "ansi"
    
    @pytest.mark.asyncio
    async def test_set_dialect(self, manager, mock_websocket):
        """Test setting dialect for client."""
        await manager.connect(mock_websocket, "client-1")
        
        manager.set_dialect("client-1", "sparksql")
        assert manager.get_dialect("client-1") == "sparksql"


class TestLSPProtocol:
    """Tests for LSPProtocol class."""
    
    def test_parse_message_valid(self):
        """Test parsing valid LSP message."""
        data = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "textDocument/didOpen",
            "params": {"uri": "file:///test.sql"}
        })
        
        request = LSPProtocol.parse_message(data)
        
        assert request is not None
        assert request.id == 1
        assert request.method == "textDocument/didOpen"
        assert request.params["uri"] == "file:///test.sql"
    
    def test_parse_message_invalid_json(self):
        """Test parsing invalid JSON."""
        request = LSPProtocol.parse_message("not json")
        assert request is None
    
    def test_parse_message_missing_method(self):
        """Test parsing message without method."""
        data = json.dumps({"jsonrpc": "2.0", "id": 1})
        request = LSPProtocol.parse_message(data)
        
        assert request is not None
        assert request.method == ""
    
    def test_serialize_response(self):
        """Test serializing LSP response."""
        response = LSPResponse(
            id=1,
            result={"test": "data"}
        )
        
        serialized = LSPProtocol.serialize_response(response)
        parsed = json.loads(serialized)
        
        assert parsed["jsonrpc"] == "2.0"
        assert parsed["id"] == 1
        assert parsed["result"]["test"] == "data"
    
    def test_create_notification(self):
        """Test creating notification message."""
        notification = LSPProtocol.create_notification(
            "textDocument/publishDiagnostics",
            {"uri": "file:///test.sql", "diagnostics": []}
        )
        
        parsed = json.loads(notification)
        
        assert parsed["jsonrpc"] == "2.0"
        assert parsed["method"] == "textDocument/publishDiagnostics"
        assert "id" not in parsed
    
    def test_create_error_response(self):
        """Test creating error response."""
        error = LSPProtocol.create_error_response(
            request_id=1,
            code=-32600,
            message="Invalid request"
        )
        
        parsed = json.loads(error)
        
        assert parsed["id"] == 1
        assert parsed["error"]["code"] == -32600
        assert parsed["error"]["message"] == "Invalid request"
    
    def test_create_diagnostics_notification(self):
        """Test creating diagnostics notification."""
        notification = LSPProtocol.create_diagnostics_notification(
            "file:///test.sql",
            []
        )
        
        parsed = json.loads(notification)
        
        assert parsed["method"] == "textDocument/publishDiagnostics"
        assert parsed["params"]["uri"] == "file:///test.sql"
        assert parsed["params"]["diagnostics"] == []


class TestWebSocketHandler:
    """Tests for WebSocketHandler class."""
    
    @pytest.fixture
    def handler(self):
        """Create a fresh WebSocketHandler instance."""
        return WebSocketHandler()
    
    def test_handler_initialization(self, handler):
        """Test handler initializes correctly."""
        assert handler is not None
        assert handler._protocol is not None


class TestWebSocketIntegration:
    """Integration tests for WebSocket endpoint."""
    
    def test_websocket_connection(self):
        """Test WebSocket connection establishment."""
        client = TestClient(app)
        
        with client.websocket_connect("/ws?client_id=test-client") as websocket:
            # Should receive welcome message
            data = websocket.receive_json()
            
            assert data["method"] == "initialize"
            assert "capabilities" in data["params"]
    
    def test_websocket_lint_request(self):
        """Test sending lint request via WebSocket."""
        client = TestClient(app)
        
        with client.websocket_connect("/ws?client_id=test-client") as websocket:
            # Receive welcome
            websocket.receive_json()
            
            # Send didOpen request
            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "textDocument/didOpen",
                "params": {
                    "textDocument": {
                        "uri": "file:///test.sql",
                        "languageId": "sql",
                        "text": "SELECT * FROM users"
                    }
                }
            }
            websocket.send_json(request)
            
            # Receive response
            response = websocket.receive_json()
            
            assert response["id"] == 1
            assert "result" in response
    
    def test_websocket_completion_request(self):
        """Test sending completion request via WebSocket."""
        client = TestClient(app)
        
        with client.websocket_connect("/ws?client_id=test-client") as websocket:
            # Receive welcome
            websocket.receive_json()
            
            # First open document
            open_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "textDocument/didOpen",
                "params": {
                    "textDocument": {
                        "uri": "file:///test.sql",
                        "languageId": "sql",
                        "text": "SEL"
                    }
                }
            }
            websocket.send_json(open_request)
            websocket.receive_json()
            
            # Request completion
            completion_request = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "textDocument/completion",
                "params": {
                    "textDocument": {"uri": "file:///test.sql"},
                    "position": {"line": 0, "character": 3}
                }
            }
            websocket.send_json(completion_request)
            
            response = websocket.receive_json()
            
            assert response["id"] == 2
            assert "result" in response
            assert "items" in response["result"]
    
    def test_websocket_set_dialect(self):
        """Test setting SQL dialect via WebSocket."""
        client = TestClient(app)
        
        with client.websocket_connect("/ws?client_id=test-client") as websocket:
            # Receive welcome
            websocket.receive_json()
            
            # Set dialect
            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "setDialect",
                "params": {
                    "uri": "file:///test.sql",
                    "dialect": "sparksql"
                }
            }
            websocket.send_json(request)
            
            response = websocket.receive_json()
            
            assert response["id"] == 1
            assert "result" in response


class TestHTTPEndpoints:
    """Tests for HTTP endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "SQLFluff LSP Server"
        assert data["status"] == "running"
    
    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    
    def test_dialects_endpoint(self, client):
        """Test dialects endpoint."""
        response = client.get("/dialects")
        
        assert response.status_code == 200
        data = response.json()
        assert "dialects" in data
        assert "ansi" in data["dialects"]
        assert "sparksql" in data["dialects"]
        assert "hive" in data["dialects"]
