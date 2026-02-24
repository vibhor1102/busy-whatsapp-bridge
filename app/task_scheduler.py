#!/usr/bin/env python3
"""
Task Scheduler Manager for Busy Whatsapp Bridge

Manages Windows Task Scheduler integration for auto-start on login.
Runs the application with tray icon using Task Scheduler instead of Windows Service.

Usage:
    python -m app.task_scheduler install    # Install scheduled task
    python -m app.task_scheduler remove     # Remove scheduled task
    python -m app.task_scheduler status     # Check task status
    python -m app.task_scheduler start      # Start task now
    python -m app.task_scheduler stop       # Stop task
"""
import subprocess
import sys
import os
from pathlib import Path
from typing import Optional
import xml.etree.ElementTree as ET


class TaskSchedulerManager:
    """Manages Windows Task Scheduler for Busy Whatsapp Bridge."""
    
    TASK_NAME = "BusyWhatsappBridge"
    TASK_DESCRIPTION = "Busy Whatsapp Bridge - Auto-start with tray icon"
    
    def __init__(self):
        self.app_dir = Path(__file__).parent.parent.absolute()
        self.python_exe = self.app_dir / "venv" / "Scripts" / "pythonw.exe"
        self.run_script = self.app_dir / "run.py"
        self.working_dir = self.app_dir
        
    def _run_schtasks(self, args: list) -> tuple[int, str, str]:
        """Run schtasks.exe command and return result."""
        cmd = ["schtasks.exe"] + args
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore'
            )
            return result.returncode, result.stdout, result.stderr
        except Exception as e:
            return 1, "", str(e)
    
    def is_installed(self) -> bool:
        """Check if the task is already installed."""
        returncode, stdout, _ = self._run_schtasks([
            "/query", "/tn", self.TASK_NAME, "/fo", "list"
        ])
        return returncode == 0 and self.TASK_NAME in stdout
    
    def is_running(self) -> bool:
        """Check if the task is currently running."""
        returncode, stdout, _ = self._run_schtasks([
            "/query", "/tn", self.TASK_NAME, "/fo", "list", "/v"
        ])
        if returncode != 0:
            return False
        return "Running" in stdout or "Running" in stdout
    
    def install(self) -> bool:
        """Install the scheduled task."""
        if self.is_installed():
            print(f"Task '{self.TASK_NAME}' is already installed.")
            print("Use 'remove' first if you want to reinstall.")
            return False
        
        # Create XML task definition
        xml_content = self._create_task_xml()
        xml_path = self.app_dir / "task_definition.xml"
        
        try:
            # Write XML with UTF-16 encoding (required by schtasks)
            xml_path.write_text(xml_content, encoding='utf-16')
            
            # Create task from XML
            returncode, stdout, stderr = self._run_schtasks([
                "/create", "/tn", self.TASK_NAME,
                "/xml", str(xml_path),
                "/f"
            ])
            
            # Clean up XML file
            xml_path.unlink(missing_ok=True)
            
            if returncode == 0:
                print(f"✓ Task '{self.TASK_NAME}' installed successfully!")
                print(f"  The application will auto-start on login with tray icon.")
                return True
            else:
                print(f"✗ Failed to install task:")
                print(f"  {stderr or stdout}")
                return False
                
        except Exception as e:
            print(f"✗ Error installing task: {e}")
            return False
    
    def remove(self) -> bool:
        """Remove the scheduled task."""
        if not self.is_installed():
            print(f"Task '{self.TASK_NAME}' is not installed.")
            return False
        
        returncode, stdout, stderr = self._run_schtasks([
            "/delete", "/tn", self.TASK_NAME, "/f"
        ])
        
        if returncode == 0:
            print(f"✓ Task '{self.TASK_NAME}' removed successfully!")
            return True
        else:
            print(f"✗ Failed to remove task:")
            print(f"  {stderr or stdout}")
            return False
    
    def start(self) -> bool:
        """Start the task now."""
        if not self.is_installed():
            print(f"Task '{self.TASK_NAME}' is not installed.")
            print("Run 'install' first.")
            return False
        
        if self.is_running():
            print(f"Task '{self.TASK_NAME}' is already running.")
            return True
        
        returncode, stdout, stderr = self._run_schtasks([
            "/run", "/tn", self.TASK_NAME
        ])
        
        if returncode == 0:
            print(f"✓ Task '{self.TASK_NAME}' started!")
            print(f"  The tray icon should appear in a few seconds.")
            return True
        else:
            print(f"✗ Failed to start task:")
            print(f"  {stderr or stdout}")
            return False
    
    def stop(self) -> bool:
        """Stop the running task."""
        if not self.is_installed():
            print(f"Task '{self.TASK_NAME}' is not installed.")
            return False
        
        if not self.is_running():
            print(f"Task '{self.TASK_NAME}' is not running.")
            return True
        
        returncode, stdout, stderr = self._run_schtasks([
            "/end", "/tn", self.TASK_NAME
        ])
        
        if returncode == 0:
            print(f"✓ Task '{self.TASK_NAME}' stopped!")
            return True
        else:
            print(f"✗ Failed to stop task:")
            print(f"  {stderr or stdout}")
            return False
    
    def status(self) -> None:
        """Display task status."""
        print(f"\nTask Scheduler Status for '{self.TASK_NAME}':")
        print("=" * 50)
        
        if not self.is_installed():
            print("  Status: Not Installed")
            print("  The application will NOT auto-start on login.")
            print("\n  To enable auto-start, run: manage-task.bat")
            print("  Or: python -m app.task_scheduler install")
        else:
            returncode, stdout, _ = self._run_schtasks([
                "/query", "/tn", self.TASK_NAME, "/fo", "list", "/v"
            ])
            
            if returncode == 0:
                # Parse key info from output
                lines = stdout.strip().split('\n')
                for line in lines:
                    line = line.strip()
                    if ':' in line:
                        key, value = line.split(':', 1)
                        key = key.strip()
                        value = value.strip()
                        if key in ['Task Name', 'Task State', 'Last Run Time', 
                                  'Next Run Time', 'Author', 'Task Status']:
                            print(f"  {key}: {value}")
            else:
                print("  Status: Installed (details unavailable)")
            
            print("\n  Auto-start on login: ENABLED")
            print("  Tray icon: Will appear on startup")
            print("\n  To disable auto-start, run: manage-task.bat")
        
        print()
    
    def _create_task_xml(self) -> str:
        """Create Task Scheduler XML definition."""
        # Use escaped backslashes for paths in XML
        python_path = str(self.python_exe).replace('\\', '\\\\')
        script_path = str(self.run_script).replace('\\', '\\\\')
        working_dir = str(self.working_dir).replace('\\', '\\\\')
        
        xml = f'''<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>{self.TASK_DESCRIPTION}</Description>
    <Author>BusyWhatsappBridge</Author>
  </RegistrationInfo>
  <Triggers>
    <LogonTrigger>
      <Enabled>true</Enabled>
    </LogonTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <IdleSettings>
      <StopOnIdleEnd>false</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <Priority>7</Priority>
    <RestartOnFailure>
      <Interval>PT1M</Interval>
      <Count>3</Count>
    </RestartOnFailure>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{python_path}</Command>
      <Arguments>{script_path} --tray</Arguments>
      <WorkingDirectory>{working_dir}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>'''
        return xml


def main():
    """Main entry point for command-line usage."""
    if len(sys.argv) < 2:
        print("Usage: python -m app.task_scheduler [install|remove|status|start|stop]")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    manager = TaskSchedulerManager()
    
    if command == "install":
        success = manager.install()
    elif command == "remove":
        success = manager.remove()
    elif command == "status":
        manager.status()
        success = True
    elif command == "start":
        success = manager.start()
    elif command == "stop":
        success = manager.stop()
    else:
        print(f"Unknown command: {command}")
        print("Usage: python -m app.task_scheduler [install|remove|status|start|stop]")
        sys.exit(1)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
