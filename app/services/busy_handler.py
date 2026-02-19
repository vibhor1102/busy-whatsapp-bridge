import structlog
from typing import Optional
from app.database.connection import db
from app.models.schemas import (
    InvoiceNotification, 
    PartyDetails, 
    WhatsAppMessage,
    WhatsAppResponse
)
from app.services.whatsapp import get_whatsapp_provider

logger = structlog.get_logger()


class BusyHandler:
    """Handler for Busy Accounting webhook notifications."""
    
    def __init__(self):
        self.whatsapp_provider = get_whatsapp_provider()
    
    async def process_invoice_notification(
        self, 
        notification: InvoiceNotification
    ) -> WhatsAppResponse:
        """
        Process invoice notification from Busy.
        
        Workflow:
        1. Receive notification with phone, message, PDF URL
        2. Query database for party details (optional enhancement)
        3. Send WhatsApp message with PDF
        """
        try:
            logger.info(
                "processing_invoice_notification",
                phone=notification.phone,
                has_pdf=bool(notification.pdf_url)
            )
            
            # Optional: Fetch additional party details from database
            party_data = db.get_party_by_phone(notification.phone)
            
            if party_data:
                # Enhance message with party details if available
                party = PartyDetails(**party_data)
                enhanced_message = self._enhance_message(
                    notification.msg, 
                    party
                )
            else:
                enhanced_message = notification.msg
                logger.warning(
                    "party_not_found_in_db",
                    phone=notification.phone,
                    using_original_message=True
                )
            
            # Prepare WhatsApp message
            whatsapp_msg = WhatsAppMessage(
                to=notification.phone,
                body=enhanced_message,
                media_url=notification.pdf_url
            )
            
            # Send via WhatsApp provider
            result = await self.whatsapp_provider.send_message(whatsapp_msg)
            
            if result.success:
                logger.info(
                    "invoice_notification_sent",
                    phone=notification.phone,
                    message_id=result.message_id
                )
            else:
                logger.error(
                    "invoice_notification_failed",
                    phone=notification.phone,
                    error=result.error
                )
            
            return result
            
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
            party_data = db.get_party_by_phone(phone)
            if party_data:
                return PartyDetails(**party_data)
            return None
        except Exception as e:
            logger.error("get_party_details_error", phone=phone, error=str(e))
            return None


# Global handler instance
busy_handler = BusyHandler()
