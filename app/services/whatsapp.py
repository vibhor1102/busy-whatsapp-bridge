from abc import ABC, abstractmethod
from typing import Optional
import httpx
import structlog
from app.config import get_settings
from app.models.schemas import WhatsAppMessage, WhatsAppResponse
from app.utils.phone import normalize_phone_e164, to_wa_id

logger = structlog.get_logger()


class WhatsAppProvider(ABC):
    """Abstract base class for WhatsApp providers."""
    
    @abstractmethod
    async def send_message(self, message: WhatsAppMessage) -> WhatsAppResponse:
        """Send a WhatsApp message."""
        pass


class BaileysProvider(WhatsAppProvider):
    """Baileys WhatsApp Web integration via Node.js bridge."""
    
    def __init__(self):
        self.settings = get_settings()
        self.server_url = getattr(self.settings, 'BAILEYS_SERVER_URL', 'http://localhost:3001')
        self.server_url = self.server_url.rstrip('/')
        self.default_country_code = self.settings.WHATSAPP_DEFAULT_COUNTRY_CODE
    
    async def _check_connection(self) -> bool:
        """Check if Baileys server is connected to WhatsApp."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.server_url}/status",
                    timeout=5.0
                )
                if response.status_code == 200:
                    data = response.json()
                    return data.get("data", {}).get("state") == "connected"
        except Exception:
            pass
        return False
    
    async def send_message(self, message: WhatsAppMessage) -> WhatsAppResponse:
        """Send message via Baileys WhatsApp Web bridge."""
        try:
            is_connected = await self._check_connection()
            if not is_connected:
                raise ValueError(
                    "Baileys server not connected to WhatsApp. "
                    "Please scan QR code at /baileys/qr endpoint"
                )
            
            to_number = to_wa_id(message.to, self.default_country_code)
            
            if message.media_url:
                endpoint = f"{self.server_url}/send-media"
                payload = {
                    "to": to_number,
                    "mediaUrl": message.media_url,
                    "caption": message.body,
                    "mimetype": "application/pdf"
                }
                logger.info(
                    "baileys_sending_media",
                    to=message.to,
                    url=message.media_url
                )
            else:
                endpoint = f"{self.server_url}/send"
                payload = {
                    "to": to_number,
                    "message": message.body
                }
                logger.info(
                    "baileys_sending_text",
                    to=message.to
                )
            
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
                
                logger.info(
                    "baileys_message_sent",
                    to=message.to,
                    message_id=result.get("data", {}).get("messageId")
                )
                
                return WhatsAppResponse(
                    success=True,
                    message_id=result.get("data", {}).get("messageId"),
                    delivery_status="delivered",
                    normalized_to=normalize_phone_e164(message.to, self.default_country_code),
                    error=None
                )
                
        except httpx.HTTPError as e:
            logger.error("baileys_http_error", to=message.to, error=str(e))
            return WhatsAppResponse(
                success=False,
                message_id=None,
                delivery_status="failed",
                normalized_to=None,
                error=f"HTTP Error: {str(e)}"
            )
        except ValueError as e:
            logger.error("baileys_connection_error", to=message.to, error=str(e))
            return WhatsAppResponse(
                success=False,
                message_id=None,
                delivery_status="failed",
                normalized_to=None,
                error=str(e)
            )
        except Exception as e:
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
            is_connected = await self._check_connection()
            if not is_connected:
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
                    logger.info(
                        "baileys_presence_set",
                        online=online,
                        success=result.get("success")
                    )
                    return result.get("success", False)
                else:
                    logger.error(
                        "baileys_presence_failed",
                        status=response.status_code
                    )
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
            is_connected = await self._check_connection()
            if not is_connected:
                logger.warning("baileys_typing_not_connected")
                return False
            
            # Clamp duration between 1s and 30s
            duration_ms = max(1000, min(30000, duration_ms))
            
            to_number = to_wa_id(phone, self.default_country_code)
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.server_url}/typing",
                    json={
                        "to": to_number,
                        "duration": duration_ms
                    },
                    timeout=60.0  # Long timeout as this waits for duration
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(
                        "baileys_typing_sent",
                        phone=phone,
                        duration=duration_ms,
                        success=result.get("success")
                    )
                    return result.get("success", False)
                else:
                    logger.error(
                        "baileys_typing_failed",
                        phone=phone,
                        status=response.status_code
                    )
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
