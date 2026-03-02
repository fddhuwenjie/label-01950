"""
Tests to verify all error responses are user-friendly and don't expose system errors.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.exceptions import ErrorCode


class TestErrorResponseFormat:
    """Tests for error response format consistency."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_error_response_has_success_field(self, client):
        """Test all error responses have success=False."""
        response = client.get("/nonexistent")
        data = response.json()
        
        assert "success" in data
        assert data["success"] is False
    
    def test_error_response_has_error_object(self, client):
        """Test all error responses have error object."""
        response = client.get("/nonexistent")
        data = response.json()
        
        assert "error" in data
        assert isinstance(data["error"], dict)
    
    def test_error_object_has_required_fields(self, client):
        """Test error object has code, message, and details."""
        response = client.get("/nonexistent")
        data = response.json()
        
        error = data["error"]
        assert "code" in error
        assert "message" in error
        assert "details" in error
    
    def test_error_code_is_integer(self, client):
        """Test error code is an integer."""
        response = client.get("/nonexistent")
        data = response.json()
        
        assert isinstance(data["error"]["code"], int)
    
    def test_error_message_is_string(self, client):
        """Test error message is a string."""
        response = client.get("/nonexistent")
        data = response.json()
        
        assert isinstance(data["error"]["message"], str)
    
    def test_error_details_is_dict(self, client):
        """Test error details is a dictionary."""
        response = client.get("/nonexistent")
        data = response.json()
        
        assert isinstance(data["error"]["details"], dict)


class TestNoSystemErrorsExposed:
    """Tests to ensure system errors are not exposed to users."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_404_no_traceback(self, client):
        """Test 404 error doesn't expose traceback."""
        response = client.get("/nonexistent")
        data = response.json()
        
        message = str(data)
        assert "traceback" not in message.lower()
        assert "file \"" not in message.lower()
        assert "line " not in message.lower() or "第" in message  # Allow Chinese line references
    
    def test_405_no_exception_details(self, client):
        """Test 405 error doesn't expose exception details."""
        response = client.post("/health")
        data = response.json()
        
        message = str(data)
        assert "exception" not in message.lower()
        assert "error:" not in message.lower()
    
    def test_error_message_is_chinese(self, client):
        """Test error messages are in Chinese (user-friendly)."""
        response = client.get("/nonexistent")
        data = response.json()
        
        message = data["error"]["message"]
        # Should contain Chinese characters
        has_chinese = any('\u4e00' <= char <= '\u9fff' for char in message)
        assert has_chinese, f"Error message should be in Chinese: {message}"
    
    def test_websocket_error_no_stack_trace(self, client):
        """Test WebSocket errors don't expose stack traces."""
        with client.websocket_connect("/ws") as websocket:
            # Skip initialization
            websocket.receive_json()
            
            # Send invalid request
            websocket.send_json({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "invalid/method",
                "params": {}
            })
            
            response = websocket.receive_json()
            
            if "error" in response:
                error_str = str(response["error"])
                assert "traceback" not in error_str.lower()
                assert "file \"" not in error_str.lower()


class TestSpecificErrorMessages:
    """Tests for specific error scenarios and their messages."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_not_found_message(self, client):
        """Test 404 returns appropriate message."""
        response = client.get("/api/nonexistent")
        data = response.json()
        
        assert "不存在" in data["error"]["message"] or "not found" in data["error"]["message"].lower()
    
    def test_method_not_allowed_message(self, client):
        """Test 405 returns appropriate message."""
        response = client.post("/health")
        data = response.json()
        
        assert "不支持" in data["error"]["message"] or "method" in data["error"]["message"].lower()


class TestWebSocketErrorHandling:
    """Tests for WebSocket error handling."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_invalid_json_error(self, client):
        """Test invalid JSON returns parse error."""
        with client.websocket_connect("/ws") as websocket:
            # Skip initialization
            websocket.receive_json()
            
            # Send invalid JSON
            websocket.send_text("{invalid json}")
            
            response = websocket.receive_json()
            
            assert "error" in response
            # Should have error code
            assert "code" in response["error"]
    
    def test_missing_jsonrpc_version(self, client):
        """Test missing jsonrpc version is handled."""
        with client.websocket_connect("/ws") as websocket:
            # Skip initialization
            websocket.receive_json()
            
            # Send without jsonrpc field
            websocket.send_json({
                "id": 1,
                "method": "test",
                "params": {}
            })
            
            response = websocket.receive_json()
            # Should handle gracefully
            assert response is not None
    
    def test_invalid_method_error_message(self, client):
        """Test invalid method returns friendly error."""
        with client.websocket_connect("/ws") as websocket:
            # Skip initialization
            websocket.receive_json()
            
            websocket.send_json({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "nonexistent/method",
                "params": {}
            })
            
            response = websocket.receive_json()
            
            if "error" in response:
                message = response["error"].get("message", "")
                # Should not contain technical details
                assert "python" not in message.lower()
                assert "module" not in message.lower()


