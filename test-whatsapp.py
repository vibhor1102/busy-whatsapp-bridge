#!/usr/bin/env python3
"""
Simple test script for WhatsApp Cloud API

Setup:
1. Fill in your META_ACCESS_TOKEN in the .env file
2. Update META_PHONE_NUMBER_ID with your test number ID (starts with 555)
3. Change WHATSAPP_PROVIDER=meta in the .env file
4. Run: python test-whatsapp.py
"""

import asyncio
import os
import sys

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
from app.services.whatsapp import MetaProvider
from app.models.schemas import WhatsAppMessage

load_dotenv()

async def send_test_message():
    """Send a test message to the specified number."""
    
    # Get settings
    token = os.getenv("META_ACCESS_TOKEN", "")
    phone_id = os.getenv("META_PHONE_NUMBER_ID", "")
    
    if not token or token == "YOUR_TOKEN_HERE":
        print("[X] Error: Please set META_ACCESS_TOKEN in .env file")
        return
    
    if not phone_id or phone_id == "555XXXXXXXXXXX":
        print("[X] Error: Please set META_PHONE_NUMBER_ID in .env file")
        return
    
    # Test recipient
    recipient = "+919350561606"
    
    print("Sending test message...")
    print(f"   From: {phone_id}")
    print(f"   To: {recipient}")
    print()
    
    try:
        provider = MetaProvider()
        message = WhatsAppMessage(
            to=recipient,
            body="Hello! This is a test message from your WhatsApp integration.",
            media_url=None
        )
        
        result = await provider.send_message(message)
        
        if result.success:
            print("[OK] Message sent successfully!")
            print(f"   Message ID: {result.message_id}")
        else:
            print("[X] Failed to send message")
            print(f"   Error: {result.error}")
            
    except Exception as e:
        print(f"[X] Error: {str(e)}")

if __name__ == "__main__":
    print("=" * 50)
    print("WhatsApp Cloud API Test Script")
    print("=" * 50)
    print()
    
    asyncio.run(send_test_message())
