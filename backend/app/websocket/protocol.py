"""
LSP Protocol implementation for WebSocket communication.
"""
import json
from typing import Any, Dict, Optional

from ..core import logger
from ..models import LSPRequest, LSPResponse


class LSPProtocol:
    """
    Handles LSP protocol message parsing and serialization.
    """
    
    JSONRPC_VERSION = "2.0"
    
    @staticmethod
    def parse_message(data: str) -> Optional[LSPRequest]:
        """
        Parse incoming WebSocket message to LSP request.
        
        Args:
            data: Raw JSON string.
            
        Returns:
            LSPRequest or None if parsing fails.
        """
        try:
            message = json.loads(data)
            
            # Validate JSON-RPC version
            if message.get("jsonrpc") != LSPProtocol.JSONRPC_VERSION:
                logger.warning(f"Invalid JSON-RPC version: {message.get('jsonrpc')}")
            
            return LSPRequest(
                jsonrpc=message.get("jsonrpc", LSPProtocol.JSONRPC_VERSION),
                id=message.get("id"),
                method=message.get("method", ""),
                params=message.get("params")
            )
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to parse LSP message: {e}")
            return None
    
    @staticmethod
    def serialize_response(response: LSPResponse) -> str:
        """
        Serialize LSP response to JSON string.
        
        Args:
            response: LSP response object.
            
        Returns:
            JSON string.
        """
        return response.model_dump_json(exclude_none=True)
    
    @staticmethod
    def create_notification(method: str, params: Dict[str, Any]) -> str:
        """
        Create an LSP notification message.
        
        Args:
            method: Notification method name.
            params: Notification parameters.
            
        Returns:
            JSON string.
        """
        message = {
            "jsonrpc": LSPProtocol.JSONRPC_VERSION,
            "method": method,
            "params": params
        }
        return json.dumps(message)
    
    @staticmethod
    def create_error_response(
        request_id: Optional[int],
        code: int,
        message: str,
        data: Optional[Dict] = None
    ) -> str:
        """
        Create an LSP error response.
        
        Args:
            request_id: Original request ID.
            code: Error code.
            message: Error message.
            data: Additional error data.
            
        Returns:
            JSON string.
        """
        error = {
            "code": code,
            "message": message
        }
        if data:
            error["data"] = data
        
        response = LSPResponse(
            id=request_id,
            error=error
        )
        return response.model_dump_json(exclude_none=True)
    
    @staticmethod
    def create_diagnostics_notification(uri: str, diagnostics: list) -> str:
        """
        Create a publishDiagnostics notification.
        
        Args:
            uri: Document URI.
            diagnostics: List of diagnostic objects.
            
        Returns:
            JSON string.
        """
        return LSPProtocol.create_notification(
            "textDocument/publishDiagnostics",
            {
                "uri": uri,
                "diagnostics": [
                    d.model_dump() if hasattr(d, 'model_dump') else d
                    for d in diagnostics
                ]
            }
        )


__all__ = ["LSPProtocol"]
