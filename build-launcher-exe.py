#!/usr/bin/env python3
"""
Build Windows EXE Launcher for Busy Whatsapp Bridge

Creates BusyWhatsappBridge.exe that users can double-click to run.
This EXE embeds the Python interpreter and all necessary logic.
"""
import subprocess
import sys
from pathlib import Path


def main():
    print("Building Busy Whatsapp Bridge EXE Launcher...")
    print("=" * 60)
    
    script_dir = Path(__file__).parent.absolute()
    
    # Check if PyInstaller is installed
    try:
        import PyInstaller
        print("PyInstaller already installed")
    except ImportError:
        print("Installing PyInstaller...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller", "-q"], check=True)
    
    print("\nBuilding EXE...")
    print("This creates BusyWhatsappBridge.exe that users can double-click")
    print()
    
    # Check for icon file
    icon_file = script_dir / "app.ico"
    
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",                    # Single EXE file
        "--windowed",                   # No console window for GUI apps
        "--name", "BusyWhatsappBridge",
        "--distpath", ".",
        "--workpath", "build-exe",
        "--specpath", "build-exe",
        "--clean",
    ]
    
    if icon_file.exists():
        cmd.extend(["--icon", str(icon_file)])
    
    cmd.append(str(script_dir / "Start-Gateway.py"))
    
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        exe_path = script_dir / "BusyWhatsappBridge.exe"
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print("\n" + "=" * 60)
            print("SUCCESS!")
            print("=" * 60)
            print(f"\nCreated: BusyWhatsappBridge.exe ({size_mb:.1f} MB)")
            print("\nThis EXE can be:")
            print("  - Double-clicked by users")
            print("  - Added to Start Menu")
            print("  - Added to Desktop")
            print("  - Set to auto-start on login")
            print("\nNo Python installation required on user machine!")
            
            # Sign the EXE
            print("\nSigning EXE...")
            try:
                subprocess.run([
                    r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
                    "-NoProfile",
                    "-NonInteractive",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File", str(script_dir / "scripts" / "manage-signing.ps1"), 
                    "-Action", "sign", 
                    "-File", str(exe_path)
                ], check=True)
            except subprocess.CalledProcessError:
                print("ERROR: Signing failed for BusyWhatsappBridge.exe.")
                return 1

            return 0
    
    print("\nBuild failed!")
    return 1


if __name__ == "__main__":
    sys.exit(main())
