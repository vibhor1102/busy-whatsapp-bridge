from abc import ABC, abstractmethod
from typing import Optional
import httpx
import structlog
from app.config import get_settings
from app.models.schemas import WhatsAppMessage, WhatsAppResponse

logger = structlog.get_logger()


class WhatsAppProvider(ABC):
    """Abstract base class for WhatsApp providers."""
    
    @abstractmethod
    async def send_message(self, message: WhatsAppMessage) -> WhatsAppResponse:
        """Send a WhatsApp message."""
        pass


class EvolutionProvider(WhatsAppProvider):
    """Evolution API (WhatsApp Web) integration."""
    
    def __init__(self):
        self.settings = get_settings()
        self.api_url = getattr(self.settings, 'EVOLUTION_API_URL', 'http://localhost:8080')
        self.api_key = getattr(self.settings, 'EVOLUTION_API_KEY', '')
        self.instance_name = getattr(self.settings, 'EVOLUTION_INSTANCE_NAME', 'default')
        
        # Ensure api_url doesn't end with /
        self.api_url = self.api_url.rstrip('/')
    
    async def send_message(self, message: WhatsAppMessage) -> WhatsAppResponse:
        """Send message via Evolution API."""
        try:
            if not self.api_key:
                raise ValueError("Evolution API key not configured")
            
            # Clean phone number
            to_number = message.to.replace("whatsapp:", "").replace("+", "")
            
            # Check if instance exists
            headers = {
                "apikey": self.api_key,
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient() as client:
                # Check instance status
                instance_url = f"{self.api_url}/instance/connectionState/{self.instance_name}"
                instance_response = await client.get(instance_url, headers=headers)
                instance_response.raise_for_status()
                
                # Build request payload
                payload = {
                    "number": to_number,
                    "options": {
                        "delay": 1200,
                        "presence": "composing"
                    }
                }
                
                if message.media_url:
                    # Send document/PDF
                    endpoint = f"{self.api_url}/message/sendMedia/{self.instance_name}"
                    payload["mediaMessage"] = {
                        "mediatype": "document",
                        "media": message.media_url,
                        "caption": message.body
                    }
                    logger.info(
                        "evolution_sending_document",
                        to=message.to,
                        url=message.media_url,
                        instance=self.instance_name
                    )
                else:
                    # Send text message
                    endpoint = f"{self.api_url}/message/sendText/{self.instance_name}"
                    payload["textMessage"] = {
                        "text": message.body
                    }
                    logger.info(
                        "evolution_sending_text",
                        to=message.to,
                        instance=self.instance_name
                    )
                
                response = await client.post(
                    endpoint,
                    headers=headers,
                    json=payload,
                    timeout=60.0
                )
                response.raise_for_status()
                
                result = response.json()
                
                logger.info(
                    "evolution_message_sent",
                    to=message.to,
                    instance=self.instance_name,
                    response=result
                )
                
                return WhatsAppResponse(
                    success=True,
                    message_id=result.get("key", {}).get("id", "evolution_msg"),
                    error=None
                )
                
        except httpx.HTTPError as e:
            logger.error("evolution_http_error", to=message.to, error=str(e))
            return WhatsAppResponse(
                success=False,
                message_id=None,
                error=f"HTTP Error: {str(e)}"
            )
        except Exception as e:
            logger.error("evolution_send_error", to=message.to, error=str(e))
            return WhatsAppResponse(
                success=False,
                message_id=None,
                error=str(e)
            )


class MetaProvider(WhatsAppProvider):
    """Meta Business API (Facebook/WhatsApp Cloud API) integration."""
    
    def __init__(self):
        self.settings = get_settings()
        self.api_version = self.settings.META_API_VERSION
        self.phone_number_id = self.settings.META_PHONE_NUMBER_ID
        self.access_token = self.settings.META_ACCESS_TOKEN
        self.base_url = f"https://graph.facebook.com/{self.api_version}"
    
    async def send_message(self, message: WhatsAppMessage) -> WhatsAppResponse:
        """Send message via Meta WhatsApp Cloud API."""
        try:
            if not self.access_token or not self.phone_number_id:
                raise ValueError("Meta credentials not configured")
            
            url = f"{self.base_url}/{self.phone_number_id}/messages"
            
            # Clean phone number (remove whatsapp: prefix if present)
            to_number = message.to.replace("whatsapp:", "")
            if not to_number.startswith("+"):
                to_number = f"+{to_number}"
            
            # Build message payload
            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": to_number,
                "type": "text",
                "text": {"body": message.body}
            }
            
            # If media URL provided, send as document
            if message.media_url:
                payload = {
                    "messaging_product": "whatsapp",
                    "recipient_type": "individual",
                    "to": to_number,
                    "type": "document",
                    "document": {
                        "link": message.media_url,
                        "caption": message.body[:1024]  # Meta caption limit
                    }
                }
            
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=30.0
                )
                response.raise_for_status()
                
                result = response.json()
                
                logger.info(
                    "meta_message_sent",
                    message_id=result.get("messages", [{}])[0].get("id"),
                    to=message.to
                )
                
                return WhatsAppResponse(
                    success=True,
                    message_id=result.get("messages", [{}])[0].get("id"),
                    error=None
                )
                
        except httpx.HTTPError as e:
            logger.error("meta_http_error", to=message.to, error=str(e))
            return WhatsAppResponse(
                success=False,
                message_id=None,
                error=f"HTTP Error: {str(e)}"
            )
        except Exception as e:
            logger.error("meta_send_error", to=message.to, error=str(e))
            return WhatsAppResponse(
                success=False,
                message_id=None,
                error=str(e)
            )


