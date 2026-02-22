#!/usr/bin/env python3
"""
Busy WhatsApp Gateway - Unified Runner
======================================

The main entry point for the gateway. Supports multiple modes:

  python run.py           # Console mode (visible logs, all servers)
  python run.py --tray    # System tray mode (hidden console, tray icon)
  python run.py --headless # Background mode (no UI, logs to file)

Features:
  - Real-time log visibility from all servers
  - Color-coded output by server
  - Startup progress with health checks
  - Graceful shutdown handling
"""

import subprocess
import sys
import os
import time
import threading
import signal
import argparse
import ctypes
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
import queue
import select

try:
    import pystray
    from PIL import Image, ImageDraw
    HAS_TRAY = True
except ImportError:
    HAS_TRAY = False

LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

PROCESSES: Dict[str, subprocess.Popen] = {}
SERVER_STATUS: Dict[str, Dict[str, Any]] = {
    'baileys': {'running': False, 'pid': None, 'started': None},
    'fastapi': {'running': False, 'pid': None, 'started': None}
}
SHUTDOWN_EVENT = threading.Event()
TRAY_ICON: Optional[pystray.Icon] = None
LOG_QUEUE: queue.Queue = queue.Queue()
CONSOLE_MODE = True

ANSI_COLORS = {
    'reset': '\033[0m',
    'bold': '\033[1m',
    'dim': '\033[2m',
    'red': '\033[91m',
    'green': '\033[92m',
    'yellow': '\033[93m',
    'blue': '\033[94m',
    'magenta': '\033[95m',
    'cyan': '\033[96m',
    'white': '\033[97m',
}

def colorize(text: str, color: str) -> str:
    if not sys.stdout.isatty():
        return text
    return f"{ANSI_COLORS.get(color, '')}{text}{ANSI_COLORS['reset']}"

def timestamp() -> str:
    return datetime.now().strftime('%H:%M:%S')

def log(prefix: str, message: str, color: str = 'white'):
    line = f"[{timestamp()}] [{prefix}] {message}"
    if CONSOLE_MODE:
        print(f"{colorize(f'[{timestamp()}]', 'dim')} {colorize(f'[{prefix}]', color)} {message}")
    LOG_QUEUE.put(line)

def log_raw(server: str, line: str):
    if CONSOLE_MODE:
        color = 'cyan' if server == 'baileys' else 'magenta'
        prefix = colorize(f"[{server}]", color)
        print(f"{colorize(f'[{timestamp()}]', 'dim')} {prefix} {line.rstrip()}")
    LOG_QUEUE.put(f"[{timestamp()}] [{server}] {line.rstrip()}")

def write_to_log_file():
    log_file = LOG_DIR / f"gateway_{datetime.now().strftime('%Y%m%d')}.log"
    buffered = []
    last_flush = time.time()
    
    while not SHUTDOWN_EVENT.is_set():
        try:
            line = LOG_QUEUE.get(timeout=0.5)
            buffered.append(line + '\n')
            
            if time.time() - last_flush > 2 or len(buffered) > 50:
                with open(log_file, 'a', encoding='utf-8') as f:
                    f.writelines(buffered)
                buffered.clear()
                last_flush = time.time()
        except queue.Empty:
            if buffered:
                with open(log_file, 'a', encoding='utf-8') as f:
                    f.writelines(buffered)
                buffered.clear()
                last_flush = time.time()

def stream_output(server: str, pipe):
    try:
        for line in iter(pipe.readline, ''):
            if line:
                log_raw(server, line)
            else:
                break
    except:
        pass

