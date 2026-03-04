#!/usr/bin/env python3
"""
Busy Invoice Simulator - Simulates webhook calls from Busy Accounting Software
Double-click to run, or run from command line.
"""

import sys
import time
import socket
import urllib.parse
import urllib.request
from urllib.error import HTTPError, URLError
import json

# Configuration - Edit these values as needed
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8000
SERVER_URL = f"http://{SERVER_HOST}:{SERVER_PORT}"
PHONE = "9215536993"
NAME = "RUCHI GOEL"
AMOUNT = "3,675.00"
DOC_TYPE = "Sales Invoice"
PDF_CODE = "AQBwhS4VN"
FROM_NAME = "AHF"

# Build the exact Busy message format
MESSAGE = f"Dear '{NAME}', Please find attached '{DOC_TYPE}' for Rs. {AMOUNT}. Regards, {FROM_NAME} files.busy.in/?{PDF_CODE}"

# ANSI colors for Windows compatibility
class Colors:
    GREEN = '\033[92m' if sys.platform != 'win32' else ''
    RED = '\033[91m' if sys.platform != 'win32' else ''
    YELLOW = '\033[93m' if sys.platform != 'win32' else ''
    CYAN = '\033[96m' if sys.platform != 'win32' else ''
    RESET = '\033[0m' if sys.platform != 'win32' else ''
    BOLD = '\033[1m' if sys.platform != 'win32' else ''


def check_server() -> bool:
    """Check if FastAPI server is running using socket first, then HTTP."""
    print("Checking if FastAPI server is running...")
    
    # First, quick socket check
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((SERVER_HOST, SERVER_PORT))
        sock.close()
        if result != 0:
            print(f"{Colors.RED}[ERROR]{Colors.RESET} Nothing listening on {SERVER_HOST}:{SERVER_PORT}")
            return False
        print(f"{Colors.GREEN}[OK]{Colors.RESET} Socket connection")
    except Exception as e:
        print(f"{Colors.RED}[ERROR]{Colors.RESET} Socket error: {e}")
        return False
    
    # Now try HTTP request with longer timeout
    try:
        req = urllib.request.Request(
            f"{SERVER_URL}/api/v1/health",
            method='GET'
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            status = response.status
            content = response.read().decode('utf-8')
            
            # Try to parse response for status info
            try:
                data = json.loads(content)
                server_status = data.get('status', 'unknown')
                print(f"{Colors.GREEN}[OK]{Colors.RESET} Server responding (status: {server_status})")
            except:
                print(f"{Colors.GREEN}[OK]{Colors.RESET} Server responding (HTTP {status})")
            return True
            
    except HTTPError as e:
        # Even if error, server is running
        print(f"{Colors.GREEN}[OK]{Colors.RESET} Server responding (HTTP {e.code})")
        return True
    except Exception as e:
        print(f"{Colors.RED}[ERROR]{Colors.RESET} HTTP request failed: {e}")
        return False


def send_invoice() -> bool:
    """Send invoice notification to FastAPI."""
    print("\nSending invoice notification to FastAPI...\n")
    
    # URL encode the message
    encoded_msg = urllib.parse.quote(MESSAGE, safe='')
    
    # Build the URL
    url = f"{SERVER_URL}/api/v1/send-invoice?phone={PHONE}&msg={encoded_msg}"
    
    print(f"Request URL: {url}\n")
    
    try:
        req = urllib.request.Request(
            url,
            method='GET',
            headers={'accept': 'application/json'}
        )
        
        with urllib.request.urlopen(req, timeout=15) as response:
            content = response.read().decode('utf-8')
            
            print(f"{Colors.CYAN}Response from server:{Colors.RESET}")
            print("-" * 50)
            
            # Pretty print JSON
            try:
                data = json.loads(content)
                print(json.dumps(data, indent=2))
            except:
                print(content)
            
            print("-" * 50)
            
            # Parse success
            try:
                data = json.loads(content)
                if data.get('success'):
                    print(f"\n{Colors.GREEN}[SUCCESS]{Colors.RESET} Invoice notification queued!")
                    if 'message_id' in data:
                        print(f"  Message ID: {data.get('message_id')}")
                    if 'status' in data:
                        print(f"  Status: {data.get('status')}")
                    return True
                else:
                    print(f"\n{Colors.YELLOW}[WARNING]{Colors.RESET} Request completed but reported failure")
                    if 'error' in data:
                        print(f"  Error: {data.get('error')}")
                    return False
            except:
                return response.status == 200
                
    except HTTPError as e:
        print(f"{Colors.RED}[HTTP ERROR]{Colors.RESET} Status: {e.code}")
        try:
            error_body = e.read().decode('utf-8')
            print(f"Server Response: {error_body}")
        except Exception:
            print(str(e))
        return False
    except Exception as e:
        print(f"{Colors.RED}[ERROR]{Colors.RESET} Request failed: {e}")
        return False


def wait_for_keypress(timeout_seconds: int = 2) -> bool:
    """Wait for keypress with timeout. Returns True if key was pressed."""
    if sys.platform == 'win32':
        import msvcrt
        
        start = time.time()
        while time.time() - start < timeout_seconds:
            if msvcrt.kbhit():
                msvcrt.getch()
                return True
            time.sleep(0.1)
        return False
    else:
        print(f"(Auto-closing in {timeout_seconds} seconds...)")
        time.sleep(timeout_seconds)
        return False


def main() -> int:
    print("\n" + "=" * 50)
    print("  BUSY SIMULATOR - Invoice Webhook Test")
    print("=" * 50)
    print()
    print("Configuration:")
    print(f"  Server: {SERVER_URL}")
    print(f"  Phone: {PHONE}")
    print(f"  Message: {MESSAGE}")
    print()
    
    # Check server
    if not check_server():
        print(f"\n{Colors.RED}Make sure to run Start-Gateway.py first!{Colors.RESET}")
        print("\nPress any key to exit...")
        if sys.platform == 'win32':
            import msvcrt
            msvcrt.getch()
        return 1
    
    # Send invoice
    success = send_invoice()
    
    # Auto-close logic
    print("\n" + "=" * 50)
    print("Press any key NOW to keep window open (for copying output)")
    print("Or wait 2 seconds for auto-close...")
    print("=" * 50)
    
    if wait_for_keypress(2):
        print(f"\n{Colors.YELLOW}[Window staying open]{Colors.RESET} - Close manually when done")
        print("Press any key to exit...")
        if sys.platform == 'win32':
            import msvcrt
            msvcrt.getch()
    
    return 0 if success else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nInterrupted.")
        sys.exit(1)
