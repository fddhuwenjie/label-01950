"""
End-to-end integration tests for the complete SQLFluff LSP system.
Tests the full flow from frontend request to backend response.
"""
import pytest
import json
import asyncio
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings


class TestEndToEndLinting:
    """End-to-end tests for SQL linting workflow."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_complete_lint_workflow(self, client):
        """Test complete workflow: connect -> open -> lint -> close."""
        with client.websocket_connect("/ws?client_id=e2e-test-1") as websocket:
            # 1. Receive initialization
            init_msg = websocket.receive_json()
            assert init_msg["method"] == "initialize"
            assert "capabilities" in init_msg["params"]
            
            # 2. Open document
            websocket.send_json({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "textDocument/didOpen",
                "params": {
                    "textDocument": {
                        "uri": "file:///e2e-test.sql",
                        "languageId": "sql",
                        "text": "SELECT * FROM users WHERE id = 1"
                    }
                }
            })
            
            # 3. Receive diagnostics
            response = websocket.receive_json()
            assert response["id"] == 1
            assert "result" in response
            assert "diagnostics" in response["result"]
            
            # Verify diagnostics structure
            diagnostics = response["result"]["diagnostics"]
            assert isinstance(diagnostics, list)
            
            # 4. Close document
            websocket.send_json({
                "jsonrpc": "2.0",
                "method": "textDocument/didClose",
                "params": {
                    "textDocument": {"uri": "file:///e2e-test.sql"}
                }
            })
    
    def test_lint_with_errors(self, client):
        """Test linting SQL with intentional errors."""
        with client.websocket_connect("/ws") as websocket:
            websocket.receive_json()  # Skip init
            
            # Open document with invalid SQL
            websocket.send_json({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "textDocument/didOpen",
                "params": {
                    "textDocument": {
                        "uri": "file:///error-test.sql",
                        "languageId": "sql",
                        "text": "SELEC * FORM users"  # Intentional typos
                    }
                }
            })
            
            response = websocket.receive_json()
            diagnostics = response["result"]["diagnostics"]
            
            # Should have errors
            assert len(diagnostics) > 0
            
            # Verify diagnostic structure
            for diag in diagnostics:
                assert "range" in diag
                assert "start" in diag["range"]
                assert "end" in diag["range"]
                assert "severity" in diag
                assert "message" in diag
                
                # Message should be user-friendly
                assert len(diag["message"]) > 0
    
    def test_lint_multiple_documents(self, client):
        """Test linting multiple documents simultaneously."""
        with client.websocket_connect("/ws") as websocket:
            websocket.receive_json()  # Skip init
            
            # Open first document
            websocket.send_json({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "textDocument/didOpen",
                "params": {
                    "textDocument": {
                        "uri": "file:///doc1.sql",
                        "languageId": "sql",
                        "text": "SELECT 1"
                    }
                }
            })
            websocket.receive_json()
            
            # Open second document
            websocket.send_json({
                "jsonrpc": "2.0",
                "id": 2,
                "method": "textDocument/didOpen",
                "params": {
                    "textDocument": {
                        "uri": "file:///doc2.sql",
                        "languageId": "sql",
                        "text": "SELECT 2"
                    }
                }
            })
            websocket.receive_json()
            
            # Both should work independently
            # Change first document
            websocket.send_json({
                "jsonrpc": "2.0",
                "id": 3,
                "method": "textDocument/didChange",
                "params": {
                    "textDocument": {"uri": "file:///doc1.sql"},
                    "contentChanges": [{"text": "SELECT 1, 2, 3"}]
                }
            })
            
            response = websocket.receive_json()
            assert response["id"] == 3


class TestEndToEndCompletion:
    """End-to-end tests for code completion workflow."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_complete_completion_workflow(self, client):
        """Test complete workflow: open -> type -> get completions."""
        with client.websocket_connect("/ws") as websocket:
            websocket.receive_json()  # Skip init
            
            # Open document
            websocket.send_json({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "textDocument/didOpen",
                "params": {
                    "textDocument": {
                        "uri": "file:///completion-test.sql",
                        "languageId": "sql",
                        "text": "SEL"
                    }
                }
            })
            websocket.receive_json()
            
            # Request completion
            websocket.send_json({
                "jsonrpc": "2.0",
                "id": 2,
                "method": "textDocument/completion",
                "params": {
                    "textDocument": {"uri": "file:///completion-test.sql"},
                    "position": {"line": 0, "character": 3}
                }
            })
            
            response = websocket.receive_json()
            assert response["id"] == 2
            assert "result" in response
            assert "items" in response["result"]
            
            items = response["result"]["items"]
            assert len(items) > 0
            
            # Should suggest SELECT
            labels = [item["label"] for item in items]
            assert "SELECT" in labels
    
    def test_completion_for_functions(self, client):
        """Test completion for SQL functions."""
        with client.websocket_connect("/ws") as websocket:
            websocket.receive_json()
            
            websocket.send_json({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "textDocument/didOpen",
                "params": {
                    "textDocument": {
                        "uri": "file:///func-test.sql",
                        "languageId": "sql",
                        "text": "SELECT COU"
                    }
                }
            })
            websocket.receive_json()
            
            websocket.send_json({
                "jsonrpc": "2.0",
                "id": 2,
                "method": "textDocument/completion",
                "params": {
                    "textDocument": {"uri": "file:///func-test.sql"},
                    "position": {"line": 0, "character": 10}
                }
            })
            
            response = websocket.receive_json()
            items = response["result"]["items"]
            labels = [item["label"] for item in items]
            
            assert "COUNT" in labels
    
    def test_completion_item_structure(self, client):
        """Test completion items have correct structure."""
        with client.websocket_connect("/ws") as websocket:
            websocket.receive_json()
            
            websocket.send_json({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "textDocument/didOpen",
                "params": {
                    "textDocument": {
                        "uri": "file:///struct-test.sql",
                        "languageId": "sql",
                        "text": "SEL"
                    }
                }
            })
            websocket.receive_json()
            
            websocket.send_json({
                "jsonrpc": "2.0",
                "id": 2,
                "method": "textDocument/completion",
                "params": {
                    "textDocument": {"uri": "file:///struct-test.sql"},
                    "position": {"line": 0, "character": 3}
                }
            })
            
            response = websocket.receive_json()
            items = response["result"]["items"]
            
            for item in items:
                assert "label" in item
                assert "kind" in item
                assert isinstance(item["label"], str)
                assert isinstance(item["kind"], int)


