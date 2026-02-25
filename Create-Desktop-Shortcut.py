#!/usr/bin/env python3
"""
Create desktop shortcuts for Busy Whatsapp Bridge
Creates shortcuts for both console mode and tray mode.
"""
import os
import sys
import subprocess
from pathlib import Path


def create_shortcut_powershell(name: str, target: str, args: str, description: str, icon_idx: int = 14) -> bool:
    """Create a shortcut using PowerShell."""
    app_dir = Path(__file__).parent.absolute()
    
    ps_command = f'''
$WshShell = New-Object -comObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("$env:USERPROFILE\\Desktop\\{name}.lnk")
$Shortcut.TargetPath = "{target}"
$Shortcut.Arguments = "{args}"
$Shortcut.WorkingDirectory = "{app_dir}"
$Shortcut.Description = "{description}"
$Shortcut.IconLocation = "%SystemRoot%\\system32\\SHELL32.dll,{icon_idx}"
$Shortcut.Save()
Write-Host "Created: {name}"
'''
    
    result = subprocess.run(
        ['powershell', '-Command', ps_command],
        capture_output=True,
        text=True
    )
    
    return result.returncode == 0


def main():
    print("="*60)
    print("  Busy Whatsapp Bridge - Shortcut Creator")
    print("="*60)
    print()
    
    if sys.platform != 'win32':
        print("This script is designed for Windows")
        return 1
    
    app_dir = Path(__file__).parent.absolute()
    
    # Use bundled Python from venv if available, otherwise fall back to system Python
    venv_python = app_dir / 'venv' / 'Scripts' / 'python.exe'
    if venv_python.exists():
        python_exe = str(venv_python)
    else:
        python_exe = sys.executable
    
    # Use Start-Gateway.py as the entry point
    start_gateway = app_dir / 'Start-Gateway.py'
    if not start_gateway.exists():
        print(f"[ERROR] Start-Gateway.py not found in {app_dir}")
        print("Please ensure the application is properly installed.")
        input("\nPress Enter to close...")
        return 1
    
    print("Creating desktop shortcuts...")
    print(f"Using: {python_exe}")
    print()
    
    shortcuts = [
        (
            "Busy Whatsapp Bridge", 
            python_exe,
            f'"{start_gateway}"',
            "Busy Whatsapp Bridge - Console Mode",
            14
        ),
        (
            "Busy Whatsapp Bridge (Tray)", 
            python_exe,
            f'"{start_gateway}" --tray',
            "Busy Whatsapp Bridge - System Tray Mode",
            14
        ),
    ]
    
    success = True
    for name, target, args, desc, icon in shortcuts:
        if create_shortcut_powershell(name, target, args, desc, icon):
            print(f"  [OK] {name}")
        else:
            print(f"  [FAIL] {name}")
            success = False
    
    print()
    if success:
        print("Shortcuts created on desktop!")
        print()
        print("  - Busy Whatsapp Bridge: Console mode (shows all logs)")
        print("  - Busy Whatsapp Bridge (Tray): System tray mode (background)")
    else:
        print("Some shortcuts failed. You can still run the application from Start Menu.")
    
    try:
        input("\nPress Enter to close...")
    except EOFError:
        pass
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
