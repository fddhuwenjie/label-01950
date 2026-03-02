"""
WebSocket connection manager for handling multiple clients.
"""
import asyncio
from typing import Dict, Set
from fastapi import WebSocket

from ..core import logger
from ..config import settings


class ConnectionManager:
    """
    Manages WebSocket connections with support for multiple clients.
    """
    
    def __init__(self):
        self._active_connections: Dict[str, WebSocket] = {}
        self._connection_dialects: Dict[str, str] = {}
        self._lock = asyncio.Lock()
        logger.info("ConnectionManager initialized")
    
    @property
    def active_count(self) -> int:
        """Get number of active connections."""
        return len(self._active_connections)
    
    async def connect(self, websocket: WebSocket, client_id: str) -> bool:
        """
        Accept a new WebSocket connection.
        
        Args:
            websocket: WebSocket instance.
            client_id: Unique client identifier.
            
        Returns:
            True if connection accepted, False if limit reached.
        """
        async with self._lock:
            if len(self._active_connections) >= settings.WS_MAX_CONNECTIONS:
                logger.warning(f"Connection limit reached, rejecting {client_id}")
                return False
            
            await websocket.accept()
            self._active_connections[client_id] = websocket
            self._connection_dialects[client_id] = settings.DEFAULT_DIALECT
            
            logger.info(f"Client connected: {client_id} (total: {self.active_count})")
            return True
    
    async def disconnect(self, client_id: str) -> None:
        """
        Remove a WebSocket connection.
        
        Args:
            client_id: Client identifier to disconnect.
        """
        async with self._lock:
            if client_id in self._active_connections:
                del self._active_connections[client_id]
                self._connection_dialects.pop(client_id, None)
                logger.info(f"Client disconnected: {client_id} (total: {self.active_count})")
    
    def get_connection(self, client_id: str) -> WebSocket:
        """
        Get WebSocket connection by client ID.
        
        Args:
            client_id: Client identifier.
            
        Returns:
            WebSocket instance or None.
        """
        return self._active_connections.get(client_id)
    
    def get_dialect(self, client_id: str) -> str:
        """Get dialect for a client."""
        return self._connection_dialects.get(client_id, settings.DEFAULT_DIALECT)
    
    def set_dialect(self, client_id: str, dialect: str) -> None:
        """Set dialect for a client."""
        if client_id in self._connection_dialects:
            self._connection_dialects[client_id] = dialect
            logger.debug(f"Set dialect for {client_id}: {dialect}")
    
    async def send_message(self, client_id: str, message: dict) -> bool:
        """
        Send a message to a specific client.
        
        Args:
            client_id: Target client identifier.
            message: Message to send.
            
        Returns:
            True if sent successfully, False otherwise.
        """
        websocket = self._active_connections.get(client_id)
        if websocket:
            try:
                await websocket.send_json(message)
                return True
            except Exception as e:
                logger.error(f"Failed to send message to {client_id}: {e}")
                await self.disconnect(client_id)
        return False
    
    async def broadcast(self, message: dict, exclude: Set[str] = None) -> int:
        """
        Broadcast a message to all connected clients.
        
        Args:
            message: Message to broadcast.
            exclude: Set of client IDs to exclude.
            
        Returns:
            Number of clients message was sent to.
        """
        exclude = exclude or set()
        sent_count = 0
        
        for client_id in list(self._active_connections.keys()):
            if client_id not in exclude:
                if await self.send_message(client_id, message):
                    sent_count += 1
        
        return sent_count
    
    async def close_all(self) -> None:
        """Close all active connections."""
        for client_id in list(self._active_connections.keys()):
            websocket = self._active_connections.get(client_id)
            if websocket:
                try:
                    await websocket.close()
                except Exception:
                    pass
            await self.disconnect(client_id)
        
        logger.info("All connections closed")


# Singleton instance
connection_manager = ConnectionManager()


__all__ = ["ConnectionManager", "connection_manager"]
