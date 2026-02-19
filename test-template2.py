#!/usr/bin/env python3
"""
WhatsApp test with different template
"""

import asyncio
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
import httpx

load_dotenv()

async def send_hello_world():
    token = os.getenv("META_ACCESS_TOKEN")
    phone_id = os.getenv("META_PHONE_NUMBER_ID")
    recipient = "919350561606"
    
    url = f"https://graph.facebook.com/v18.0/{phone_id}/messages"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Send hello_world template again
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
    
    print("Sending hello_world template...")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers, timeout=30.0)
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}")
            
            if response.status_code == 200:
                print("\n[OK] Template message sent!")
                print("\nIMPORTANT: Now you have a 24-hour window to send free-form messages.")
                print("Reply to this message from your phone to keep the session active.")
            else:
                print(f"\n[X] Failed: {response.text}")
                
    except Exception as e:
        print(f"\n[X] Error: {e}")

if __name__ == "__main__":
    print("="*60)
    print("WhatsApp Test - Template Message")
    print("="*60)
    print()
    
    asyncio.run(send_hello_world())
    
    print()
    print("="*60)
    print("LIMITATIONS OF TEST ACCOUNTS:")
    print("="*60)
    print("""
1. Test numbers can ONLY send template messages to new recipients
2. After the recipient replies, you have 24 hours to send free-form text
3. You only have 1 template available: 'hello_world'

SOLUTIONS:
A) For testing: Reply to the template message from your phone first,
   then free-form messages will work for 24 hours

B) For production: Upgrade to a verified business account and create
   custom message templates for your use case

C) Use this workflow:
   - Always send template first
   - Wait for user reply
   - Then send regular messages within 24 hours
""")
