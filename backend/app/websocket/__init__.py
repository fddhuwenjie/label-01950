"""
WebSocket module for real-time communication.
"""
from .manager import ConnectionManager, connection_manager
from .handler import WebSocketHandler, websocket_handler
from .protocol import LSPProtocol

__all__ = [
    "ConnectionManager",
    "connection_manager",
    "WebSocketHandler",
    "websocket_handler",
    "LSPProtocol",
]