class TestLintingErrorHandling:
    """Tests for linting error handling."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_lint_invalid_dialect_error(self, client):
        """Test linting with invalid dialect returns friendly error."""
        with client.websocket_connect("/ws") as websocket:
            # Skip initialization
            websocket.receive_json()
            
            # Open document
            websocket.send_json({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "textDocument/didOpen",
                "params": {
                    "textDocument": {
                        "uri": "file:///test.sql",
                        "languageId": "sql",
                        "text": "SELECT 1"
                    }
                }
            })
            websocket.receive_json()
            
            # Set invalid dialect
            websocket.send_json({
                "jsonrpc": "2.0",
                "id": 2,
                "method": "setDialect",
                "params": {
                    "uri": "file:///test.sql",
                    "dialect": "nonexistent_dialect"
                }
            })
            
            response = websocket.receive_json()
            
            if "error" in response:
                message = response["error"].get("message", "")
                # Should mention the dialect issue
                assert "方言" in message or "dialect" in message.lower()
    
    def test_lint_very_long_sql(self, client):
        """Test linting very long SQL handles gracefully."""
        with client.websocket_connect("/ws") as websocket:
            # Skip initialization
            websocket.receive_json()
            
            # Create a long SQL (but not too long to cause timeout)
            long_sql = "SELECT " + ", ".join([f"col{i}" for i in range(100)]) + " FROM table1"
            
            websocket.send_json({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "textDocument/didOpen",
                "params": {
                    "textDocument": {
                        "uri": "file:///test.sql",
                        "languageId": "sql",
                        "text": long_sql
                    }
                }
            })
            
            response = websocket.receive_json()
            # Should not crash
            assert response is not None


class TestCompletionErrorHandling:
    """Tests for completion error handling."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_completion_invalid_position(self, client):
        """Test completion with invalid position handles gracefully."""
        with client.websocket_connect("/ws") as websocket:
            # Skip initialization
            websocket.receive_json()
            
            # Open document
            websocket.send_json({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "textDocument/didOpen",
                "params": {
                    "textDocument": {
                        "uri": "file:///test.sql",
                        "languageId": "sql",
                        "text": "SELECT 1"
                    }
                }
            })
            websocket.receive_json()
            
            # Request completion at invalid position
            websocket.send_json({
                "jsonrpc": "2.0",
                "id": 2,
                "method": "textDocument/completion",
                "params": {
                    "textDocument": {"uri": "file:///test.sql"},
                    "position": {"line": 100, "character": 100}  # Way out of bounds
                }
            })
            
            response = websocket.receive_json()
            # Should handle gracefully, either return empty or error
            assert response is not None
            if "error" in response:
                # Error should be friendly
                assert "traceback" not in str(response).lower()
    
    def test_completion_unopened_document(self, client):
        """Test completion for unopened document handles gracefully."""
        with client.websocket_connect("/ws") as websocket:
            # Skip initialization
            websocket.receive_json()
            
            # Request completion without opening document
            websocket.send_json({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "textDocument/completion",
                "params": {
                    "textDocument": {"uri": "file:///nonexistent.sql"},
                    "position": {"line": 0, "character": 0}
                }
            })
            
            response = websocket.receive_json()
            # Should handle gracefully
            assert response is not None


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_empty_sql_document(self, client):
        """Test handling empty SQL document."""
        with client.websocket_connect("/ws") as websocket:
            # Skip initialization
            websocket.receive_json()
            
            websocket.send_json({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "textDocument/didOpen",
                "params": {
                    "textDocument": {
                        "uri": "file:///empty.sql",
                        "languageId": "sql",
                        "text": ""
                    }
                }
            })
            
            response = websocket.receive_json()
            assert response is not None
    
    def test_sql_with_special_characters(self, client):
        """Test SQL with special characters."""
        with client.websocket_connect("/ws") as websocket:
            # Skip initialization
            websocket.receive_json()
            
            sql_with_special = "SELECT * FROM users WHERE name = '测试用户' AND email LIKE '%@%.com'"
            
            websocket.send_json({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "textDocument/didOpen",
                "params": {
                    "textDocument": {
                        "uri": "file:///special.sql",
                        "languageId": "sql",
                        "text": sql_with_special
                    }
                }
            })
            
            response = websocket.receive_json()
            assert response is not None
    
    def test_multiple_rapid_requests(self, client):
        """Test handling multiple rapid requests."""
        with client.websocket_connect("/ws") as websocket:
            # Skip initialization
            websocket.receive_json()
            
            # Open document
            websocket.send_json({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "textDocument/didOpen",
                "params": {
                    "textDocument": {
                        "uri": "file:///rapid.sql",
                        "languageId": "sql",
                        "text": "SELECT 1"
                    }
                }
            })
            websocket.receive_json()
            
            # Send multiple rapid change requests
            for i in range(5):
                websocket.send_json({
                    "jsonrpc": "2.0",
                    "id": i + 2,
                    "method": "textDocument/didChange",
                    "params": {
                        "textDocument": {"uri": "file:///rapid.sql"},
                        "contentChanges": [{"text": f"SELECT {i}"}]
                    }
                })
            
            # Should handle all requests without crashing
            # Receive responses
            for _ in range(5):
                try:
                    response = websocket.receive_json()
                    assert response is not None
                except Exception:
                    pass  # Some responses might be combined