def check_prerequisites() -> bool:
    log('SYSTEM', 'Checking prerequisites...', 'yellow')
    
    node_result = subprocess.run(['node', '--version'], capture_output=True, text=True, timeout=5)
    if node_result.returncode != 0:
        log('SYSTEM', 'ERROR: Node.js not found! Install from https://nodejs.org/', 'red')
        return False
    log('SYSTEM', f'Node.js: {node_result.stdout.strip()}', 'green')
    
    py_result = subprocess.run([sys.executable, '--version'], capture_output=True, text=True, timeout=5)
    if py_result.returncode != 0:
        log('SYSTEM', 'ERROR: Python not found!', 'red')
        return False
    log('SYSTEM', f'Python: {py_result.stdout.strip()}', 'green')
    
    baileys_dir = Path(__file__).parent / 'baileys-server'
    if not (baileys_dir / 'node_modules').exists():
        log('SYSTEM', 'Installing Baileys dependencies...', 'yellow')
        result = subprocess.run(['npm', 'install'], cwd=baileys_dir, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            log('SYSTEM', f'Failed to install Baileys deps: {result.stderr}', 'red')
            return False
        log('SYSTEM', 'Baileys dependencies installed', 'green')
    
    env_file = Path(__file__).parent / '.env'
    if not env_file.exists():
        example = Path(__file__).parent / '.env.example'
        if example.exists():
            import shutil
            shutil.copy(example, env_file)
            log('SYSTEM', 'Created .env from template. Please configure and restart.', 'yellow')
            return False
    
    log('SYSTEM', 'All prerequisites OK', 'green')
    return True

def start_baileys() -> bool:
    if SERVER_STATUS['baileys']['running']:
        log('BAILEYS', 'Already running', 'yellow')
        return True
    
    baileys_dir = Path(__file__).parent / 'baileys-server'
    log('BAILEYS', 'Starting server...', 'cyan')
    
    try:
        if CONSOLE_MODE:
            proc = subprocess.Popen(
                ['node', 'server.js'],
                cwd=baileys_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
        else:
            creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            proc = subprocess.Popen(
                ['node', 'server.js'],
                cwd=baileys_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=creationflags
            )
        
        PROCESSES['baileys'] = proc
        SERVER_STATUS['baileys'] = {'running': True, 'pid': proc.pid, 'started': datetime.now()}
        
        threading.Thread(target=stream_output, args=('baileys', proc.stdout), daemon=True).start()
        threading.Thread(target=stream_output, args=('baileys', proc.stderr), daemon=True).start()
        threading.Thread(target=monitor_process, args=('baileys',), daemon=True).start()
        
        log('BAILEYS', f'Started (PID: {proc.pid})', 'green')
        return True
        
    except Exception as e:
        log('BAILEYS', f'Failed to start: {e}', 'red')
        return False

def start_fastapi() -> bool:
    if SERVER_STATUS['fastapi']['running']:
        log('FASTAPI', 'Already running', 'yellow')
        return True
    
    log('FASTAPI', 'Starting server...', 'magenta')
    
    try:
        if CONSOLE_MODE:
            proc = subprocess.Popen(
                [sys.executable, '-m', 'uvicorn', 'app.main:app', '--host', '0.0.0.0', '--port', '8000'],
                cwd=Path(__file__).parent,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
        else:
            creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            proc = subprocess.Popen(
                [sys.executable, '-m', 'uvicorn', 'app.main:app', '--host', '0.0.0.0', '--port', '8000'],
                cwd=Path(__file__).parent,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=creationflags
            )
        
        PROCESSES['fastapi'] = proc
        SERVER_STATUS['fastapi'] = {'running': True, 'pid': proc.pid, 'started': datetime.now()}
        
        threading.Thread(target=stream_output, args=('fastapi', proc.stdout), daemon=True).start()
        threading.Thread(target=stream_output, args=('fastapi', proc.stderr), daemon=True).start()
        threading.Thread(target=monitor_process, args=('fastapi',), daemon=True).start()
        
        log('FASTAPI', f'Started (PID: {proc.pid})', 'green')
        return True
        
    except Exception as e:
        log('FASTAPI', f'Failed to start: {e}', 'red')
        return False

def monitor_process(server: str):
    proc = PROCESSES.get(server)
    if not proc:
        return
    
    while not SHUTDOWN_EVENT.is_set():
        ret = proc.poll()
        if ret is not None:
            SERVER_STATUS[server]['running'] = False
            log(server.upper(), f'Process exited (code: {ret})', 'red')
            update_tray()
            break
        time.sleep(1)

def stop_server(server: str):
    if server not in PROCESSES:
        return
    
    proc = PROCESSES[server]
    if proc.poll() is None:
        log(server.upper(), f'Stopping...', 'yellow')
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
    
    SERVER_STATUS[server] = {'running': False, 'pid': None, 'started': None}
    del PROCESSES[server]
    log(server.upper(), 'Stopped', 'yellow')
    update_tray()

def stop_all():
    log('SYSTEM', 'Shutting down...', 'yellow')
    SHUTDOWN_EVENT.set()
    stop_server('baileys')
    stop_server('fastapi')
    log('SYSTEM', 'All servers stopped', 'green')

def wait_for_server(url: str, name: str, timeout: int = 30) -> bool:
    import httpx
    log('SYSTEM', f'Waiting for {name} to be ready...', 'yellow')
    
    start = time.time()
    while time.time() - start < timeout:
        try:
            resp = httpx.get(url, timeout=2)
            if resp.status_code < 500:
                log('SYSTEM', f'{name} is ready!', 'green')
                return True
        except:
            pass
        time.sleep(1)
    
    log('SYSTEM', f'{name} did not become ready in {timeout}s', 'red')
    return False

def create_tray_icon():
    if not HAS_TRAY:
        return None
    
    size = 64
    image = Image.new('RGB', (size, size), 'white')
    dc = ImageDraw.Draw(image)
    dc.ellipse([4, 4, size-4, size-4], fill='#25D366')
    dc.ellipse([20, 18, 28, 26], fill='white')
    dc.rectangle([24, 22, 32, 42], fill='white')
    dc.ellipse([20, 38, 28, 46], fill='white')
    return image

def create_error_icon():
    if not HAS_TRAY:
        return None
    
    size = 64
    image = Image.new('RGB', (size, size), 'white')
    dc = ImageDraw.Draw(image)
    dc.ellipse([4, 4, size-4, size-4], fill='#dc3545')
    dc.line([(20, 20), (44, 44)], fill='white', width=4)
    dc.line([(44, 20), (20, 44)], fill='white', width=4)
    return image

def create_partial_icon():
    if not HAS_TRAY:
        return None
    
    size = 64
    image = Image.new('RGB', (size, size), 'white')
    dc = ImageDraw.Draw(image)
    dc.ellipse([4, 4, size-4, size-4], fill='#6c757d')
    dc.ellipse([20, 18, 28, 26], fill='white')
    dc.rectangle([24, 22, 32, 42], fill='white')
    dc.ellipse([20, 38, 28, 46], fill='white')
    return image

def update_tray():
    global TRAY_ICON
    if not TRAY_ICON or not HAS_TRAY:
        return
    
    baileys_ok = SERVER_STATUS['baileys']['running']
    fastapi_ok = SERVER_STATUS['fastapi']['running']
    
    if baileys_ok and fastapi_ok:
        TRAY_ICON.icon = create_tray_icon()
        TRAY_ICON.title = "Busy WhatsApp Gateway - Running"
    elif baileys_ok or fastapi_ok:
        TRAY_ICON.icon = create_partial_icon()
        running = [n for n, s in SERVER_STATUS.items() if s['running']]
        TRAY_ICON.title = f"Busy WhatsApp Gateway - {', '.join(running).title()}"
    else:
        TRAY_ICON.icon = create_error_icon()
        TRAY_ICON.title = "Busy WhatsApp Gateway - Stopped"
    
    TRAY_ICON.menu = create_tray_menu()

def create_tray_menu():
    if not HAS_TRAY:
        return None
    
    return pystray.Menu(
        pystray.MenuItem("Open Dashboard", lambda: open_url('http://localhost:8000/dashboard'), default=True),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Open QR Page", lambda: open_url('http://localhost:3001/qr/page')),
        pystray.MenuItem("Open API Docs", lambda: open_url('http://localhost:8000/docs')),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(
            "Stop Baileys" if SERVER_STATUS['baileys']['running'] else "Start Baileys",
            lambda: stop_server('baileys') if SERVER_STATUS['baileys']['running'] else start_baileys()
        ),
        pystray.MenuItem(
            "Stop FastAPI" if SERVER_STATUS['fastapi']['running'] else "Start FastAPI",
            lambda: stop_server('fastapi') if SERVER_STATUS['fastapi']['running'] else start_fastapi()
        ),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Show Status", show_status),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Exit", stop_tray)
    )

def open_url(url: str):
    import webbrowser
    webbrowser.open(url)
    log('SYSTEM', f'Opened {url}', 'green')

def show_status():
    print("\n" + "="*60)
    for name, status in SERVER_STATUS.items():
        state = colorize("Running", 'green') if status['running'] else colorize("Stopped", 'red')
        pid = f" (PID: {status['pid']})" if status['pid'] else ""
        print(f"  {name.title()}: {state}{pid}")
    print("\n  Dashboard: http://localhost:8000/dashboard")
    print("  QR Code:   http://localhost:3001/qr/page")
    print("  API Docs:  http://localhost:8000/docs")
    print("="*60 + "\n")

def stop_tray():
    stop_all()
    if TRAY_ICON:
        TRAY_ICON.stop()

def ensure_single_instance() -> bool:
    if sys.platform != 'win32':
        return True
    
    try:
        kernel32 = ctypes.windll.kernel32
        mutex = kernel32.CreateMutexW(None, False, "Global\\BusyWhatsAppGateway_Instance")
        if kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
            kernel32.CloseHandle(mutex)
            print("\n" + "="*60)
            print("  BUSY WHATSAPP GATEWAY - ALREADY RUNNING")
            print("="*60)
            print("\n  Check system tray for the green WhatsApp icon.")
            print("  Right-click to access controls.\n")
            input("Press Enter to close this window...")
            return False
        return True
    except:
        return True

def run_console_mode():
    global CONSOLE_MODE
    CONSOLE_MODE = True
    
    print("\n" + colorize("="*60, 'bold'))
    print(colorize("  BUSY WHATSAPP GATEWAY - CONSOLE MODE", 'bold'))
    print(colorize("="*60, 'bold') + "\n")
    
    if not check_prerequisites():
        return 1
    
    threading.Thread(target=write_to_log_file, daemon=True).start()
    
    if not start_baileys():
        log('SYSTEM', 'Failed to start Baileys', 'red')
    
    time.sleep(2)
    
    if not start_fastapi():
        log('SYSTEM', 'Failed to start FastAPI', 'red')
    
    if not SERVER_STATUS['baileys']['running'] and not SERVER_STATUS['fastapi']['running']:
        log('SYSTEM', 'No servers started. Exiting.', 'red')
        return 1
    
    log('SYSTEM', '='*50, 'white')
    log('SYSTEM', 'Dashboard: http://localhost:8000/dashboard', 'green')
    log('SYSTEM', 'QR Code:   http://localhost:3001/qr/page', 'green')
    log('SYSTEM', 'API Docs:  http://localhost:8000/docs', 'green')
    log('SYSTEM', '='*50, 'white')
    log('SYSTEM', 'Press Ctrl+C to stop all servers', 'yellow')
    
    def signal_handler(sig, frame):
        print()
        stop_all()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        while not SHUTDOWN_EVENT.is_set():
            time.sleep(1)
    except KeyboardInterrupt:
        stop_all()
    
    return 0

def run_tray_mode():
    global CONSOLE_MODE, TRAY_ICON
    CONSOLE_MODE = False
    
    if not HAS_TRAY:
        print("ERROR: pystray not installed. Run: pip install pystray pillow")
        return 1
    
    if not check_prerequisites():
        return 1
    
    threading.Thread(target=write_to_log_file, daemon=True).start()
    
    start_baileys()
    time.sleep(2)
    start_fastapi()
    
    TRAY_ICON = pystray.Icon(
        "busy-whatsapp",
        create_tray_icon(),
        "Busy WhatsApp Gateway",
        create_tray_menu()
    )
    
    def on_exit():
        stop_all()
    
    TRAY_ICON.on_exit = on_exit
    TRAY_ICON.run()
    
    return 0

def run_headless_mode():
    global CONSOLE_MODE
    CONSOLE_MODE = False
    
    print("Starting in headless mode (logs to file only)...")
    
    if not check_prerequisites():
        return 1
    
    threading.Thread(target=write_to_log_file, daemon=True).start()
    
    start_baileys()
    time.sleep(2)
    start_fastapi()
    
    log('SYSTEM', 'Running in headless mode. Logs: logs/gateway_*.log', 'green')
    
    signal.pause()
    return 0

def main():
    parser = argparse.ArgumentParser(
        description='Busy WhatsApp Gateway',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Modes:
  (default)    Console mode - visible logs, interactive
  --tray       System tray mode - hidden console, tray icon
  --headless   Background mode - no UI, logs to file only
'''
    )
    parser.add_argument('--tray', action='store_true', help='Run in system tray mode')
    parser.add_argument('--headless', action='store_true', help='Run in headless mode (no UI)')
    
    args = parser.parse_args()
    
    if not ensure_single_instance():
        return 1
    
    if args.tray:
        return run_tray_mode()
    elif args.headless:
        return run_headless_mode()
    else:
        return run_console_mode()

if __name__ == '__main__':
    sys.exit(main())
