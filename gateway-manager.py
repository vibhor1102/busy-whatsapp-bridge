#!/usr/bin/env python3
"""
Busy WhatsApp Gateway - Unified Tray Manager
Starts and manages both Baileys and FastAPI servers from one tray icon.
"""

import subprocess
import sys
import os
import time
import threading
import signal
import ctypes
from pathlib import Path
from datetime import datetime

# Windows-specific imports
try:
    import pystray
    from PIL import Image, ImageDraw
    HAS_TRAY = True
except ImportError:
    HAS_TRAY = False

# Process management
processes = {}
server_status = {
    'baileys': {'running': False, 'pid': None, 'started': None},
    'fastapi': {'running': False, 'pid': None, 'started': None}
}
tray_icon = None
shutdown_event = threading.Event()


def show_already_running():
    """Show clear console message when already running."""
    print("\n" + "="*60)
    print(" BUSY WHATSAPP GATEWAY")
    print("="*60)
    print("\n Already running!")
    print("\n Check your system tray (near the clock)")
    print(" for the green WhatsApp icon.")
    print("\n Right-click the icon to access controls.")
    print("\n" + "="*60 + "\n")
    input("Press Enter to close...")


def ensure_single_instance():
    """Ensure only one instance of gateway-manager is running."""
    if sys.platform != 'win32':
        return True
    
    try:
        mutex_name = "Global\\BusyWhatsAppGateway_Instance"
        kernel32 = ctypes.windll.kernel32
        ERROR_ALREADY_EXISTS = 183
        
        mutex = kernel32.CreateMutexW(None, False, mutex_name)
        last_error = kernel32.GetLastError()
        
        if mutex == 0:
            return True
        
        if last_error == ERROR_ALREADY_EXISTS:
            kernel32.CloseHandle(mutex)
            show_already_running()
            return False
        
        return True
        
    except Exception as e:
        print(f"Warning: Could not check for running instance: {e}")
        return True

# Run single instance check FIRST
if not ensure_single_instance():
    sys.exit(0)


def create_tray_icon():
    """Create a simple icon for the system tray."""
    if not HAS_TRAY:
        return None
    
    width = 64
    height = 64
    image = Image.new('RGB', (width, height), 'white')
    dc = ImageDraw.Draw(image)
    dc.ellipse([4, 4, width-4, height-4], fill='#25D366')
    dc.ellipse([20, 18, 28, 26], fill='white')
    dc.rectangle([24, 22, 32, 42], fill='white')
    dc.ellipse([20, 38, 28, 46], fill='white')
    return image


def create_error_icon():
    """Create a red icon for error state."""
    if not HAS_TRAY:
        return None
    
    width = 64
    height = 64
    image = Image.new('RGB', (width, height), 'white')
    dc = ImageDraw.Draw(image)
    dc.ellipse([4, 4, width-4, height-4], fill='#dc3545')
    dc.line([(20, 20), (44, 44)], fill='white', width=4)
    dc.line([(44, 20), (20, 44)], fill='white', width=4)
    return image


def create_gray_icon():
    """Create a gray icon for partial running state."""
    if not HAS_TRAY:
        return None
    
    width = 64
    height = 64
    image = Image.new('RGB', (width, height), 'white')
    dc = ImageDraw.Draw(image)
    dc.ellipse([4, 4, width-4, height-4], fill='#6c757d')
    dc.ellipse([20, 18, 28, 26], fill='white')
    dc.rectangle([24, 22, 32, 42], fill='white')
    dc.ellipse([20, 38, 28, 46], fill='white')
    return image


def log_message(msg, level='INFO'):
    """Log message with timestamp."""
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(f"[{timestamp}] [{level}] {msg}")


