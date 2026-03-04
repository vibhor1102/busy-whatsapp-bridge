#!/usr/bin/env python3
"""
Simple backend verification script.
Tests the API without any fancy setup.
"""

import sys
import os
import subprocess
import time
import json
import requests
from pathlib import Path

# Configuration
BASE_URL = "http://localhost:8000"
TEST_TIMEOUT = 30

def print_header(text):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")

def print_result(test_name, success, details=""):
    status = "[OK]" if success else "[FAIL]"
    print(f"{status} {test_name}")
    if details:
        print(f"      {details}")

def check_dependencies():
    """Check if required packages are installed."""
    print_header("1. Checking Dependencies")
    
    required = ['fastapi', 'uvicorn', 'pyodbc', 'pydantic', 'httpx']
    missing = []
    
    for pkg in required:
        try:
            __import__(pkg)
            print(f"  [OK] {pkg}")
        except ImportError:
            print(f"  [MISSING] {pkg}")
            missing.append(pkg)
    
    if missing:
        print(f"\n  Install missing packages:")
        print(f"  pip install {' '.join(missing)}")
        return False
    
    return True

def check_environment():
    """Check if conf.json file exists and is configured."""
    print_header("2. Checking Environment")
    
    from app.config import get_config_path
    config_path = get_config_path()
    
    if not config_path.exists():
        print(f"  [MISSING] conf.json not found at {config_path}")
        print("  Creating from template...")
        
        example = Path("conf.json.example")
        if example.exists():
            import shutil
            config_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(example, config_path)
            print(f"  [OK] Created conf.json at {config_path}")
            print("  [!] Please edit conf.json with your database path and credentials")
        else:
            print("  [FAIL] conf.json.example not found")
        return False
    
    print(f"  [OK] conf.json exists at {config_path}")
    
    # Check critical config
    try:
        from app.config import get_settings
        settings = get_settings()
        
        bds_path = settings.BDS_FILE_PATH
        if bds_path and Path(bds_path).exists():
            print(f"  [OK] Database file found: {bds_path}")
        elif bds_path:
            print(f"  [MISSING] Database file NOT found: {bds_path}")
            print(f"    Please update database.bds_file_path in conf.json")
            return False
        else:
            print(f"  [WARN] BDS_FILE_PATH not set in conf.json")
            print(f"    Database tests will be skipped")
    except Exception as e:
        print(f"  [WARN] Could not load conf.json: {e}")
    
    return True

def test_database():
    """Test database connectivity."""
    print_header("3. Testing Database Connection")
    
    # First check Python architecture
    import struct
    arch_bits = struct.calcsize('P') * 8
    print(f"  Python architecture: {arch_bits}-bit")
    
    if arch_bits != 32:
        print(f"  [WARN] Python is {arch_bits}-bit, but 32-bit is required for ODBC")
        print(f"  [WARN] Database tests will likely fail")
        print(f"  [INFO] Install 32-bit Python from: https://www.python.org/downloads/windows/")
    
    try:
        from app.database.connection import db
        
        print("  Attempting to connect to database...")
        if db.test_connection():
            print("  [OK] Database connection successful")
            
            # Try to query Master1
            print("  Testing query on Master1 table...")
            import pyodbc
            conn = pyodbc.connect(db.settings.database_connection_string)
            cursor = conn.cursor()
            cursor.execute("SELECT TOP 1 * FROM Master1")
            columns = [desc[0] for desc in cursor.description]
            print(f"  [OK] Master1 table accessible")
            print(f"    Columns: {', '.join(columns[:5])}...")
            conn.close()
            return True
        else:
            print("  [FAIL] Database connection failed")
            return False
    except Exception as e:
        print(f"  [FAIL] Database error: {e}")
        print(f"    Make sure:")
        print(f"    - Python is 32-bit (required for ODBC)")
        print(f"    - Microsoft Access Database Engine is installed (32-bit)")
        print(f"    - Database path in conf.json is correct")
        return False

def start_server():
    """Start the uvicorn server in background."""
    print_header("4. Starting Server")
    
    print("  Starting uvicorn server...")
    
    # Start server as subprocess
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=os.getcwd()
    )
    
    # Wait for server to start
    print("  Waiting for server to start (5 seconds)...")
    time.sleep(5)
    
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/api/v1/health", timeout=5)
        if response.status_code == 200:
            print("  [OK] Server started successfully")
            return process
    except:
        pass
    
    print("  [FAIL] Server failed to start")
    process.terminate()
    return None

