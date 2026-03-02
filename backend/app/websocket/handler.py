"""
WebSocket message handler for processing LSP requests.
"""
import asyncio
import time
from typing import Optional

from fastapi import WebSocket, WebSocketDisconnect

from ..core import logger
from ..services import lsp_service
from ..models import LSPRequest
from .manager import connection_manager
from .protocol import LSPProtocol


class WebSocketHandler:
    """
    Handles WebSocket connections and message processing.
    """
    
    def __init__(self):
        self._protocol = LSPProtocol()
        logger.info("WebSocketHandler initialized")
    
    async def handle_connection(
        self,
        websocket: WebSocket,
        client_id: str
    ) -> None:
        """
        Handle a WebSocket connection lifecycle.
        
        Args:
            websocket: WebSocket instance.
            client_id: Unique client identifier.
        """
        # Accept connection
        if not await connection_manager.connect(websocket, client_id):
            await websocket.close(code=1013, reason="Connection limit reached")
            return
        
        try:
            # Send welcome message
            await self._send_welcome(client_id)
            
            # Message loop
            while True:
                try:
                    data = await websocket.receive_text()
                    await self._handle_message(client_id, data)
                except WebSocketDisconnect:
                    logger.info(f"Client {client_id} disconnected normally")
                    break
                except Exception as e:
                    logger.error(f"Error handling message from {client_id}: {e}")
                    await self._send_error(client_id, str(e))
        
        finally:
            await connection_manager.disconnect(client_id)
    
    async def _send_welcome(self, client_id: str) -> None:
        """Send welcome message with server capabilities."""
        welcome = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "capabilities": {
                    "textDocumentSync": 1,
                    "completionProvider": {
                        "triggerCharacters": [".", " "]
                    },
                    "diagnosticProvider": True
                },
                "serverInfo": {
                    "name": "SQLFluff LSP Server",
                    "version": "1.0.0"
                }
            }
        }
        await connection_manager.send_message(client_id, welcome)
        logger.debug(f"Sent welcome message to {client_id}")
    
    async def _handle_message(self, client_id: str, data: str) -> None:
        """
        Process incoming WebSocket message.
        
        Args:
            client_id: Client identifier.
            data: Raw message data.
        """
        start_time = time.time()
        
        # Parse message
        request = LSPProtocol.parse_message(data)
        if not request:
            await self._send_error(client_id, "Invalid message format")
            return
        
        logger.debug(f"Received {request.method} from {client_id}")
        
        # Process request
        response = await lsp_service.process_request(request)
        
        # Send response
        if response:
            response_data = response.model_dump(exclude_none=True)
            await connection_manager.send_message(client_id, response_data)
        
        # Log performance
        elapsed = (time.time() - start_time) * 1000
        logger.debug(f"Processed {request.method} in {elapsed:.2f}ms")
        
        if elapsed > 200:
            logger.warning(f"Slow response for {request.method}: {elapsed:.2f}ms")
    
    async def _send_error(self, client_id: str, message: str) -> None:
        """Send error message to client."""
        error_response = {
            "jsonrpc": "2.0",
            "error": {
                "code": -32603,
                "message": message
            }
        }
        await connection_manager.send_message(client_id, error_response)


# Singleton instance
websocket_handler = WebSocketHandler()


__all__ = ["WebSocketHandler", "websocket_handler"]
