import structlog
import re
import asyncio
from typing import Optional, Tuple
from app.config import get_settings
from app.database.connection import db
from app.models.schemas import (
    InvoiceNotification, 
    PartyDetails, 
    WhatsAppMessage,
    WhatsAppResponse
)
from app.services.whatsapp import get_whatsapp_provider
from app.services.queue_service import queue_service

logger = structlog.get_logger()


class BusyHandler:
    """Handler for Busy Accounting webhook notifications."""
    
    def __init__(self):
        self.settings = get_settings()
        self.whatsapp_provider = get_whatsapp_provider()
    
    def _extract_pdf_url(self, msg: str, pdf_url: Optional[str]) -> Tuple[str, Optional[str]]:
        """
        Extract PDF URL from message if pdf_url is a placeholder.
        
        Returns:
            Tuple of (cleaned_message, extracted_pdf_url)
        """
        # Check if pdf_url is a placeholder or empty
        is_placeholder = not pdf_url or pdf_url.strip() == "" or "{" in pdf_url or "}" in pdf_url
        
        if is_placeholder:
            # Try to extract URL from message (looking for busy.in domain or any URL)
            # Pattern matches: files.busy.in/?XXXXXX or any http/https URL
            url_patterns = [
                r'(files\.busy\.in/\?\w+)',  # Busy cloud files
                r'(https?://\S+)',  # Any HTTP URL
                r'(www\.\S+)',  # www URLs
            ]
            
            for pattern in url_patterns:
                match = re.search(pattern, msg, re.IGNORECASE)
                if match:
                    extracted_url = match.group(1)
                    # Ensure it has protocol
                    if not extracted_url.startswith('http'):
                        extracted_url = f"https://{extracted_url}"
                    
                    # Remove URL from message
                    cleaned_msg = re.sub(pattern, '', msg, flags=re.IGNORECASE).strip()
                    # Clean up extra whitespace
                    cleaned_msg = re.sub(r'\s+', ' ', cleaned_msg).strip()
                    
                    return cleaned_msg, extracted_url
            
            # No URL found in message
            return msg, None
        
        # pdf_url is valid, just return as-is
        return msg, pdf_url

    async def process_invoice_notification(
        self, 
        notification: InvoiceNotification
    ) -> WhatsAppResponse:
        """
        Process invoice notification from Busy.
        
        Workflow:
        1. Receive notification with phone, message, PDF URL
        2. Extract PDF URL from message if needed
        3. Query database for party details (optional enhancement)
        4. Queue message for delivery (via background worker)
        """
        try:
            # Extract PDF URL from message if placeholder
            cleaned_msg, extracted_pdf_url = self._extract_pdf_url(
                notification.msg, 
                notification.pdf_url
            )
            
            logger.info(
                "processing_invoice_notification",
                phone=notification.phone,
                has_pdf=bool(extracted_pdf_url),
                pdf_extracted=extracted_pdf_url != notification.pdf_url
            )
            
            # Optional: Fetch additional party details from database
            party_data = await asyncio.to_thread(
                db.get_party_by_phone, notification.phone
            )
            
            if party_data:
                # Enhance message with party details if available
                party = PartyDetails(**party_data)
                enhanced_message = self._enhance_message(
                    cleaned_msg, 
                    party
                )
            else:
                enhanced_message = cleaned_msg
                logger.warning(
                    "party_not_found_in_db",
                    phone=notification.phone,
                    using_original_message=True
                )
            
            # Queue message for delivery (non-blocking)
            result = await queue_service.enqueue_invoice_notification(
                phone=notification.phone,
                message=enhanced_message,
                pdf_url=extracted_pdf_url,
                provider=self.settings.WHATSAPP_PROVIDER,
                source="busy"
            )
            
            logger.info(
                "invoice_notification_queued",
                phone=notification.phone,
                queue_id=result["queue_id"],
                status=result["status"]
            )
            
            return WhatsAppResponse(
                success=True,
                message_id=str(result["queue_id"]),
                error=None
            )
            
        except Exception as e:
            logger.error(
                "process_notification_error",
                phone=notification.phone,
                error=str(e)
            )
            return WhatsAppResponse(
                success=False,
                message_id=None,
                error=f"Processing error: {str(e)}"
            )
    
    def _enhance_message(self, original_msg: str, party: PartyDetails) -> str:
        """
        Enhance message with party details.
        
        This can be customized to include:
        - Party name
        - GST number
        - Custom greeting
        """
        enhancements = []
        
        # Add party name if available
        if party.print_name:
            enhancements.append(f"Dear {party.print_name},")
        elif party.name:
            enhancements.append(f"Dear {party.name},")
        
        # Combine with original message
        if enhancements:
            return "\n\n".join(enhancements + [original_msg])
        
        return original_msg
    
    async def get_party_details(self, phone: str) -> Optional[PartyDetails]:
        """Fetch party details from database by phone number."""
        try:
            party_data = await asyncio.to_thread(db.get_party_by_phone, phone)
            if party_data:
                return PartyDetails(**party_data)
            return None
        except Exception as e:
            logger.error("get_party_details_error", phone=phone, error=str(e))
            return None


# Global handler instance
busy_handler = BusyHandler()