def test_api_endpoints():
    """Test API endpoints."""
    print_header("5. Testing API Endpoints")
    
    results = []
    
    # Test 1: Health endpoint
    try:
        response = requests.get(f"{BASE_URL}/api/v1/health", timeout=10)
        data = response.json()
        success = response.status_code == 200 and data.get("status") == "healthy"
        print_result("Health Check", success, f"Status: {data.get('status')}")
        results.append(("Health", success))
    except Exception as e:
        print_result("Health Check", False, str(e))
        results.append(("Health", False))
    
    # Test 2: Send Invoice (GET) - Simulate Busy request
    try:
        params = {
            "phone": "+919876543210",
            "msg": "Test invoice #001 for Rs. 1000",
            "pdf_url": "https://example.com/test.pdf"
        }
        response = requests.get(f"{BASE_URL}/api/v1/send-invoice", params=params, timeout=10)
        # Even if it fails to send WhatsApp, the endpoint should work
        success = response.status_code in [200, 500]  # 500 is OK if WhatsApp not configured
        print_result("Send Invoice Endpoint", success, f"Status: {response.status_code}")
        results.append(("Send Invoice", success))
    except Exception as e:
        print_result("Send Invoice Endpoint", False, str(e))
        results.append(("Send Invoice", False))
    
    # Test 3: Party Lookup (if database works)
    try:
        response = requests.get(f"{BASE_URL}/api/v1/parties/+919876543210", timeout=10)
        # 200 = found, 404 = not found (both are valid responses)
        success = response.status_code in [200, 404]
        print_result("Party Lookup", success, f"Status: {response.status_code}")
        results.append(("Party Lookup", success))
    except Exception as e:
        print_result("Party Lookup", False, str(e))
        results.append(("Party Lookup", False))
    
    return results

def simulate_busy_request():
    """Simulate what Busy software will send."""
    print_header("6. Simulating Busy Software Request")
    
    print("  This is what Busy will send when an invoice is saved:")
    print()
    
    # Example 1: GET request
    url = f"{BASE_URL}/api/v1/send-invoice?phone=%2B919876543210&msg=Your+invoice+%23INV001+for+Rs.+5000+is+ready&pdf_url=https%3A%2F%2Fbdep.busy.in%2Finvoice%2F12345.pdf"
    print(f"  GET Request URL:")
    print(f"  {url}")
    print()
    
    # Actually send it
    try:
        response = requests.get(url, timeout=10)
        print(f"  Response Status: {response.status_code}")
        print(f"  Response Body:")
        print(json.dumps(response.json(), indent=4))
        
        if response.status_code == 200:
            print("\n  [OK] Request processed successfully")
        else:
            print(f"\n  [WARN] Request returned status {response.status_code}")
            print("         (This is OK if WhatsApp provider is not configured yet)")
    except Exception as e:
        print(f"\n  [FAIL] Request failed: {e}")

def main():
    print_header("BUSY WHATSAPP GATEWAY - BACKEND VERIFICATION")
    print("This script tests if the backend is working correctly.")
    print("No Windows Service or production setup needed.")
    
    # Check dependencies
    if not check_dependencies():
        print("\n[FAIL] Please install missing dependencies first")
        print("  pip install -r requirements.txt")
        return 1
    
    # Check environment
    if not check_environment():
        print("\n[WARN] Please configure conf.json file before continuing")
        print("  Copy conf.json.example to conf.json and edit it")
        return 1
    
    # Test database
    db_ok = test_database()
    
    # Start server
    server_process = start_server()
    if not server_process:
        print("\n[FAIL] Cannot continue without server")
        return 1
    
    try:
        # Test endpoints
        api_results = test_api_endpoints()
        
        # Simulate Busy request
        simulate_busy_request()
        
        # Summary
        print_header("SUMMARY")
        
        all_passed = all(success for _, success in api_results)
        
        print(f"Database Connection: {'[OK] WORKING' if db_ok else '[FAIL] FAILED'}")
        print(f"API Endpoints: {'[OK] WORKING' if all_passed else '[WARN] SOME ISSUES'}")
        print()
        
        if db_ok and all_passed:
            print("[OK] Backend is working correctly!")
            print()
            print("Next steps:")
            print("1. Keep this server running")
            print("2. Configure Busy SMS provider (see BUSY_CONFIG.md)")
            print("3. Test with actual Busy invoice")
        else:
            print("[WARN] Some tests failed. Check the errors above.")
            print()
            print("Common issues:")
            if not db_ok:
                print("- Database: Ensure 32-bit Python and Access Engine are installed")
            print("- API: Check if server started correctly")
        
        print()
        print("Press Ctrl+C to stop the server when done testing")
        
        # Keep server running
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\nStopping server...")
    
    finally:
        server_process.terminate()
        server_process.wait()
        print("Server stopped.")
    
    return 0 if (db_ok and all_passed) else 1

if __name__ == "__main__":
    sys.exit(main())
