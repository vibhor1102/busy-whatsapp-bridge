#!/usr/bin/env python3
"""
Create desktop shortcuts for Busy Whatsapp Bridge
Creates shortcuts for both console mode (with logs) and tray mode.
"""
import os
import sys
import subprocess
from pathlib import Path


def create_shortcut_powershell(name: str, args: str, description: str) -> bool:
    """Create a shortcut using PowerShell."""
    python_exe = sys.executable
    app_dir = Path(__file__).parent.absolute()
    run_py = app_dir / 'run.py'
    
    ps_command = f'''
$WshShell = New-Object -comObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("$env:USERPROFILE\\Desktop\\{name}.lnk")
$Shortcut.TargetPath = "{python_exe}"
$Shortcut.Arguments = '"{run_py}" {args}'
$Shortcut.WorkingDirectory = "{app_dir}"
$Shortcut.Description = "{description}"
$Shortcut.IconLocation = "%SystemRoot%\\system32\\SHELL32.dll,14"
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
    
    print("Creating desktop shortcuts...")
    print()
    
    shortcuts = [
        ("WhatsApp Bridge", "", "Busy Whatsapp Bridge - Console Mode"),
        ("WhatsApp Bridge (Tray)", "--tray", "Busy Whatsapp Bridge - System Tray Mode"),
    ]
    
    success = True
    for name, args, desc in shortcuts:
        if create_shortcut_powershell(name, args, desc):
            print(f"  [OK] {name}")
        else:
            print(f"  [FAIL] {name}")
            success = False
    
    print()
    if success:
        print("Shortcuts created on desktop!")
        print()
        print("  - WhatsApp Bridge: Console mode (shows all logs)")
        print("  - WhatsApp Bridge (Tray): System tray mode (background)")
    else:
        print("Some shortcuts failed. Run 'python run.py' directly.")
    
    try:
        input("\nPress Enter to close...")
    except EOFError:
        pass
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
