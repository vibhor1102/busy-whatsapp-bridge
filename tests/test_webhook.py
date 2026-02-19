#!/usr/bin/env python
"""
Test script to simulate Busy Accounting webhook requests.

Usage:
    python tests/test_webhook.py
    
Or with custom parameters:
    python tests/test_webhook.py --phone "+919876543210" --msg "Test message"
"""

import argparse
import requests
import sys
from datetime import datetime


def test_health_endpoint(base_url: str = "http://localhost:8000"):
    """Test the health check endpoint."""
    print("\n" + "="*60)
    print("TEST 1: Health Check")
    print("="*60)
    
    try:
        response = requests.get(f"{base_url}/api/v1/health", timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Service is {data['status']}")
            print(f"✓ Database connected: {data['database_connected']}")
            return True
        else:
            print(f"✗ Health check failed")
            return False
            
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_get_invoice_notification(
    base_url: str = "http://localhost:8000",
    phone: str = "+919876543210",
    msg: str = "Your invoice #INV001 for Rs. 5000 is ready",
    pdf_url: str = "https://example.com/invoice.pdf"
):
    """Test GET endpoint for invoice notification."""
    print("\n" + "="*60)
    print("TEST 2: Send Invoice Notification (GET)")
    print("="*60)
    
    params = {
        "phone": phone,
        "msg": msg,
        "pdf_url": pdf_url
    }
    
    print(f"Parameters: {params}")
    
    try:
        response = requests.get(
            f"{base_url}/api/v1/send-invoice",
            params=params,
            timeout=30
        )
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                print(f"✓ Message sent successfully")
                print(f"✓ Message ID: {data.get('message_id')}")
                return True
            else:
                print(f"✗ Message sending failed: {data.get('error')}")
                return False
        else:
            print(f"✗ Request failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_post_invoice_notification(
    base_url: str = "http://localhost:8000",
    phone: str = "+919876543210",
    msg: str = "Your invoice #INV002 for Rs. 7500 is ready",
    pdf_url: str = "https://example.com/invoice2.pdf"
):
    """Test POST endpoint for invoice notification."""
    print("\n" + "="*60)
    print("TEST 3: Send Invoice Notification (POST)")
    print("="*60)
    
    payload = {
        "phone": phone,
        "msg": msg,
        "pdf_url": pdf_url
    }
    
    print(f"Payload: {payload}")
    
    try:
        response = requests.post(
            f"{base_url}/api/v1/send-invoice",
            json=payload,
            timeout=30
        )
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                print(f"✓ Message sent successfully")
                print(f"✓ Message ID: {data.get('message_id')}")
                return True
            else:
                print(f"✗ Message sending failed: {data.get('error')}")
                return False
        else:
            print(f"✗ Request failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_party_lookup(base_url: str = "http://localhost:8000", phone: str = "+919876543210"):
    """Test party lookup by phone number."""
    print("\n" + "="*60)
    print("TEST 4: Party Lookup")
    print("="*60)
    
    try:
        response = requests.get(
            f"{base_url}/api/v1/parties/{phone}",
            timeout=10
        )
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Party found:")
            print(f"  - Code: {data.get('code')}")
            print(f"  - Name: {data.get('name')}")
            print(f"  - Print Name: {data.get('print_name')}")
            print(f"  - Email: {data.get('email')}")
            print(f"  - GST No: {data.get('gst_no')}")
            return True
        elif response.status_code == 404:
            print(f"✗ Party not found for phone: {phone}")
            return False
        else:
            print(f"✗ Request failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_search_parties(base_url: str = "http://localhost:8000", search_term: str = "ABC"):
    """Test party search."""
    print("\n" + "="*60)
    print("TEST 5: Party Search")
    print("="*60)
    
    try:
        response = requests.get(
            f"{base_url}/api/v1/parties/search/{search_term}",
            timeout=10
        )
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Found {data.get('count')} parties")
            for party in data.get('parties', [])[:3]:  # Show first 3
                print(f"  - {party.get('code')}: {party.get('name')}")
            return True
        else:
            print(f"✗ Request failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Test Busy WhatsApp Gateway API"
    )
    parser.add_argument(
        "--url", 
        default="http://localhost:8000",
        help="Base URL of the API (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--phone",
        default="+919876543210",
        help="Phone number for testing (default: +919876543210)"
    )
    parser.add_argument(
        "--msg",
        default="Your invoice #TEST001 for Rs. 5000 is ready",
        help="Message text for testing"
    )
    parser.add_argument(
        "--pdf-url",
        default="https://example.com/test-invoice.pdf",
        help="PDF URL for testing"
    )
    parser.add_argument(
        "--skip-send",
        action="store_true",
        help="Skip message sending tests (useful if WhatsApp not configured)"
    )
    
    args = parser.parse_args()
    
    print("\n" + "="*60)
    print("BUSY WHATSAPP GATEWAY - API TEST SUITE")
    print(f"Target: {args.url}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    results = []
    
    # Test 1: Health Check
    results.append(("Health Check", test_health_endpoint(args.url)))
    
    # Test 2 & 3: Send Invoice (only if not skipped)
    if not args.skip_send:
        results.append(("Send Invoice (GET)", test_get_invoice_notification(
            args.url, args.phone, args.msg, args.pdf_url
        )))
        results.append(("Send Invoice (POST)", test_post_invoice_notification(
            args.url, args.phone, args.msg, args.pdf_url
        )))
    else:
        print("\n[!] Skipping message sending tests (use --skip-send to enable)")
    
    # Test 4: Party Lookup
    results.append(("Party Lookup", test_party_lookup(args.url, args.phone)))
    
    # Test 5: Party Search
    results.append(("Party Search", test_search_parties(args.url, "Test")))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    failed = len(results) - passed
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {len(results)} tests")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
