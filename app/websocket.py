"""
WebSocket manager for real-time dashboard updates.
Handles connections and broadcasts messages to all connected clients.
"""

from fastapi import WebSocket, WebSocketDisconnect
import asyncio
import json
from datetime import datetime
from typing import List, Dict, Any
import structlog

logger = structlog.get_logger()


class DashboardWebSocketManager:
    """Manages WebSocket connections for the dashboard."""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)
        logger.info(
            "websocket_client_connected",
            clients=len(self.active_connections)
        )
    
    async def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
        logger.info(
            "websocket_client_disconnected",
            clients=len(self.active_connections)
        )
    
    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast a message to all connected clients."""
        if not self.active_connections:
            return
        
        disconnected = []
        message_with_timestamp = {
            **message,
            "timestamp": datetime.now().isoformat()
        }
        
        for connection in self.active_connections:
            try:
                await connection.send_json(message_with_timestamp)
            except Exception as e:
                logger.warning(
                    "websocket_send_failed",
                    error=str(e)
                )
                disconnected.append(connection)
        
        # Clean up disconnected clients
        async with self._lock:
            for conn in disconnected:
                if conn in self.active_connections:
                    self.active_connections.remove(conn)
    
    def get_connection_count(self) -> int:
        """Get number of active connections."""
        return len(self.active_connections)


# Global WebSocket manager instance
ws_manager = DashboardWebSocketManager()


class WebSocketMessage:
    """Helper class to create WebSocket messages."""
    
    @staticmethod
    def queue_update(stats: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "type": "queue_update",
            "data": stats
        }
    
    @staticmethod
    def baileys_status(status: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "type": "baileys_status",
            "data": status
        }
    
    @staticmethod
    def new_log(log_entry: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "type": "new_log",
            "data": log_entry
        }
    
    @staticmethod
    def message_sent(message: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "type": "message_sent",
            "data": message
        }
    
    @staticmethod
    def message_failed(message: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "type": "message_failed",
            "data": message
        }
    
    @staticmethod
    def system_alert(alert: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "type": "system_alert",
            "data": alert
        }
    
    @staticmethod
    def health_update(health: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "type": "health_update",
            "data": health
        }