class WebhookProvider(WhatsAppProvider):
    """Custom webhook provider for local automation tools."""
    
    def __init__(self):
        self.settings = get_settings()
        self.webhook_url = self.settings.WEBHOOK_URL
        self.auth_token = self.settings.WEBHOOK_AUTH_TOKEN
    
    async def send_message(self, message: WhatsAppMessage) -> WhatsAppResponse:
        """Forward message to custom webhook endpoint."""
        try:
            if not self.webhook_url:
                raise ValueError("Webhook URL not configured")
            
            payload = {
                "phone": message.to,
                "message": message.body,
                "pdf_url": message.media_url
            }
            
            headers = {"Content-Type": "application/json"}
            if self.auth_token:
                headers["Authorization"] = f"Bearer {self.auth_token}"
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.webhook_url,
                    json=payload,
                    headers=headers,
                    timeout=30.0
                )
                response.raise_for_status()
                
                logger.info(
                    "webhook_message_sent",
                    to=message.to,
                    url=self.webhook_url
                )
                
                return WhatsAppResponse(
                    success=True,
                    message_id=None,
                    error=None
                )
                
        except httpx.HTTPError as e:
            logger.error("webhook_http_error", to=message.to, error=str(e))
            return WhatsAppResponse(
                success=False,
                message_id=None,
                error=f"HTTP Error: {str(e)}"
            )
        except Exception as e:
            logger.error("webhook_send_error", to=message.to, error=str(e))
            return WhatsAppResponse(
                success=False,
                message_id=None,
                error=str(e)
            )


class BaileysProvider(WhatsAppProvider):
    """Baileys WhatsApp Web integration via Node.js bridge."""
    
    def __init__(self):
        self.settings = get_settings()
        self.server_url = getattr(self.settings, 'BAILEYS_SERVER_URL', 'http://localhost:3001')
        self.server_url = self.server_url.rstrip('/')
    
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
            
            to_number = message.to.replace("whatsapp:", "").replace("+", "")
            
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
                    error=None
                )
                
        except httpx.HTTPError as e:
            logger.error("baileys_http_error", to=message.to, error=str(e))
            return WhatsAppResponse(
                success=False,
                message_id=None,
                error=f"HTTP Error: {str(e)}"
            )
        except ValueError as e:
            logger.error("baileys_connection_error", to=message.to, error=str(e))
            return WhatsAppResponse(
                success=False,
                message_id=None,
                error=str(e)
            )
        except Exception as e:
            logger.error("baileys_send_error", to=message.to, error=str(e))
            return WhatsAppResponse(
                success=False,
                message_id=None,
                error=str(e)
            )


def get_whatsapp_provider(provider_name: Optional[str] = None) -> WhatsAppProvider:
    """Factory function to get configured WhatsApp provider."""
    settings = get_settings()
    
    # Use provided name or default from settings
    provider_name = (provider_name or settings.WHATSAPP_PROVIDER).lower()
    
    provider_map = {
        "meta": MetaProvider,
        "webhook": WebhookProvider,
        "evolution": EvolutionProvider,
        "baileys": BaileysProvider,
    }
    
    provider_class = provider_map.get(provider_name)
    if not provider_class:
        raise ValueError(f"Unknown WhatsApp provider: {provider_name}")
    
    return provider_class()
