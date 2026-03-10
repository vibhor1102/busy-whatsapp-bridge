from abc import ABC, abstractmethod
from typing import Optional
import httpx
import structlog
from app.config import get_settings
from app.models.schemas import WhatsAppMessage, WhatsAppResponse
from app.services.baileys_bridge import baileys_bridge
from app.utils.phone import normalize_phone_e164, to_wa_id

logger = structlog.get_logger()


class WhatsAppProvider(ABC):
    """Abstract base class for WhatsApp providers."""
    
    @abstractmethod
    async def send_message(self, message: WhatsAppMessage) -> WhatsAppResponse:
        """Send a WhatsApp message."""
        pass

    async def get_status(self) -> dict:
        raise NotImplementedError


class BaileysProvider(WhatsAppProvider):
    """Baileys WhatsApp Web integration via Node.js bridge."""
    
    def __init__(self):
        self.settings = get_settings()
        self.server_url = getattr(self.settings, 'BAILEYS_SERVER_URL', 'http://localhost:3001')
        self.server_url = self.server_url.rstrip('/')
        self.default_country_code = self.settings.WHATSAPP_DEFAULT_COUNTRY_CODE
    
    async def _get_connection_status(self) -> dict:
        """Get current Baileys bridge health and connection status."""
        return await baileys_bridge.get_status()

    @staticmethod
    def _is_send_ready(status: dict) -> bool:
        return (
            status.get("state") == "connected"
            and not bool(status.get("isDegraded"))
            and status.get("sessionState") != "degraded"
        )

    async def _request_recovery_if_safe(self, status: dict, reason: str) -> None:
        state = (status.get("state") or "").strip().lower()
        if state in {"logged_out", "qr_ready", "connecting"}:
            return
        try:
            await baileys_bridge.restart()
            logger.warning("baileys_recovery_requested", state=state or "unknown", reason=reason)
        except Exception as exc:
            logger.warning("baileys_recovery_request_failed", state=state or "unknown", reason=reason, error=str(exc))

    async def get_status(self) -> dict:
        return await baileys_bridge.get_status()
    
    async def send_message(self, message: WhatsAppMessage) -> WhatsAppResponse:
        """Send message via Baileys WhatsApp Web bridge."""
        try:
            status = await self._get_connection_status()
            if not self._is_send_ready(status):
                if status.get("state") == "connected" and status.get("isDegraded"):
                    await self._request_recovery_if_safe(status, "send_blocked_session_degraded")
                    raise ValueError(
                        "bridge_session_degraded_retryable: Baileys session crypto state is degraded and recovery was requested"
                    )
                raise ValueError(
                    "Baileys server not connected to WhatsApp. "
                    "Please scan QR code at /baileys/qr endpoint"
                )
            
            to_number = to_wa_id(message.to, self.default_country_code)
            
            if message.media_url:
                payload = {
                    "to": to_number,
                    "mediaUrl": message.media_url,
                    "caption": message.body,
                    "mimetype": "application/pdf",
                }
                if message.file_name:
                    payload["fileName"] = message.file_name
                logger.info(
                    "baileys_sending_media",
                    to=message.to,
                    url=message.media_url,
                    file_name=message.file_name,
                )
            else:
                payload = {
                    "to": to_number,
                    "message": message.body
                }
                logger.info(
                    "baileys_sending_text",
                    to=message.to
                )
            
            endpoint = f"{self.server_url}/send-media" if message.media_url else f"{self.server_url}/send"
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    endpoint,
                    json=payload,
                    timeout=60.0
                )
                if response.status_code != 200:
                    error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                    raise ValueError(error_data.get('error', f'HTTP {response.status_code}'))
                result = response.json()
            data = result.get("data", {}) if isinstance(result, dict) else {}
            contact = data.get("contact", {}) if isinstance(data, dict) else {}
            
            logger.info(
                "baileys_message_sent",
                to=message.to,
                message_id=data.get("messageId")
            )
            
            return WhatsAppResponse(
                success=True,
                message_id=data.get("messageId"),
                delivery_status="accepted",
                normalized_to=normalize_phone_e164(message.to, self.default_country_code),
                contact_name=contact.get("name"),
                contact_source=contact.get("source"),
                contact_is_saved=contact.get("isSaved"),
                contact_state=contact.get("state"),
                error=None
            )
                
        except httpx.HTTPError as e:
            if "not connected" in str(e).lower():
                await self._request_recovery_if_safe({"state": "disconnected"}, "http_error_not_connected")
            logger.error("baileys_http_error", to=message.to, error=str(e))
            return WhatsAppResponse(
                success=False,
                message_id=None,
                delivery_status="failed",
                normalized_to=None,
                error=f"HTTP Error: {str(e)}"
            )
        except ValueError as e:
            lowered = str(e).lower()
            if "bridge_session_degraded_retryable" not in lowered and "not connected to whatsapp" in lowered:
                await self._request_recovery_if_safe(status if 'status' in locals() else {"state": "disconnected"}, "value_error_send_retryable")
            logger.error("baileys_connection_error", to=message.to, error=str(e))
            return WhatsAppResponse(
                success=False,
                message_id=None,
                delivery_status="failed",
                normalized_to=None,
                error=str(e)
            )
        except Exception as e:
            lowered = str(e).lower()
            if "bad mac" in lowered or "decrypt" in lowered or "not connected to whatsapp" in lowered:
                await self._request_recovery_if_safe(status if 'status' in locals() else {"state": "disconnected"}, "exception_send_retryable")
            logger.error("baileys_send_error", to=message.to, error=str(e))
            return WhatsAppResponse(
                success=False,
                message_id=None,
                delivery_status="failed",
                normalized_to=None,
                error=str(e)
            )
    
    async def set_presence(self, online: bool = True) -> bool:
        """Set user presence (online/offline) on WhatsApp.
        
        Args:
            online: True to set online, False for offline
            
        Returns:
            True if successful
        """
        try:
            status = await self._get_connection_status()
            if not self._is_send_ready(status):
                logger.warning("baileys_presence_not_connected")
                return False
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.server_url}/presence",
                    json={"online": online},
                    timeout=10.0
                )
                if response.status_code == 200:
                    result = response.json()
                    logger.info("baileys_presence_set", online=online, success=result.get("success"))
                    return result.get("success", False)
                logger.error("baileys_presence_failed", status=response.status_code)
                return False
                    
        except Exception as e:
            logger.error("baileys_presence_error", error=str(e))
            return False
    
    async def send_typing_indicator(self, phone: str, duration_ms: int = 5000) -> bool:
        """Send typing indicator to a chat.
        
        Args:
            phone: Phone number to send typing indicator to
            duration_ms: Duration in milliseconds to show typing (1000-30000)
            
        Returns:
            True if successful
        """
        try:
            status = await self._get_connection_status()
            if not self._is_send_ready(status):
                logger.warning("baileys_typing_not_connected")
                return False
            
            # Clamp duration between 1s and 30s
            duration_ms = max(1000, min(30000, duration_ms))
            
            to_number = to_wa_id(phone, self.default_country_code)
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.server_url}/typing",
                    json={"to": to_number, "duration": duration_ms},
                    timeout=60.0
                )
                if response.status_code == 200:
                    result = response.json()
                    logger.info("baileys_typing_sent", phone=phone, duration=duration_ms, success=result.get("success"))
                    return result.get("success", False)
                logger.error("baileys_typing_failed", phone=phone, status=response.status_code)
                return False
                    
        except Exception as e:
            logger.error("baileys_typing_error", phone=phone, error=str(e))
            return False


