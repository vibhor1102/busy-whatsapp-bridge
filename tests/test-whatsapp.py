#!/usr/bin/env python3
"""
Simple test script for WhatsApp via Baileys

Setup:
1. Ensure Baileys server is running (npm start in baileys-server/)
2. Ensure WHATSAPP_PROVIDER=baileys in the conf.json file
3. Run: python test-whatsapp.py

NOTE: This script previously tested Meta Cloud API which has been removed.
Only Baileys is now available.
TODO: Re-add via Baileys integration when needed
"""

import asyncio
import os
import sys

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config import get_settings
from app.services.whatsapp import BaileysProvider
from app.models.schemas import WhatsAppMessage

async def send_test_message():
    """Send a test message to the specified number."""
    
    # Get settings
    settings = get_settings()
    
    print(f"Using provider: {settings.WHATSAPP_PROVIDER}")
    
    # Test recipient
    recipient = "+919350561606"
    
    # Create provider
    provider = BaileysProvider()
    
    # Create message
    message = WhatsAppMessage(
        to=recipient,
        body="Test message from Busy WhatsApp Bridge (Baileys)",
    )
    
    # Send
    print(f"Sending message to {recipient}...")
    result = await provider.send_message(message)
    
    if result.success:
        print(f"[OK] Message sent successfully!")
        print(f"    Message ID: {result.message_id}")
        print(f"    Status: {result.delivery_status}")
    else:
        print(f"[X] Failed: {result.error}")

if __name__ == "__main__":
    asyncio.run(send_test_message())
