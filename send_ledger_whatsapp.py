"""
Send ledger PDF via WhatsApp to Anjali Greh Sajja Panipat.
"""
import asyncio
import os
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.ledger_generator import generate_ledger_pdf, cleanup_ledger_pdf
from app.services.whatsapp import get_whatsapp_provider
from app.exceptions.ledger_exceptions import LedgerError

# Customer details
PARTY_CODE = "7160"
PHONE_NUMBER = "919215536993"  # WhatsApp number with country code (91 = India)

async def send_ledger():
    """Generate and send ledger PDF."""
    pdf_path = None
    
    try:
        print("=" * 60)
        print("SENDING LEDGER TO ANJALI GREH SAJJA-PANIPAT")
        print("=" * 60)
        
        # Generate PDF
        print(f"\nGenerating ledger for party: {PARTY_CODE}")
        pdf_path = await generate_ledger_pdf(PARTY_CODE)
        print(f"PDF generated: {pdf_path}")
        print(f"File size: {os.path.getsize(pdf_path) / 1024:.2f} KB")
        
        # Get WhatsApp provider
        print("\nInitializing WhatsApp provider...")
        whatsapp = get_whatsapp_provider()
        
        # Prepare message
        message_text = (
            "Dear Customer,\n\n"
            "Please find your ledger statement attached for Financial Year 2025-26.\n"
            "Kindly review and arrange payment for outstanding amounts.\n\n"
            "Thank you,\n"
            "Anjali Home Fashion"
        )
        
        # Create WhatsAppMessage object
        from app.models.schemas import WhatsAppMessage
        message = WhatsAppMessage(
            to=PHONE_NUMBER,
            body=message_text,
            media_url=pdf_path
        )
        
        # Send via WhatsApp
        print(f"\nSending to: {PHONE_NUMBER}")
        print("Sending PDF...")
        
        # For Baileys provider
        result = await whatsapp.send_message(message)
        
        if result.success:
            print("\n[OK] Message sent successfully!")
            print(f"[OK] Message ID: {result.message_id}")
        else:
            print(f"\n[X] Failed to send: {result.error}")
        
    except LedgerError as e:
        print(f"\n[X] Ledger Error: {e.error_code}")
        print(f"    {e.message}")
    except Exception as e:
        print(f"\n[X] Error: {type(e).__name__}")
        print(f"    {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        # Clean up
        if pdf_path and os.path.exists(pdf_path):
            cleanup_ledger_pdf(pdf_path)
            print("\n[OK] Cleaned up temp file")

if __name__ == "__main__":
    asyncio.run(send_ledger())
