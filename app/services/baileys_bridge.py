from __future__ import annotations

from typing import Any, Dict, Optional

import httpx
import structlog

from app.config import get_settings

logger = structlog.get_logger()


class BaileysBridge:
    """Stable adapter around the local Node.js Baileys bridge."""

    def __init__(self) -> None:
        settings = get_settings()
        self.server_url = getattr(settings, "BAILEYS_SERVER_URL", "http://localhost:3001").rstrip("/")

    async def _request(self, method: str, path: str, *, json_body: Optional[Dict[str, Any]] = None, timeout: float = 10.0) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.request(method, f"{self.server_url}{path}", json=json_body, timeout=timeout)
            response.raise_for_status()
            payload = response.json()
            if isinstance(payload, dict):
                return payload
            return {"data": payload}

    async def get_status(self) -> Dict[str, Any]:
        try:
            payload = await self._request("GET", "/status", timeout=5.0)
            return payload.get("data", payload)
        except httpx.ConnectError:
            return {"state": "unreachable", "error": "Baileys server is not running"}
        except Exception as exc:
            logger.error("baileys_bridge_status_error", error=str(exc))
            return {"state": "error", "error": str(exc)}

    async def send_text(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return await self._request("POST", "/send", json_body=payload, timeout=60.0)

    async def send_media(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return await self._request("POST", "/send-media", json_body=payload, timeout=60.0)

    async def set_presence(self, online: bool) -> Dict[str, Any]:
        return await self._request("POST", "/presence", json_body={"online": online}, timeout=10.0)

    async def send_typing(self, to: str, duration_ms: int) -> Dict[str, Any]:
        return await self._request("POST", "/typing", json_body={"to": to, "duration": duration_ms}, timeout=60.0)

    async def restart(self) -> Dict[str, Any]:
        return await self._request("POST", "/restart", timeout=30.0)

    async def logout(self) -> Dict[str, Any]:
        return await self._request("POST", "/logout", timeout=10.0)


baileys_bridge = BaileysBridge()
