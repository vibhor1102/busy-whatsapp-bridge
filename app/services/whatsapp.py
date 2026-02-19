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


class TwilioProvider(WhatsAppProvider):
    """Twilio WhatsApp Business API integration."""
    
    def __init__(self):
        self.settings = get_settings()
        self.account_sid = self.settings.TWILIO_ACCOUNT_SID
        self.auth_token = self.settings.TWILIO_AUTH_TOKEN
        self.from_number = self.settings.TWILIO_PHONE_NUMBER
        self.base_url = "https://api.twilio.com/2010-04-01"
    
    async def send_message(self, message: WhatsAppMessage) -> WhatsAppResponse:
        """Send message via Twilio WhatsApp API."""
        try:
            if not self.account_sid or not self.auth_token:
                raise ValueError("Twilio credentials not configured")
            
            url = f"{self.base_url}/Accounts/{self.account_sid}/Messages.json"
            
            # Format phone numbers with WhatsApp prefix
            to_number = message.to if message.to.startswith("whatsapp:") else f"whatsapp:{message.to}"
            if self.from_number:
                from_number = self.from_number if self.from_number.startswith("whatsapp:") else f"whatsapp:{self.from_number}"
            else:
                raise ValueError("TWILIO_PHONE_NUMBER not configured")
            
            payload = {
                "To": to_number,
                "From": from_number,
                "Body": message.body
            }
            
            # Add media URL if provided
            if message.media_url:
                payload["MediaUrl"] = message.media_url
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    data=payload,
                    auth=(self.account_sid, self.auth_token),
                    timeout=30.0
                )
                response.raise_for_status()
                
                result = response.json()
                
                logger.info(
                    "twilio_message_sent",
                    message_sid=result.get("sid"),
                    to=message.to,
                    status=result.get("status")
                )
                
                return WhatsAppResponse(
                    success=True,
                    message_id=result.get("sid"),
                    error=None
                )
                
        except httpx.HTTPError as e:
            logger.error("twilio_http_error", to=message.to, error=str(e))
            return WhatsAppResponse(
                success=False,
                message_id=None,
                error=f"HTTP Error: {str(e)}"
            )
        except Exception as e:
            logger.error("twilio_send_error", to=message.to, error=str(e))
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


def get_whatsapp_provider() -> WhatsAppProvider:
    """Factory function to get configured WhatsApp provider."""
    settings = get_settings()
    
    provider_map = {
        "twilio": TwilioProvider,
        "meta": MetaProvider,
        "webhook": WebhookProvider
    }
    
    provider_class = provider_map.get(settings.WHATSAPP_PROVIDER.lower())
    if not provider_class:
        raise ValueError(f"Unknown WhatsApp provider: {settings.WHATSAPP_PROVIDER}")
    
    return provider_class()
