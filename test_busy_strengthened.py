#!/usr/bin/env python3
"""
Comprehensive Busy Webhook Test Suite
Tests the strengthened Busy configuration with PDF extraction
"""

import requests
import sys
from urllib.parse import quote

BASE_URL = "http://192.168.1.166:8000"


def test_health():
    """Test health endpoint"""
    print("\n" + "="*60)
    print("TEST 1: Health Check")
    print("="*60)
    
    try:
        response = requests.get(f"{BASE_URL}/api/v1/health", timeout=10)
        data = response.json()
        print(f"Status: {data.get('status')}")
        print(f"Database: {'✓ Connected' if data.get('database_connected') else '✗ Not connected'}")
        return response.status_code == 200
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_busy_webhook_with_pdf_in_message():
    """Test webhook with PDF URL embedded in message"""
    print("\n" + "="*60)
    print("TEST 2: Busy Webhook - PDF in Message (No pdf_url param)")
    print("="*60)
    
    # Simulate exactly what Busy sends
    phone = "9826463222"
    msg = "Dear 'ANKUR AGGARWAL INDORE', Please find attached 'Sales Invoice' for Rs. 3,675.00. Regards, ankur files.busy.in/?AQBwhS4VN"
    
    params = {
        "phone": phone,
        "msg": msg
        # Note: NO pdf_url parameter - we're extracting it from message
    }
    
    try:
        print(f"Sending request to: {BASE_URL}/api/v1/send-invoice")
        print(f"Phone: {phone}")
        print(f"Message: {msg[:60]}...")
        print(f"PDF URL: <extracted from message>")
        
        response = requests.get(
            f"{BASE_URL}/api/v1/send-invoice",
            params=params,
            timeout=30
        )
        
        print(f"\nResponse Status: {response.status_code}")
        data = response.json()
        print(f"Response Body: {data}")
        
        if response.status_code == 200 and data.get('success'):
            print("\n✓ Webhook processed successfully")
            print(f"✓ Message ID: {data.get('message_id')}")
            return True
        else:
            print(f"\n✗ Failed: {data.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_busy_webhook_with_explicit_pdf_url():
    """Test webhook with explicit pdf_url parameter"""
    print("\n" + "="*60)
    print("TEST 3: Busy Webhook - Explicit PDF URL")
    print("="*60)
    
    phone = "9812802226"
    msg = "Your invoice is ready"
    pdf_url = "https://example.com/invoice.pdf"
    
    params = {
        "phone": phone,
        "msg": msg,
        "pdf_url": pdf_url
    }
    
    try:
        print(f"Sending request with explicit PDF URL...")
        response = requests.get(
            f"{BASE_URL}/api/v1/send-invoice",
            params=params,
            timeout=30
        )
        
        data = response.json()
        print(f"Response: {data}")
        
        return response.status_code == 200
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_error_handling():
    """Test error handling for invalid requests"""
    print("\n" + "="*60)
    print("TEST 4: Error Handling")
    print("="*60)
    
    # Test missing required parameter
    try:
        response = requests.get(
            f"{BASE_URL}/api/v1/send-invoice?phone=123",
            timeout=10
        )
        print(f"Missing 'msg' parameter - Status: {response.status_code}")
        
        if response.status_code == 422:
            print("✓ Correctly rejected missing parameter")
            return True
        else:
            print(f"Unexpected status: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def main():
    print("\n" + "="*60)
    print("BUSY WEBHOOK CONFIGURATION TEST SUITE")
    print("="*60)
    print(f"Target: {BASE_URL}")
    print("="*60)
    
    tests = [
        ("Health Check", test_health),
        ("Webhook - PDF in Message", test_busy_webhook_with_pdf_in_message),
        ("Webhook - Explicit PDF", test_busy_webhook_with_explicit_pdf_url),
        ("Error Handling", test_error_handling),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ Test '{name}' crashed: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, r in results if r)
    failed = len(results) - passed
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {len(results)} tests")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print("="*60)
    
    if failed == 0:
        print("\n🎉 All tests passed! Busy configuration is working correctly.")
        print("\nNext steps:")
        print("1. Update Busy SMS Configuration URL to:")
        print(f"   http://192.168.1.166:8000/api/v1/send-invoice?phone={{MobileNo}}&msg={{Message}}")
        print("2. Test with actual Busy invoice")
        print("3. Configure WhatsApp provider (Meta or Webhook)")
    else:
        print("\n⚠ Some tests failed. Please check the errors above.")
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