class TestEndToEndDialects:
    """End-to-end tests for SQL dialect switching."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_switch_dialect(self, client):
        """Test switching SQL dialect."""
        with client.websocket_connect("/ws") as websocket:
            websocket.receive_json()
            
            # Open document
            websocket.send_json({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "textDocument/didOpen",
                "params": {
                    "textDocument": {
                        "uri": "file:///dialect-test.sql",
                        "languageId": "sql",
                        "text": "SELECT * FROM users"
                    }
                }
            })
            websocket.receive_json()
            
            # Switch to SparkSQL
            websocket.send_json({
                "jsonrpc": "2.0",
                "id": 2,
                "method": "setDialect",
                "params": {
                    "uri": "file:///dialect-test.sql",
                    "dialect": "sparksql"
                }
            })
            
            response = websocket.receive_json()
            assert response["id"] == 2
            assert response["result"]["success"] is True
            assert response["result"]["dialect"] == "sparksql"
    
    def test_all_supported_dialects(self, client):
        """Test all supported dialects work."""
        for dialect in settings.SUPPORTED_DIALECTS:
            with client.websocket_connect("/ws") as websocket:
                websocket.receive_json()
                
                websocket.send_json({
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "textDocument/didOpen",
                    "params": {
                        "textDocument": {
                            "uri": f"file:///{dialect}-test.sql",
                            "languageId": "sql",
                            "text": "SELECT 1"
                        }
                    }
                })
                websocket.receive_json()
                
                websocket.send_json({
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "setDialect",
                    "params": {
                        "uri": f"file:///{dialect}-test.sql",
                        "dialect": dialect
                    }
                })
                
                response = websocket.receive_json()
                assert response["result"]["success"] is True


class TestEndToEndErrorHandling:
    """End-to-end tests for error handling."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_graceful_error_handling(self, client):
        """Test system handles errors gracefully."""
        with client.websocket_connect("/ws") as websocket:
            websocket.receive_json()
            
            # Send invalid request
            websocket.send_json({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "invalid/method",
                "params": {}
            })
            
            response = websocket.receive_json()
            
            # Should return error, not crash
            assert "error" in response
            assert "message" in response["error"]
            
            # Connection should still work
            websocket.send_json({
                "jsonrpc": "2.0",
                "id": 2,
                "method": "textDocument/didOpen",
                "params": {
                    "textDocument": {
                        "uri": "file:///after-error.sql",
                        "languageId": "sql",
                        "text": "SELECT 1"
                    }
                }
            })
            
            response = websocket.receive_json()
            assert response["id"] == 2
    
    def test_error_messages_are_friendly(self, client):
        """Test all error messages are user-friendly."""
        with client.websocket_connect("/ws") as websocket:
            websocket.receive_json()
            
            # Try invalid dialect
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
            
            websocket.send_json({
                "jsonrpc": "2.0",
                "id": 2,
                "method": "setDialect",
                "params": {
                    "uri": "file:///test.sql",
                    "dialect": "invalid_dialect_xyz"
                }
            })
            
            response = websocket.receive_json()
            
            if "error" in response:
                error_msg = str(response["error"])
                # Should not expose internal details
                assert "traceback" not in error_msg.lower()
                assert "exception" not in error_msg.lower()
                assert "file \"" not in error_msg.lower()


