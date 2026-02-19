#!/usr/bin/env python3
"""
WhatsApp test with debugging
"""

import asyncio
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
import httpx

load_dotenv()

async def send_with_debug():
    token = os.getenv("META_ACCESS_TOKEN")
    phone_id = os.getenv("META_PHONE_NUMBER_ID")
    
    # Try without + symbol
    recipient = "919350561606"  # Remove + for testing
    
    print(f"Token: {token[:20]}...")
    print(f"Phone ID: {phone_id}")
    print(f"To: {recipient}")
    print()
    
    url = f"https://graph.facebook.com/v18.0/{phone_id}/messages"
    
    # Try a simple text message
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": recipient,
        "type": "text",
        "text": {"body": "Test message 1 - plain text"}
    }
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    print("Attempt 1: Plain text message")
    print(f"URL: {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    print()
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers, timeout=30.0)
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}")
            
            if response.status_code == 200:
                result = response.json()
                msg_id = result.get("messages", [{}])[0].get("id")
                print(f"\n[OK] Sent! Message ID: {msg_id}")
            else:
                print(f"\n[X] Failed: {response.text}")
                
    except Exception as e:
        print(f"\n[X] Error: {e}")
    
    print("\n" + "="*50)
    
    # Try with + symbol
    recipient2 = "+919350561606"
    payload2 = payload.copy()
    payload2["to"] = recipient2
    
    print("\nAttempt 2: With + symbol")
    print(f"To: {recipient2}")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload2, headers=headers, timeout=30.0)
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}")
            
            if response.status_code == 200:
                result = response.json()
                msg_id = result.get("messages", [{}])[0].get("id")
                print(f"\n[OK] Sent! Message ID: {msg_id}")
            else:
                print(f"\n[X] Failed: {response.text}")
                
    except Exception as e:
        print(f"\n[X] Error: {e}")

if __name__ == "__main__":
    asyncio.run(send_with_debug())
