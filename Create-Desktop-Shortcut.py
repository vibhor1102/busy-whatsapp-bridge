#!/usr/bin/env python3
"""
Create desktop shortcut for Busy WhatsApp Gateway
"""
import os
import sys
from pathlib import Path

def create_shortcut():
    """Create Windows desktop shortcut."""
    if sys.platform != 'win32':
        print("This script only works on Windows")
        return False
    
    try:
        import winshell
        from win32com.client import Dispatch
        
        # Get paths
        desktop = winshell.desktop()
        app_dir = Path(__file__).parent.absolute()
        bat_file = app_dir / 'Start-Gateway.bat'
        icon_file = app_dir / 'assets' / 'gateway.ico'
        
        # Create shortcut
        shortcut_path = os.path.join(desktop, "Busy WhatsApp Gateway.lnk")
        shell = Dispatch('WScript.Shell')
        shortcut = shell.CreateShortCut(shortcut_path)
        shortcut.Targetpath = str(bat_file)
        shortcut.WorkingDirectory = str(app_dir)
        
        # Set icon if exists, otherwise use default
        if icon_file.exists():
            shortcut.IconLocation = str(icon_file)
        else:
            # Use system icon
            shortcut.IconLocation = r"%SystemRoot%\system32\SHELL32.dll,14"
        
        shortcut.Description = "Busy WhatsApp Gateway Manager"
        shortcut.save()
        
        print(f"✓ Shortcut created on desktop: {shortcut_path}")
        return True
        
    except ImportError:
        print("Note: winshell not installed, using alternative method...")
        return create_shortcut_manual()
    except Exception as e:
        print(f"Error creating shortcut: {e}")
        return create_shortcut_manual()

def create_shortcut_manual():
    """Manual shortcut creation using PowerShell."""
    try:
        import subprocess
        
        app_dir = Path(__file__).parent.absolute()
        bat_file = app_dir / 'Start-Gateway.bat'
        
        # PowerShell command to create shortcut
        ps_command = rf'''
        $WshShell = New-Object -comObject WScript.Shell
        $Shortcut = $WshShell.CreateShortcut("$env:USERPROFILE\Desktop\Busy WhatsApp Gateway.lnk")
        $Shortcut.TargetPath = "{bat_file}"
        $Shortcut.WorkingDirectory = "{app_dir}"
        $Shortcut.Description = "Busy WhatsApp Gateway Manager"
        $Shortcut.IconLocation = "%SystemRoot%\system32\SHELL32.dll,14"
        $Shortcut.Save()
        '''
        
        result = subprocess.run(
            ['powershell', '-Command', ps_command],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("✓ Desktop shortcut created successfully!")
            print("  You can now double-click 'Busy WhatsApp Gateway' on your desktop")
            return True
        else:
            print(f"Error: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    print("="*60)
    print("Busy WhatsApp Gateway - Desktop Shortcut Creator")
    print("="*60)
    print()
    
    if sys.platform != 'win32':
        print("This script is designed for Windows")
        print("On other systems, please run Start-Gateway.bat directly")
        return 1
    
    print("Creating desktop shortcut...")
    print()
    
    if create_shortcut():
        print()
        print("✓ Success! You can now:")
        print("  1. Close this window")
        print("  2. Find 'Busy WhatsApp Gateway' on your desktop")
        print("  3. Double-click it to start the manager")
        print()
        input("Press Enter to close...")
        return 0
    else:
        print()
        print("✗ Failed to create shortcut")
        print("  You can still run Start-Gateway.bat directly")
        input("\nPress Enter to close...")
        return 1

if __name__ == "__main__":
    sys.exit(main())
