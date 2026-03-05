#!/usr/bin/env python3
"""
Integration test for Payment Reminders with Baileys

This script tests the complete flow:
1. Generate a test ledger PDF
2. Queue a payment reminder message with PDF attachment
3. Process the queue (which sends via Baileys)

Usage:
    python test-reminder-baileys.py

Prerequisites:
1. Baileys server must be running: cd baileys-server && npm start
2. WhatsApp must be authenticated (scan QR code at http://localhost:3001/qr/page)
3. DATABASE connection must be configured (for ledger data)
"""

import asyncio
import os
import sys
from datetime import datetime
from decimal import Decimal

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config import get_settings
from app.services.reminder_service import ReminderService
from app.services.queue_service import queue_service
from app.database.message_queue import message_db
import structlog

logger = structlog.get_logger()


async def test_baileys_connection():
    """Test if Baileys server is connected."""
    import httpx
    
    settings = get_settings()
    baileys_url = getattr(settings, 'BAILEYS_SERVER_URL', 'http://localhost:3001')
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{baileys_url}/status",
                timeout=5.0
            )
            if response.status_code == 200:
                data = response.json()
                state = data.get("data", {}).get("state")
                if state == "connected":
                    user = data.get("data", {}).get("user", {})
                    print(f"[OK] Baileys connected!")
                    print(f"    User: {user.get('name', 'Unknown')}")
                    print(f"    Phone: {user.get('id', 'Unknown')}")
                    return True
                else:
                    print(f"[X] Baileys not connected. State: {state}")
                    print(f"    Please scan QR code at: {baileys_url}/qr/page")
                    return False
            else:
                print(f"[X] Baileys server returned status {response.status_code}")
                return False
    except Exception as e:
        print(f"[X] Baileys server not reachable: {str(e)}")
        print(f"    Start it with: cd baileys-server && npm start")
        return False


async def test_reminder_queue_flow():
    """Test the reminder-to-queue flow."""
    print("\n" + "="*60)
    print("Testing Payment Reminder with Baileys Integration")
    print("="*60)
    
    # Check Baileys connection first
    if not await test_baileys_connection():
        print("\n[!] Please ensure Baileys is connected before testing.")
        return False
    
    print("\n[1] Testing queue service with PDF attachment...")
    
    # Create a test PDF file
    test_pdf_path = os.path.join(os.path.dirname(__file__), "test_ledger.pdf")
    
    # Create a simple test PDF
    try:
        from fpdf import FPDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt="Test Ledger for Payment Reminder", ln=1, align="C")
        pdf.cell(200, 10, txt="Customer: Test Customer", ln=1, align="L")
        pdf.cell(200, 10, txt="Amount Due: Rs. 5,000.00", ln=1, align="L")
        pdf.cell(200, 10, txt="Date: " + datetime.now().strftime("%d/%m/%Y"), ln=1, align="L")
        pdf.output(test_pdf_path)
        print(f"    [OK] Created test PDF: {test_pdf_path}")
    except Exception as e:
        print(f"    [!] Could not create test PDF: {str(e)}")
        print(f"        Continuing with text-only message...")
        test_pdf_path = None
    
    # Queue a test message
    try:
        result = await queue_service.enqueue_invoice_notification(
            phone="+919350561606",  # Test phone number
            message="This is a test payment reminder from Busy WhatsApp Bridge via Baileys.",
            pdf_url=test_pdf_path,
            provider="baileys",
            source="integration_test"
        )
        
        queue_id = result.get("queue_id")
        print(f"    [OK] Message queued with ID: {queue_id}")
        
        # Process the queue immediately
        print("\n[2] Processing queue...")
        message = message_db.get_message_by_id(queue_id)
        
        if message:
            print(f"    Processing message to: {message['phone']}")
            success = await queue_service.process_single_message(message)
            
            if success:
                print(f"    [OK] Message sent successfully!")
                
                # Check message status
                history = message_db.get_message_history(limit=1)
                if history:
                    msg = history[0]
                    print(f"\n[3] Message Status:")
                    print(f"    Phone: {msg['phone']}")
                    print(f"    Status: {msg['status']}")
                    print(f"    Delivery: {msg.get('delivery_status', 'N/A')}")
                    print(f"    Sent at: {msg.get('sent_at', 'N/A')}")
                    print(f"    Message ID: {msg.get('message_id', 'N/A')}")
                
                return True
            else:
                print(f"    [X] Message failed to send")
                
                # Check error
                history = message_db.get_message_history(limit=1)
                if history:
                    msg = history[0]
                    print(f"    Error: {msg.get('error_message', 'Unknown error')}")
                
                return False
        else:
            print(f"    [X] Could not retrieve queued message")
            return False
            
    except Exception as e:
        print(f"    [X] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Cleanup test PDF
        if test_pdf_path and os.path.exists(test_pdf_path):
            try:
                os.remove(test_pdf_path)
                print(f"\n    [OK] Cleaned up test PDF")
            except:
                pass


async def main():
    """Main test function."""
    print("Busy WhatsApp Bridge - Baileys Integration Test")
    print("=" * 60)
    
    settings = get_settings()
    print(f"\nConfiguration:")
    print(f"  Provider: {settings.WHATSAPP_PROVIDER}")
    print(f"  Baileys URL: {settings.BAILEYS_SERVER_URL}")
    print(f"  Default Country: {settings.WHATSAPP_DEFAULT_COUNTRY_CODE}")
    
    success = await test_reminder_queue_flow()
    
    print("\n" + "="*60)
    if success:
        print("[SUCCESS] Integration test completed!")
        print("\nThe payment reminder system is properly integrated with Baileys.")
        print("You can now send payment reminders with PDF attachments via WhatsApp Web.")
    else:
        print("[FAILED] Integration test failed!")
        print("\nPlease check:")
        print("1. Baileys server is running (npm start in baileys-server/)")
        print("2. WhatsApp is authenticated (visit /baileys/qr)")
        print("3. The test phone number is correct")
    print("="*60)
    
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