def check_nodejs():
    """Check if Node.js is installed."""
    try:
        result = subprocess.run(['node', '--version'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            return True, result.stdout.strip()
    except:
        pass
    return False, None


def check_python():
    """Check if Python is available."""
    try:
        result = subprocess.run([sys.executable, '--version'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            return True, result.stdout.strip()
    except:
        pass
    return False, None


def check_baileys_deps():
    """Check if Baileys dependencies are installed."""
    baileys_dir = Path(__file__).parent / 'baileys-server'
    return (baileys_dir / 'node_modules').exists()


def install_baileys_deps():
    """Install Baileys dependencies."""
    log_message("Installing Baileys dependencies...")
    baileys_dir = Path(__file__).parent / 'baileys-server'
    try:
        result = subprocess.run(
            ['npm', 'install'],
            cwd=baileys_dir,
            capture_output=True,
            text=True,
            timeout=120
        )
        if result.returncode == 0:
            log_message("Baileys dependencies installed successfully")
            return True
        else:
            log_message(f"Failed to install Baileys deps: {result.stderr}", 'ERROR')
            return False
    except Exception as e:
        log_message(f"Error installing Baileys deps: {e}", 'ERROR')
        return False


def start_baileys():
    """Start Baileys server."""
    global processes, server_status
    
    if server_status['baileys']['running']:
        log_message("Baileys already running")
        return True
    
    baileys_dir = Path(__file__).parent / 'baileys-server'
    log_message("Starting Baileys server...")
    
    try:
        creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        
        proc = subprocess.Popen(
            ['node', 'server.js'],
            cwd=baileys_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=creationflags
        )
        
        processes['baileys'] = proc
        server_status['baileys'] = {
            'running': True,
            'pid': proc.pid,
            'started': datetime.now()
        }
        
        log_message(f"Baileys server started (PID: {proc.pid})")
        threading.Thread(target=monitor_baileys, daemon=True).start()
        update_tray_icon()
        return True
    except Exception as e:
        log_message(f"Failed to start Baileys: {e}", 'ERROR')
        return False


def start_fastapi():
    """Start FastAPI server."""
    global processes, server_status
    
    if server_status['fastapi']['running']:
        log_message("FastAPI already running")
        return True
    
    log_message("Starting FastAPI server...")
    
    try:
        creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        
        proc = subprocess.Popen(
            [sys.executable, '-m', 'uvicorn', 'app.main:app', '--host', '0.0.0.0', '--port', '8000'],
            cwd=Path(__file__).parent,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=creationflags
        )
        
        processes['fastapi'] = proc
        server_status['fastapi'] = {
            'running': True,
            'pid': proc.pid,
            'started': datetime.now()
        }
        
        log_message(f"FastAPI server started (PID: {proc.pid})")
        threading.Thread(target=monitor_fastapi, daemon=True).start()
        update_tray_icon()
        return True
    except Exception as e:
        log_message(f"Failed to start FastAPI: {e}", 'ERROR')
        return False


def stop_baileys():
    """Stop Baileys server."""
    global server_status
    if 'baileys' not in processes:
        log_message("Baileys not running")
        return
    
    proc = processes['baileys']
    if proc.poll() is None:
        log_message("Stopping Baileys server...")
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except:
            proc.kill()
    
    server_status['baileys'] = {'running': False, 'pid': None, 'started': None}
    del processes['baileys']
    log_message("Baileys stopped")
    update_tray_icon()


def stop_fastapi():
    """Stop FastAPI server."""
    global server_status
    if 'fastapi' not in processes:
        log_message("FastAPI not running")
        return
    
    proc = processes['fastapi']
    if proc.poll() is None:
        log_message("Stopping FastAPI server...")
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except:
            proc.kill()
    
    server_status['fastapi'] = {'running': False, 'pid': None, 'started': None}
    del processes['fastapi']
    log_message("FastAPI stopped")
    update_tray_icon()


def monitor_baileys():
    """Monitor Baileys process."""
    global server_status
    proc = processes.get('baileys')
    if not proc:
        return
    
    while not shutdown_event.is_set():
        ret = proc.poll()
        if ret is not None:
            server_status['baileys']['running'] = False
            log_message(f"Baileys server stopped (exit code: {ret})", 'WARNING')
            update_tray_icon()
            break
        time.sleep(1)


def monitor_fastapi():
    """Monitor FastAPI process."""
    global server_status
    proc = processes.get('fastapi')
    if not proc:
        return
    
    while not shutdown_event.is_set():
        ret = proc.poll()
        if ret is not None:
            server_status['fastapi']['running'] = False
            log_message(f"FastAPI server stopped (exit code: {ret})", 'WARNING')
            update_tray_icon()
            break
        time.sleep(1)


def stop_all():
    """Stop all servers."""
    log_message("Shutting down all servers...")
    shutdown_event.set()
    stop_baileys()
    stop_fastapi()
    log_message("All servers stopped")


def update_tray_icon():
    """Update tray icon based on server status."""
    if not tray_icon or not HAS_TRAY:
        return
    
    baileys_running = server_status['baileys']['running']
    fastapi_running = server_status['fastapi']['running']
    
    if baileys_running and fastapi_running:
        tray_icon.icon = create_tray_icon()
        tray_icon.title = "Busy WhatsApp Gateway - Running"
    elif baileys_running or fastapi_running:
        tray_icon.icon = create_gray_icon()
        running = []
        if baileys_running:
            running.append("Baileys")
        if fastapi_running:
            running.append("FastAPI")
        tray_icon.title = f"Busy WhatsApp Gateway - {', '.join(running)} running"
    else:
        tray_icon.icon = create_error_icon()
        tray_icon.title = "Busy WhatsApp Gateway - Stopped"
    
    # Update menu dynamically
    tray_icon.menu = create_tray_menu()


def open_dashboard():
    """Open dashboard in browser."""
    import webbrowser
    webbrowser.open('http://localhost:8000/dashboard')
    log_message("Opened Dashboard")


def open_qr_page():
    """Open QR code page in browser."""
    import webbrowser
    webbrowser.open('http://localhost:3001/qr/page')
    log_message("Opened QR code page")


def open_api_docs():
    """Open API documentation."""
    import webbrowser
    webbrowser.open('http://localhost:8000/docs')
    log_message("Opened API docs")


def show_status():
    """Show current status."""
    status_text = "Server Status:\n\n"
    
    for name, status in server_status.items():
        state = "Running" if status['running'] else "Stopped"
        pid = f" (PID: {status['pid']})" if status['pid'] else ""
        started = f"\n  Started: {status['started'].strftime('%H:%M:%S')}" if status['started'] else ""
        status_text += f"{name.title()}: {state}{pid}{started}\n"
    
    status_text += f"\nDashboard: http://localhost:8000/dashboard (Left-click tray icon)"
    status_text += f"\nBaileys QR: http://localhost:3001/qr/page"
    status_text += f"\nAPI Docs: http://localhost:8000/docs"
    
    log_message("\n" + status_text)
    
    # Simple console output - no MessageBox
    print("\n" + "="*60)
    print(status_text)
    print("="*60 + "\n")


def create_tray_menu():
    """Create system tray menu."""
    if not HAS_TRAY:
        return None
    
    return pystray.Menu(
        pystray.MenuItem("Open Dashboard", open_dashboard, default=True),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Status", show_status),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(
            "Stop Baileys" if server_status['baileys']['running'] else "Start Baileys",
            stop_baileys if server_status['baileys']['running'] else start_baileys
        ),
        pystray.MenuItem("Open QR Code Page", open_qr_page),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(
            "Stop FastAPI" if server_status['fastapi']['running'] else "Start FastAPI",
            stop_fastapi if server_status['fastapi']['running'] else start_fastapi
        ),
        pystray.MenuItem("Open API Docs", open_api_docs),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Stop All & Exit", stop_tray)
    )


def stop_tray():
    """Stop tray and exit."""
    global tray_icon
    stop_all()
    if tray_icon:
        tray_icon.stop()


def setup_tray():
    """Setup system tray icon."""
    global tray_icon
    if not HAS_TRAY:
        return
    
    icon = create_tray_icon()
    menu = create_tray_menu()
    
    tray_icon = pystray.Icon(
        "busy-whatsapp",
        icon,
        "Busy WhatsApp Gateway",
        menu
    )
    
    tray_icon.run()


def main():
    """Main entry point."""
    print("="*60)
    print("Busy WhatsApp Gateway - Tray Manager")
    print("="*60)
    print()
    
    # Check prerequisites
    node_ok, node_ver = check_nodejs()
    if not node_ok:
        print("ERROR: Node.js is required but not found!")
        print("Please install Node.js 18+ from https://nodejs.org/")
        input("\nPress Enter to exit...")
        return 1
    
    py_ok, py_ver = check_python()
    if not py_ok:
        print("ERROR: Python is required but not found!")
        input("\nPress Enter to exit...")
        return 1
    
    log_message(f"Node.js: {node_ver}")
    log_message(f"Python: {py_ver}")
    
    # Check/install Baileys dependencies
    if not check_baileys_deps():
        log_message("Baileys dependencies not found")
        if not install_baileys_deps():
            print("ERROR: Failed to install Baileys dependencies")
            input("\nPress Enter to exit...")
            return 1
    
    # Check .env file
    env_file = Path(__file__).parent / '.env'
    if not env_file.exists():
        log_message("Creating .env from template...")
        example_env = Path(__file__).parent / '.env.example'
        if example_env.exists():
            import shutil
            shutil.copy(example_env, env_file)
            log_message("Please edit .env file with your database path before running again!")
            input("\nPress Enter to open .env file...")
            os.startfile(env_file)
            return 1
    
    # Start servers
    log_message("Starting servers...")
    
    baileys_ok = start_baileys()
    if baileys_ok:
        time.sleep(2)
    
    fastapi_ok = start_fastapi()
    
    if not baileys_ok and not fastapi_ok:
        print("ERROR: Failed to start any server")
        input("\nPress Enter to exit...")
        return 1
    
    log_message("Servers started!")
    log_message("Dashboard: http://localhost:8000/dashboard")
    log_message("QR Code: http://localhost:3001/qr/page")
    log_message("API: http://localhost:8000")
    
    # Setup signal handlers
    def signal_handler(signum, frame):
        log_message(f"Received signal {signum}")
        stop_tray()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start tray or console mode
    if HAS_TRAY:
        print("\nRunning in system tray mode...")
        print("Left-click tray icon to open Dashboard")
        print("Right-click tray icon to control servers")
        print()
        
        tray_thread = threading.Thread(target=setup_tray, daemon=True)
        tray_thread.start()
        
        try:
            while not shutdown_event.is_set():
                time.sleep(1)
        except KeyboardInterrupt:
            log_message("Keyboard interrupt received")
            stop_tray()
    else:
        print("\nRunning in console mode...")
        print("Commands: [b]aileys [f]astapi [s]tatus [q]uit")
        print()
        
        try:
            while not shutdown_event.is_set():
                cmd = input().lower().strip()
                if cmd in ['b', 'baileys']:
                    if server_status['baileys']['running']:
                        stop_baileys()
                    else:
                        start_baileys()
                elif cmd in ['f', 'fastapi']:
                    if server_status['fastapi']['running']:
                        stop_fastapi()
                    else:
                        start_fastapi()
                elif cmd in ['s', 'status']:
                    show_status()
                elif cmd in ['q', 'quit', 'exit']:
                    stop_all()
                    break
        except KeyboardInterrupt:
            log_message("Keyboard interrupt received")
            stop_all()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
