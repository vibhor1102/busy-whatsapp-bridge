#!/usr/bin/env python3
"""
Busy Whatsapp Bridge - Main Entry Point

This is the primary executable entry point for the application.
It locates the bundled Python virtual environment and runs the main application.

Usage:
    BusyWhatsappBridge.exe                    # Mandatory tray mode
    BusyWhatsappBridge.exe --version          # Show version

This file should be compiled to an .exe using PyInstaller for distribution.
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path


def get_executable_dir() -> Path:
    """Get the directory containing this executable/script."""
    if getattr(sys, 'frozen', False):
        # Running as compiled .exe
        return Path(sys.executable).parent
    else:
        # Running as .py script
        return Path(__file__).parent.absolute()


def find_venv_python(program_dir: Path) -> Path:
    """Find the virtual environment Python executable."""
    # Check for venv in program directory
    venv_python = program_dir / "venv" / "Scripts" / "python.exe"
    
    if venv_python.exists():
        return venv_python
    
    # Check for bundled Python (fallback)
    bundled_python = program_dir / "python" / "python.exe"
    if bundled_python.exists():
        return bundled_python
    
    return None


def check_setup_complete(program_dir: Path) -> bool:
    """Check if initial setup has been completed."""
    venv_dir = program_dir / "venv"
    return venv_dir.exists() and (venv_dir / "Scripts" / "python.exe").exists()


def run_setup_if_needed(program_dir: Path, silent: bool = False) -> bool:
    """Run setup if virtual environment doesn't exist."""
    if check_setup_complete(program_dir):
        return True
    
    print("First-time setup required...")
    print("Running setup.py...")
    
    setup_script = program_dir / "setup.py"
    bundled_python = program_dir / "python" / "python.exe"
    
    if not setup_script.exists():
        print("ERROR: setup.py not found!")
        return False

    if not bundled_python.exists():
        print("ERROR: Bundled Python not found!")
        return False

    try:
        args = [str(bundled_python), str(setup_script)]
        if silent:
            args.append("--silent")

        result = subprocess.run(args, check=True)
        return result.returncode == 0
    except subprocess.CalledProcessError:
        print("ERROR: Setup failed!")
        return False


def cleanup_existing_runtime() -> None:
    """Stop stale BusyWhatsappBridge runtime processes before startup."""
    cleanup_cmd = (
        "Get-CimInstance Win32_Process | "
        "Where-Object { $_.CommandLine -match 'BusyWhatsappBridge' -and "
        "$_.CommandLine -match 'run\\.py|baileys-server\\\\server\\.js|uvicorn app\\.main:app' } | "
        "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }; "
        "$ports = @(3001,8000); "
        "foreach($port in $ports){ "
        "Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | "
        "Select-Object -ExpandProperty OwningProcess -Unique | "
        "ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue } }"
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", cleanup_cmd],
        capture_output=True,
        text=True
    )


def main():
    parser = argparse.ArgumentParser(
        description="Busy Whatsapp Bridge - WhatsApp Integration for Busy Accounting",
        prog="BusyWhatsappBridge"
    )
    
    parser.add_argument(
        "--version", "-v",
        action="store_true",
        help="Show version information"
    )
    
    parser.add_argument(
        "--setup", "-s",
        action="store_true",
        help="Run setup/repair (recreate virtual environment)"
    )
    
    # Parse known args to pass remaining to run.py
    args, remaining = parser.parse_known_args()
    
    program_dir = get_executable_dir()
    
    # Show version
    if args.version:
        try:
            sys.path.insert(0, str(program_dir))
            from app.version import get_version
            print(f"Busy Whatsapp Bridge v{get_version()}")
            print(f"Installation directory: {program_dir}")
        except ImportError:
            print("Busy Whatsapp Bridge (version unknown)")
        return 0
    
    # Run setup if requested
    if args.setup:
        setup_script = program_dir / "setup.py"
        bundled_python = program_dir / "python" / "python.exe"
        
        if not bundled_python.exists():
            print("ERROR: Bundled Python not found!")
            return 1
        
        subprocess.run([str(bundled_python), str(setup_script)] + remaining)
        return 0
    
    # Check/setup virtual environment
    if not check_setup_complete(program_dir):
        print("First-time setup required.")
        print("Running setup...")
        if not run_setup_if_needed(program_dir, silent=True):
            print("\nSetup failed. Please run setup.py manually:")
            print(f"  cd \"{program_dir}\"")
            print(f"  python setup.py")
            input("\nPress Enter to exit...")
            return 1
    
    # Find Python executable
    python_exe = find_venv_python(program_dir)
    if not python_exe:
        print("ERROR: Virtual environment not found!")
        print("Please run setup.py to install:")
        print(f"  cd \"{program_dir}\"")
        print(f"  python setup.py")
        input("\nPress Enter to exit...")
        return 1
    
    # Find run.py
    run_script = program_dir / "run.py"
    if not run_script.exists():
        print(f"ERROR: run.py not found in {program_dir}")
        input("\nPress Enter to exit...")
        return 1
    
    # Build command
    cmd = [str(python_exe), str(run_script)]
    
    # Filter out any legacy mode flags from pass-through arguments.
    disallowed_mode_flags = {"--tray", "-t", "--headless", "-H"}
    remaining = [arg for arg in remaining if arg not in disallowed_mode_flags]
    cmd.extend(remaining)
    
    # Run the application
    try:
        # Ensure stale background instances don't block tray startup
        cleanup_existing_runtime()

        # Change to program directory
        os.chdir(program_dir)
        
        # Execute run.py
        result = subprocess.run(cmd)
        return result.returncode
        
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        return 130
    except Exception as e:
        print(f"ERROR: Failed to start application: {e}")
        input("\nPress Enter to exit...")
        return 1


if __name__ == "__main__":
    sys.exit(main())
