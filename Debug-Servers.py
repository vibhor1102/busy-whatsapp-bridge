#!/usr/bin/env python3
"""
Emergency Debug Launcher
========================

Starts servers WITHOUT any output redirection.
All logs go directly to console.
"""

import subprocess
import sys
import os
import time
import signal
from pathlib import Path

# Change to script directory
os.chdir(Path(__file__).parent)

print("="*60)
print("EMERGENCY DEBUG MODE")
print("="*60)
print()
print("Starting servers with DIRECT console output...")
print("[Press Ctrl+C to stop]")
print()

processes = []

def start_baileys():
    """Start Baileys server - output goes directly to console"""
    print("[1/2] Starting Baileys server...")
    print("      Command: node baileys-server/server.js")
    print()
    
    env = os.environ.copy()
    env['BAILEYS_AUTH_DIR'] = str(Path.home() / 'AppData/Local/BusyWhatsappBridge/auth/baileys_session')
    env['BAILEYS_PORT'] = '3001'
    
    proc = subprocess.Popen(
        ['node', 'baileys-server/server.js'],
        cwd=Path(__file__).parent,
        env=env,
        # NO stdout/stderr redirection - goes directly to console!
    )
    processes.append(('baileys', proc))
    print(f"      PID: {proc.pid}")
    return proc

def start_fastapi():
    """Start FastAPI server - output goes directly to console"""
    print("[2/2] Starting FastAPI server...")
    print("      Command: python -m uvicorn app.main:app --host 0.0.0.0 --port 8000")
    print()
    
    proc = subprocess.Popen(
        [sys.executable, '-m', 'uvicorn', 'app.main:app', '--host', '0.0.0.0', '--port', '8000', '--log-level', 'info'],
        cwd=Path(__file__).parent,
        # NO stdout/stderr redirection - goes directly to console!
    )
    processes.append(('fastapi', proc))
    print(f"      PID: {proc.pid}")
    return proc

def signal_handler(signum, frame):
    print("\n[STOPPING] Shutting down servers...")
    for name, proc in processes:
        print(f"  Stopping {name} (PID: {proc.pid})...")
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except:
            proc.kill()
    print("All servers stopped.")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

try:
    # Start both servers
    baileys_proc = start_baileys()
    time.sleep(2)  # Give Baileys a moment to start
    
    fastapi_proc = start_fastapi()
    
    print()
    print("="*60)
    print("SERVERS STARTED - Showing live output below:")
    print("="*60)
    print()
    print("Dashboard: http://localhost:8000/dashboard")
    print("QR Page:   http://localhost:3001/qr/page")
    print()
    
    # Wait for both processes
    # This will show ALL their output in real-time!
    while True:
        baileys_status = baileys_proc.poll()
        fastapi_status = fastapi_proc.poll()
        
        if baileys_status is not None:
            print(f"\n[ERROR] Baileys exited with code: {baileys_status}")
            break
            
        if fastapi_status is not None:
            print(f"\n[ERROR] FastAPI exited with code: {fastapi_status}")
            break
            
        time.sleep(1)
        
except KeyboardInterrupt:
    signal_handler(None, None)
except Exception as e:
    print(f"\n[ERROR] {e}")
    import traceback
    traceback.print_exc()
    
input("\nPress Enter to exit...")