#!/usr/bin/env python3
"""
WhatsApp template message test
"""

import asyncio
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
import httpx

load_dotenv()

async def send_template():
    token = os.getenv("META_ACCESS_TOKEN")
    phone_id = os.getenv("META_PHONE_NUMBER_ID")
    recipient = "919350561606"
    
    url = f"https://graph.facebook.com/v18.0/{phone_id}/messages"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Try hello_world template (Meta's default template)
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": recipient,
        "type": "template",
        "template": {
            "name": "hello_world",
            "language": {"code": "en_US"}
        }
    }
    
    print("Sending template message (hello_world)...")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    print()
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers, timeout=30.0)
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}")
            
            if response.status_code == 200:
                print("\n[OK] Template message sent!")
            else:
                print(f"\n[X] Failed: {response.text}")
                
    except Exception as e:
        print(f"\n[X] Error: {e}")
    
    print("\n" + "="*50)
    print("\nNOTE: If you still don't receive the message:")
    print("1. Check that you've added this phone number to Meta dashboard")
    print("2. Make sure WhatsApp is installed on the phone")
    print("3. The test number might need to receive a message first")
    print("4. Try messaging the test number from your phone first")

if __name__ == "__main__":
    asyncio.run(send_template())
