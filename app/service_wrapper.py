import sys
import os
import servicemanager
import win32serviceutil
import win32service
import win32event
import win32evtlog
import win32evtlogutil
import logging
import logging.handlers
from pathlib import Path

# Add project directory to path
BASE_DIR = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(BASE_DIR))

from app.main import app
import uvicorn


class BusyWhatsappBridgeService(win32serviceutil.ServiceFramework):
    """
    Windows Service for Busy Whatsapp Bridge.
    
    This service runs the FastAPI application as a Windows service,
    providing automatic startup, crash recovery, and event logging.
    """
    
    _svc_name_ = "BusyWhatsappBridge"
    _svc_display_name_ = "Busy Whatsapp Bridge"
    _svc_description_ = "Integrates Busy Accounting Software with WhatsApp/SMS providers via webhook API"
    
    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.is_alive = True
        
        # Setup logging
        self.setup_logging()
        self.logger = logging.getLogger(__name__)
        
    def setup_logging(self):
        """Configure logging for Windows service."""
        # Use install directory for logs (overwritten on updates)
        log_dir = BASE_DIR / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        # File handler with rotation
        file_handler = logging.handlers.RotatingFileHandler(
            log_dir / "service.log",
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(logging.INFO)
        
        # Windows Event Log handler
        event_handler = logging.handlers.NTEventLogHandler(
            appname="BusyWhatsappBridge"
        )
        event_handler.setLevel(logging.WARNING)
        
        # Console handler (for debugging)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        root_logger.addHandler(file_handler)
        root_logger.addHandler(event_handler)
        root_logger.addHandler(console_handler)
    
    def SvcStop(self):
        """Stop the service."""
        self.logger.info("Service stop requested")
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        self.is_alive = False
        win32event.SetEvent(self.stop_event)
    
    def SvcDoRun(self):
        """Run the service."""
        self.logger.info("Service starting...")
        self.ReportServiceStatus(win32service.SERVICE_START_PENDING)
        
        try:
            # Log service start to Windows Event Log
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STARTED,
                (self._svc_name_, '')
            )
            
            self.ReportServiceStatus(win32service.SERVICE_RUNNING)
            self.logger.info("Service is now running on http://0.0.0.0:8000")
            
            # Run uvicorn server
            import threading
            server_thread = threading.Thread(
                target=self.run_server,
                daemon=True
            )
            server_thread.start()
            
            # Wait for stop signal
            while self.is_alive:
                rc = win32event.WaitForSingleObject(self.stop_event, 5000)
                if rc == win32event.WAIT_OBJECT_0:
                    break
            
            self.logger.info("Service stopped")
            
        except Exception as e:
            self.logger.error(f"Service error: {e}", exc_info=True)
            servicemanager.LogErrorMsg(
                f"Service error: {str(e)}"
            )
            raise
    
    def run_server(self):
        """Run the uvicorn server."""
        try:
            uvicorn.run(
                app,
                host="0.0.0.0",
                port=8000,
                log_level="info",
                access_log=True
            )
        except Exception as e:
            self.logger.error(f"Server error: {e}", exc_info=True)


def cmd_install():
    """Install the Windows service."""
    try:
        win32serviceutil.InstallService(
            BusyWhatsappBridgeService.__class__,
            BusyWhatsappBridgeService._svc_name_,
            BusyWhatsappBridgeService._svc_display_name_,
            startType=win32service.SERVICE_AUTO_START
        )
        print(f"✓ Service '{BusyWhatsappBridgeService._svc_name_}' installed successfully")
        print(f"  Display Name: {BusyWhatsappBridgeService._svc_display_name_}")
        print(f"  Start Type: Automatic")
        print("\nTo start the service, run:")
        print(f"  python app\\service_wrapper.py start")
    except Exception as e:
        print(f"✗ Failed to install service: {e}")
        sys.exit(1)


def cmd_remove():
    """Remove the Windows service."""
    try:
        win32serviceutil.RemoveService(BusyWhatsappBridgeService._svc_name_)
        print(f"✓ Service '{BusyWhatsappBridgeService._svc_name_}' removed successfully")
    except Exception as e:
        print(f"✗ Failed to remove service: {e}")
        sys.exit(1)


def cmd_start():
    """Start the Windows service."""
    try:
        win32serviceutil.StartService(BusyWhatsappBridgeService._svc_name_)
        print(f"✓ Service '{BusyWhatsappBridgeService._svc_name_}' started")
        print("  Check status with: python app\\service_wrapper.py status")
    except Exception as e:
        print(f"✗ Failed to start service: {e}")
        sys.exit(1)


def cmd_stop():
    """Stop the Windows service."""
    try:
        win32serviceutil.StopService(BusyWhatsappBridgeService._svc_name_)
        print(f"✓ Service '{BusyWhatsappBridgeService._svc_name_}' stopped")
    except Exception as e:
        print(f"✗ Failed to stop service: {e}")
        sys.exit(1)


def cmd_restart():
    """Restart the Windows service."""
    cmd_stop()
    cmd_start()


def cmd_status():
    """Check service status."""
    try:
        status = win32serviceutil.QueryServiceStatus(BusyWhatsappBridgeService._svc_name_)
        status_map = {
            win32service.SERVICE_STOPPED: "Stopped",
            win32service.SERVICE_START_PENDING: "Starting",
            win32service.SERVICE_STOP_PENDING: "Stopping",
            win32service.SERVICE_RUNNING: "Running",
            win32service.SERVICE_CONTINUE_PENDING: "Continue Pending",
            win32service.SERVICE_PAUSE_PENDING: "Pause Pending",
            win32service.SERVICE_PAUSED: "Paused",
        }
        current_status = status_map.get(status[1], f"Unknown ({status[1]})")
        print(f"Service '{BusyWhatsappBridgeService._svc_name_}': {current_status}")
        
        if status[1] == win32service.SERVICE_RUNNING:
            print("  API Endpoint: http://localhost:8000")
            print("  Documentation: http://localhost:8000/docs")
    except Exception as e:
        print(f"✗ Service not installed or error: {e}")


if __name__ == '__main__':
    if len(sys.argv) == 1:
        # No arguments - run as service
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(BusyWhatsappBridgeService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        # Command line arguments
        command = sys.argv[1].lower()
        
        commands = {
            'install': cmd_install,
            'remove': cmd_remove,
            'start': cmd_start,
            'stop': cmd_stop,
            'restart': cmd_restart,
            'status': cmd_status,
        }
        
        if command in commands:
            commands[command]()
        else:
            print(f"Unknown command: {command}")
            print(f"\nUsage: python app\\service_wrapper.py [command]")
            print(f"\nCommands:")
            print(f"  install   - Install the Windows service")
            print(f"  remove    - Remove the Windows service")
            print(f"  start     - Start the service")
            print(f"  stop      - Stop the service")
            print(f"  restart   - Restart the service")
            print(f"  status    - Check service status")
            print(f"\nOr run without arguments to start as a service")
            sys.exit(1)
