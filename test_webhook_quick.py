#!/usr/bin/env python3
"""
Quick manual test for Busy webhook
Run this AFTER starting the server with: python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
"""

import requests
import sys

BASE_URL = "http://localhost:8000"

def test_webhook():
    """Test webhook with PDF in message"""
    print("\n" + "="*60)
    print("Testing Busy Webhook")
    print("="*60)
    
    phone = "9826463222"
    msg = "Dear 'ANKUR AGGARWAL INDORE', Please find attached 'Sales Invoice' for Rs. 3,675.00. Regards, ankur files.busy.in/?AQBwhS4VN"
    
    params = {
        "phone": phone,
        "msg": msg
    }
    
    try:
        print(f"URL: {BASE_URL}/api/v1/send-invoice")
        print(f"Phone: {phone}")
        print(f"Message: {msg[:60]}...")
        print("\nSending request...")
        
        response = requests.get(
            f"{BASE_URL}/api/v1/send-invoice",
            params=params,
            timeout=30
        )
        
        print(f"\nStatus: {response.status_code}")
        data = response.json()
        print(f"Response: {data}")
        
        if response.status_code == 200 and data.get('success'):
            print("\n✓ SUCCESS!")
            print(f"Message ID: {data.get('message_id')}")
            return True
        else:
            print(f"\n✗ FAILED: {data.get('error', 'Unknown')}")
            return False
            
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        print("\nMake sure the server is running:")
        print("  python -m uvicorn app.main:app --host 0.0.0.0 --port 8000")
        return False

if __name__ == "__main__":
    success = test_webhook()
    sys.exit(0 if success else 1)