# =============================================================================
# REMOVED PROVIDERS (kept as comments for future reference)
# =============================================================================
# The following providers have been removed as per user request to use only
# Baileys. These can be re-integrated later when needed.
#
# TODO: Meta Cloud API integration - To be re-added via Baileys in the future
# class MetaProvider(WhatsAppProvider):
#     """Meta Business API (Facebook/WhatsApp Cloud API) integration."""
#     # Was previously used for sending via Meta Cloud API
#     # Future: Re-integrate via Baileys
#
# TODO: Evolution API integration - To be re-added later if needed
# class EvolutionProvider(WhatsAppProvider):
#     """Evolution API (WhatsApp Web) integration."""
#     # Was previously used for sending via Evolution API
#
# TODO: Webhook Provider - To be re-added later if needed
# class WebhookProvider(WhatsAppProvider):
#     """Custom webhook provider for local automation tools."""
#     # Was previously used for forwarding to custom webhook endpoints
# =============================================================================


def get_whatsapp_provider(provider_name: Optional[str] = None) -> WhatsAppProvider:
    """Factory function to get configured WhatsApp provider.
    
    NOTE: Currently only Baileys is available. Other providers (Meta, Evolution,
    Webhook) have been removed and will be re-integrated via Baileys in the future.
    """
    settings = get_settings()
    
    # Use provided name or default from settings
    provider_name = (provider_name or settings.WHATSAPP_PROVIDER).lower()
    
    # Only Baileys is available now
    # Other providers removed - will be re-added via Baileys later
    provider_map = {
        "baileys": BaileysProvider,
    }
    
    # Fallback to baileys for any provider request (backward compatibility)
    # This ensures existing code continues to work
    if provider_name not in provider_map:
        logger.warning(
            "provider_not_available_falling_back",
            requested=provider_name,
            available="baileys",
            message="Requested provider not available, using Baileys"
        )
        provider_name = "baileys"
    
    provider_class = provider_map.get(provider_name)
    if not provider_class:
        raise ValueError(f"Unknown WhatsApp provider: {provider_name}")
    
    return provider_class()
