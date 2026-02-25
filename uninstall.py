#!/usr/bin/env python3
"""
Uninstall Busy Whatsapp Bridge

Safely removes the application while preserving user choice about data.

Usage:
    python uninstall.py                    # Interactive uninstall
    python uninstall.py --silent           # Silent (keep data)
    python uninstall.py --purge            # Remove everything including data
"""
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def get_program_dir() -> Path:
    """Get the program installation directory."""
    return Path(__file__).parent.absolute()


def get_local_appdata_dir() -> Path:
    """Get the Local AppData directory for machine-specific data."""
    appdata = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local'))
    return appdata / "BusyWhatsappBridge"


def get_roaming_appdata_dir() -> Path:
    """Get the Roaming AppData directory for user configuration."""
    appdata = Path(os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming'))
    return appdata / "BusyWhatsappBridge"


def stop_running_processes():
    """Stop any running Busy Whatsapp Bridge processes."""
    print("Stopping any running processes...")
    
    # Stop Task Scheduler task
    try:
        subprocess.run(
            ["schtasks", "/end", "/tn", "BusyWhatsappBridge"],
            capture_output=True,
            timeout=5
        )
    except:
        pass
    
    # Kill Python processes running our app
    try:
        subprocess.run(
            ["taskkill", "/F", "/IM", "python.exe", "/FI", "WINDOWTITLE eq Busy Whatsapp Bridge"],
            capture_output=True,
            timeout=5
        )
    except:
        pass


def remove_task_scheduler_entry():
    """Remove Task Scheduler entry."""
    print("Removing Task Scheduler entry...")
    try:
        result = subprocess.run(
            ["schtasks", "/delete", "/tn", "BusyWhatsappBridge", "/f"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            print("  Task Scheduler entry removed")
        else:
            print("  Task Scheduler entry not found (may not have been installed)")
    except Exception as e:
        print(f"  Warning: Could not remove Task Scheduler entry: {e}")


def remove_shortcuts():
    """Remove desktop and start menu shortcuts."""
    print("Removing shortcuts...")
    
    # Desktop shortcuts (multiple possible names)
    desktop = Path.home() / "Desktop"
    desktop_shortcuts = [
        "Busy Whatsapp Bridge.lnk",
        "Busy Whatsapp Bridge (Tray).lnk",
        "WhatsApp Bridge.lnk",  # Legacy name
        "WhatsApp Bridge (Tray).lnk",  # Legacy name
    ]
    
    for shortcut_name in desktop_shortcuts:
        shortcut = desktop / shortcut_name
        if shortcut.exists():
            shortcut.unlink()
            print(f"  Desktop shortcut removed: {shortcut_name}")
    
    # Start Menu - check both user and all-users locations
    start_menu_paths = [
        Path(os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming')) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Busy Whatsapp Bridge",
        Path(os.environ.get('PROGRAMDATA', Path.home().parent / 'ProgramData')) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Busy Whatsapp Bridge",
    ]
    
    for start_menu in start_menu_paths:
        if start_menu.exists():
            shutil.rmtree(start_menu)
            print(f"  Start Menu folder removed: {start_menu}")


def remove_program_files(program_dir: Path):
    """Remove program files."""
    print(f"Removing program files from: {program_dir}")
    
    if program_dir.exists():
        try:
            shutil.rmtree(program_dir)
            print("  Program files removed")
        except Exception as e:
            print(f"  Error removing program files: {e}")
            print("  You may need to manually delete the folder")


def remove_appdata(appdata_dir: Path, purge: bool = False):
    """Remove AppData (user data)."""
    if purge:
        print(f"Removing all data from: {appdata_dir}")
        if appdata_dir.exists():
            shutil.rmtree(appdata_dir)
            print("  All data removed")
    else:
        print("Preserving user data (configuration, databases, logs)")
        print(f"  Data location: {appdata_dir}")
        print("  You can manually delete this folder if needed")


def main():
    parser = argparse.ArgumentParser(description="Uninstall Busy Whatsapp Bridge")
    parser.add_argument(
        "--silent", "-s",
        action="store_true",
        help="Silent mode (no prompts)"
    )
    parser.add_argument(
        "--purge", "-p",
        action="store_true",
        help="Remove everything including user data"
    )
    
    args = parser.parse_args()
    
    program_dir = get_program_dir()
    local_appdata_dir = get_local_appdata_dir()
    roaming_appdata_dir = get_roaming_appdata_dir()
    
    print("=" * 60)
    print("Busy Whatsapp Bridge Uninstaller")
    print("=" * 60)
    print()
    
    if not args.silent:
        print(f"This will uninstall Busy Whatsapp Bridge from:")
        print(f"  {program_dir}")
        print()
        
        if args.purge:
            print("WARNING: --purge flag specified!")
            print("This will ALSO delete all user data including:")
            print(f"  Config (Roaming): {roaming_appdata_dir}")
            print(f"  Data (Local): {local_appdata_dir}")
            print()
            response = input("Are you sure? Type 'yes' to continue: ")
            if response.lower() != 'yes':
                print("Uninstall cancelled.")
                return 1
        else:
            print("User data will be preserved at:")
            print(f"  Config (Roaming): {roaming_appdata_dir}")
            print(f"  Data (Local): {local_appdata_dir}")
            print()
            response = input("Continue with uninstall? [Y/n]: ")
            if response and response.lower() not in ('y', 'yes'):
                print("Uninstall cancelled.")
                return 1
        
        print()
    
    # Perform uninstall
    stop_running_processes()
    remove_task_scheduler_entry()
    remove_shortcuts()
    remove_program_files(program_dir)
    
    # Remove both roaming (config) and local (data) AppData
    remove_appdata(roaming_appdata_dir, purge=args.purge)
    remove_appdata(local_appdata_dir, purge=args.purge)
    
    print()
    print("=" * 60)
    print("Uninstall completed!")
    print("=" * 60)
    
    if not args.purge:
        print()
        print("Your data has been preserved at:")
        print(f"  Config (Roaming): {roaming_appdata_dir}")
        print(f"  Data (Local): {local_appdata_dir}")
        print()
        print("To completely remove all traces, delete these folders manually.")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