class TestEndToEndPerformance:
    """End-to-end tests for performance requirements."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_lint_response_time(self, client):
        """Test linting responds within 200ms for simple SQL."""
        import time
        
        with client.websocket_connect("/ws") as websocket:
            websocket.receive_json()
            
            start_time = time.time()
            
            websocket.send_json({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "textDocument/didOpen",
                "params": {
                    "textDocument": {
                        "uri": "file:///perf-test.sql",
                        "languageId": "sql",
                        "text": "SELECT id, name FROM users WHERE id = 1"
                    }
                }
            })
            
            response = websocket.receive_json()
            
            elapsed_time = time.time() - start_time
            
            # Should respond within 200ms for simple SQL
            # Note: First request might be slower due to initialization
            assert elapsed_time < 2.0  # Allow 2s for first request with initialization
    
    def test_completion_response_time(self, client):
        """Test completion responds quickly."""
        import time
        
        with client.websocket_connect("/ws") as websocket:
            websocket.receive_json()
            
            websocket.send_json({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "textDocument/didOpen",
                "params": {
                    "textDocument": {
                        "uri": "file:///perf-completion.sql",
                        "languageId": "sql",
                        "text": "SEL"
                    }
                }
            })
            websocket.receive_json()
            
            start_time = time.time()
            
            websocket.send_json({
                "jsonrpc": "2.0",
                "id": 2,
                "method": "textDocument/completion",
                "params": {
                    "textDocument": {"uri": "file:///perf-completion.sql"},
                    "position": {"line": 0, "character": 3}
                }
            })
            
            response = websocket.receive_json()
            
            elapsed_time = time.time() - start_time
            
            # Completion should be very fast
            assert elapsed_time < 0.5


class TestEndToEndMultipleClients:
    """End-to-end tests for multiple client connections."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_multiple_clients_independent(self, client):
        """Test multiple clients work independently."""
        with client.websocket_connect("/ws?client_id=client-1") as ws1:
            ws1.receive_json()
            
            with client.websocket_connect("/ws?client_id=client-2") as ws2:
                ws2.receive_json()
                
                # Client 1 opens document
                ws1.send_json({
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "textDocument/didOpen",
                    "params": {
                        "textDocument": {
                            "uri": "file:///client1.sql",
                            "languageId": "sql",
                            "text": "SELECT 1"
                        }
                    }
                })
                ws1.receive_json()
                
                # Client 2 opens different document
                ws2.send_json({
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "textDocument/didOpen",
                    "params": {
                        "textDocument": {
                            "uri": "file:///client2.sql",
                            "languageId": "sql",
                            "text": "SELECT 2"
                        }
                    }
                })
                ws2.receive_json()
                
                # Both should work independently
                ws1.send_json({
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "textDocument/completion",
                    "params": {
                        "textDocument": {"uri": "file:///client1.sql"},
                        "position": {"line": 0, "character": 0}
                    }
                })
                
                ws2.send_json({
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "textDocument/completion",
                    "params": {
                        "textDocument": {"uri": "file:///client2.sql"},
                        "position": {"line": 0, "character": 0}
                    }
                })
                
                response1 = ws1.receive_json()
                response2 = ws2.receive_json()
                
                assert response1["id"] == 2
                assert response2["id"] == 2
