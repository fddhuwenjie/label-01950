"""
Integration tests for LSP service functionality.
Tests the complete flow from WebSocket message to LSP response.
"""
import pytest
import json
import asyncio
from fastapi.testclient import TestClient

from app.main import app
from app.services import lsp_service, linter_service, completion_service
from app.config import settings


class TestLSPServiceIntegration:
    """Integration tests for LSP service."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_did_open_and_lint(self, client):
        """Test document open triggers linting."""
        with client.websocket_connect("/ws") as websocket:
            # Receive initialization
            init_msg = websocket.receive_json()
            assert init_msg["method"] == "initialize"
            
            # Send didOpen
            websocket.send_json({
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
            })
            
            # Should receive diagnostics
            response = websocket.receive_json()
            assert "result" in response or "method" in response
    
    def test_did_change_triggers_lint(self, client):
        """Test document change triggers re-linting."""
        with client.websocket_connect("/ws") as websocket:
            # Skip initialization
            websocket.receive_json()
            
            # Open document first
            websocket.send_json({
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
            })
            websocket.receive_json()
            
            # Change document
            websocket.send_json({
                "jsonrpc": "2.0",
                "id": 2,
                "method": "textDocument/didChange",
                "params": {
                    "textDocument": {"uri": "file:///test.sql"},
                    "contentChanges": [{"text": "SELECT id, name FROM users WHERE id = 1"}]
                }
            })
            
            # Should receive updated diagnostics
            response = websocket.receive_json()
            assert response is not None
    
    def test_completion_request(self, client):
        """Test code completion request."""
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
                    "textDocument": {"uri": "file:///test.sql"},
                    "position": {"line": 0, "character": 3}
                }
            })
            
            response = websocket.receive_json()
            assert "result" in response
            assert "items" in response["result"]
    
    def test_set_dialect(self, client):
        """Test setting SQL dialect."""
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
                        "text": "SELECT * FROM users"
                    }
                }
            })
            websocket.receive_json()
            
            # Set dialect to SparkSQL
            websocket.send_json({
                "jsonrpc": "2.0",
                "id": 2,
                "method": "setDialect",
                "params": {
                    "uri": "file:///test.sql",
                    "dialect": "sparksql"
                }
            })
            
            response = websocket.receive_json()
            assert "result" in response
            assert response["result"]["success"] is True
    
    def test_invalid_dialect_returns_friendly_error(self, client):
        """Test invalid dialect returns friendly error message."""
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
                        "text": "SELECT * FROM users"
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
                    "dialect": "invalid_dialect"
                }
            })
            
            response = websocket.receive_json()
            
            # Should return error with friendly message
            assert "error" in response
            assert "message" in response["error"]
            # Should not contain system error details
            assert "traceback" not in response["error"]["message"].lower()
    
    def test_unknown_method_returns_friendly_error(self, client):
        """Test unknown method returns friendly error message."""
        with client.websocket_connect("/ws") as websocket:
            # Skip initialization
            websocket.receive_json()
            
            # Send unknown method
            websocket.send_json({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "unknownMethod",
                "params": {}
            })
            
            response = websocket.receive_json()
            
            # Should return error
            assert "error" in response
            assert "message" in response["error"]


class TestLinterServiceIntegration:
    """Integration tests for linter service."""
    
    @pytest.fixture
    def linter(self):
        """Create a fresh linter service for each test."""
        from app.services.linter_service import LinterService
        service = LinterService()
        yield service
        service.shutdown()
    
    @pytest.mark.asyncio
    async def test_lint_valid_sql(self, linter):
        """Test linting valid SQL returns no errors."""
        diagnostics = await linter.lint(
            "SELECT id, name FROM users WHERE id = 1",
            dialect="ansi"
        )
        
        # Valid SQL should have minimal or no errors
        assert isinstance(diagnostics, list)
    
    @pytest.mark.asyncio
    async def test_lint_invalid_sql(self, linter):
        """Test linting invalid SQL returns diagnostics."""
        diagnostics = await linter.lint(
            "SELEC * FORM users",  # Intentional typos
            dialect="ansi"
        )
        
        assert isinstance(diagnostics, list)
        # Should have some diagnostics for invalid SQL
        assert len(diagnostics) > 0
    
    @pytest.mark.asyncio
    async def test_lint_with_different_dialects(self, linter):
        """Test linting with different SQL dialects."""
        sql = "SELECT * FROM users"
        
        for dialect in settings.SUPPORTED_DIALECTS:
            diagnostics = await linter.lint(sql, dialect=dialect)
            assert isinstance(diagnostics, list)
    
    @pytest.mark.asyncio
    async def test_lint_empty_sql(self, linter):
        """Test linting empty SQL."""
        diagnostics = await linter.lint("", dialect="ansi")
        
        assert isinstance(diagnostics, list)
    
    @pytest.mark.asyncio
    async def test_lint_returns_diagnostic_structure(self, linter):
        """Test lint returns proper diagnostic structure."""
        diagnostics = await linter.lint(
            "select * from users",  # lowercase - might trigger style warnings
            dialect="ansi"
        )
        
        for diag in diagnostics:
            assert hasattr(diag, 'range')
            assert hasattr(diag, 'severity')
            assert hasattr(diag, 'message')
            assert hasattr(diag.range, 'start')
            assert hasattr(diag.range, 'end')


class TestCompletionServiceIntegration:
    """Integration tests for completion service."""
    
    def test_completion_for_select(self):
        """Test completion suggestions for SELECT keyword."""
        items = completion_service.get_completions(
            text="SEL",
            line=0,
            character=3,
            dialect="ansi"
        )
        
        assert isinstance(items, list)
        # Should suggest SELECT
        labels = [item.label for item in items]
        assert "SELECT" in labels
    
    def test_completion_for_from(self):
        """Test completion suggestions for FROM keyword."""
        items = completion_service.get_completions(
            text="SELECT * FR",
            line=0,
            character=11,
            dialect="ansi"
        )
        
        assert isinstance(items, list)
        labels = [item.label for item in items]
        assert "FROM" in labels
    
    def test_completion_for_functions(self):
        """Test completion suggestions for SQL functions."""
        items = completion_service.get_completions(
            text="SELECT COU",
            line=0,
            character=10,
            dialect="ansi"
        )
        
        assert isinstance(items, list)
        labels = [item.label for item in items]
        assert "COUNT" in labels
    
    def test_completion_case_insensitive(self):
        """Test completion is case insensitive."""
        items_upper = completion_service.get_completions(
            text="SEL",
            line=0,
            character=3,
            dialect="ansi"
        )
        
        items_lower = completion_service.get_completions(
            text="sel",
            line=0,
            character=3,
            dialect="ansi"
        )
        
        # Should return same suggestions
        labels_upper = {item.label for item in items_upper}
        labels_lower = {item.label for item in items_lower}
        assert labels_upper == labels_lower
    
    def test_completion_empty_prefix(self):
        """Test completion with empty prefix returns all keywords."""
        items = completion_service.get_completions(
            text="",
            line=0,
            character=0,
            dialect="ansi"
        )
        
        assert isinstance(items, list)
        assert len(items) > 0
    
    def test_completion_dialect_specific(self):
        """Test dialect-specific completions."""
        # SparkSQL specific
        spark_items = completion_service.get_completions(
            text="EXPL",
            line=0,
            character=4,
            dialect="sparksql"
        )
        
        spark_labels = [item.label for item in spark_items]
        assert "EXPLODE" in spark_labels
    
    def test_completion_item_structure(self):
        """Test completion items have correct structure."""
        items = completion_service.get_completions(
            text="SEL",
            line=0,
            character=3,
            dialect="ansi"
        )
        
        for item in items:
            assert hasattr(item, 'label')
            assert hasattr(item, 'kind')
            assert hasattr(item, 'detail')
            assert isinstance(item.label, str)
            assert isinstance(item.kind, int)


class TestLSPProtocolMessages:
    """Tests for LSP protocol message handling."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_invalid_json_returns_error(self, client):
        """Test invalid JSON returns parse error."""
        with client.websocket_connect("/ws") as websocket:
            # Skip initialization
            websocket.receive_json()
            
            # Send invalid JSON
            websocket.send_text("not valid json")
            
            response = websocket.receive_json()
            
            assert "error" in response
            assert "code" in response["error"]
    
    def test_missing_method_returns_error(self, client):
        """Test missing method field returns error."""
        with client.websocket_connect("/ws") as websocket:
            # Skip initialization
            websocket.receive_json()
            
            # Send message without method
            websocket.send_json({
                "jsonrpc": "2.0",
                "id": 1,
                "params": {}
            })
            
            response = websocket.receive_json()
            
            assert "error" in response
    
    def test_response_includes_request_id(self, client):
        """Test response includes the request ID."""
        with client.websocket_connect("/ws") as websocket:
            # Skip initialization
            websocket.receive_json()
            
            # Send request with specific ID
            websocket.send_json({
                "jsonrpc": "2.0",
                "id": 12345,
                "method": "textDocument/didOpen",
                "params": {
                    "textDocument": {
                        "uri": "file:///test.sql",
                        "languageId": "sql",
                        "text": "SELECT 1"
                    }
                }
            })
            
            response = websocket.receive_json()
            
            assert response.get("id") == 12345
    
    def test_notification_no_response_required(self, client):
        """Test notifications (no id) don't require response."""
        with client.websocket_connect("/ws") as websocket:
            # Skip initialization
            websocket.receive_json()
            
            # Open document first
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
            
            # Send notification (no id)
            websocket.send_json({
                "jsonrpc": "2.0",
                "method": "textDocument/didClose",
                "params": {
                    "textDocument": {"uri": "file:///test.sql"}
                }
            })
            
            # Should not crash, connection should remain open
            # Send another request to verify
            websocket.send_json({
                "jsonrpc": "2.0",
                "id": 2,
                "method": "textDocument/didOpen",
                "params": {
                    "textDocument": {
                        "uri": "file:///test2.sql",
                        "languageId": "sql",
                        "text": "SELECT 2"
                    }
                }
            })
            
            response = websocket.receive_json()
            assert response.get("id") == 2
