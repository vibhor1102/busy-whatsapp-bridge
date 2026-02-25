#!/usr/bin/env python3
"""
Build Standalone EXE for Busy Whatsapp Bridge

Creates a TRULY standalone Windows executable that includes:
- Python runtime
- Virtual environment with all dependencies
- Application code
- Baileys server
- Dashboard files
- All configuration templates

The resulting EXE is self-contained and can be run from anywhere.

Output:
    dist/BusyWhatsappBridge-Standalone.exe (~80-100MB)
    
Usage:
    python build-standalone-exe.py
    
Note: This creates a large EXE (~80-100MB) but it's completely portable.
"""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def get_project_dir():
    """Get project root directory."""
    return Path(__file__).parent.absolute()


def prepare_build_dir(build_dir: Path):
    """Prepare temporary build directory with all files."""
    print("Preparing build directory...")
    project_dir = get_project_dir()
    
    # Create structure
    (build_dir / "app").mkdir(parents=True, exist_ok=True)
    (build_dir / "baileys-server").mkdir(parents=True, exist_ok=True)
    (build_dir / "python").mkdir(parents=True, exist_ok=True)
    (build_dir / "venv").mkdir(parents=True, exist_ok=True)
    (build_dir / "dashboard").mkdir(parents=True, exist_ok=True)
    
    # Copy application code
    print("  Copying app/...")
    if (project_dir / "app").exists():
        shutil.copytree(project_dir / "app", build_dir / "app", dirs_exist_ok=True)
    
    # Copy Baileys server
    print("  Copying baileys-server/...")
    if (project_dir / "baileys-server").exists():
        shutil.copytree(project_dir / "baileys-server", build_dir / "baileys-server", dirs_exist_ok=True)
    
    # Copy bundled Python
    print("  Copying python/...")
    if (project_dir / "python").exists():
        shutil.copytree(project_dir / "python", build_dir / "python", dirs_exist_ok=True)
    
    # Copy virtual environment
    print("  Copying venv/...")
    if (project_dir / "venv").exists():
        shutil.copytree(project_dir / "venv", build_dir / "venv", dirs_exist_ok=True)
    
    # Copy dashboard
    print("  Copying dashboard/...")
    if (project_dir / "dashboard").exists():
        shutil.copytree(project_dir / "dashboard", build_dir / "dashboard", dirs_exist_ok=True)
    
    # Copy essential files
    print("  Copying configuration files...")
    for file in ["conf.json.example", "requirements.txt", "LICENSE", "README.md"]:
        src = project_dir / file
        if src.exists():
            shutil.copy2(src, build_dir / file)
    
    # Create launcher script
    print("  Creating launcher...")
    launcher_code = '''
import os
import sys
import subprocess
from pathlib import Path

def main():
    # Get the directory where the EXE is running
    if getattr(sys, 'frozen', False):
        # Running as compiled EXE
        exe_dir = Path(sys._MEIPASS)
    else:
        # Running as script
        exe_dir = Path(__file__).parent
    
    # Find Python executable
    python_exe = exe_dir / "venv" / "Scripts" / "python.exe"
    if not python_exe.exists():
        python_exe = exe_dir / "python" / "python.exe"
    
    if not python_exe.exists():
        print("ERROR: Python not found in bundled application")
        input("Press Enter to exit...")
        return 1
    
    # Find and run Start-Gateway.py
    run_script = exe_dir / "Start-Gateway.py"
    if not run_script.exists():
        print("ERROR: Start-Gateway.py not found")
        input("Press Enter to exit...")
        return 1
    
    # Change to exe directory and run
    os.chdir(exe_dir)
    result = subprocess.run([str(python_exe), str(run_script)] + sys.argv[1:])
    return result.returncode

if __name__ == "__main__":
    sys.exit(main())
'''
    
    (build_dir / "launcher.py").write_text(launcher_code)
    
    # Copy Start-Gateway.py
    if (project_dir / "Start-Gateway.py").exists():
        shutil.copy2(project_dir / "Start-Gateway.py", build_dir / "Start-Gateway.py")
    
    print("Build directory ready!")
    return build_dir / "launcher.py"


def build_exe(launcher_script: Path, build_dir: Path):
    """Build the standalone EXE using PyInstaller."""
    print("\nBuilding standalone EXE with PyInstaller...")
    print("This may take several minutes...")
    
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",                    # Single EXE file
        "--windowed",                   # No console window
        "--name", "BusyWhatsappBridge-Standalone",
        "--distpath", "dist",
        "--workpath", "build-exe",
        "--specpath", ".",
        "--clean",                      # Clean build
        # Add all data directories
        "--add-data", f"{build_dir / 'app'};app",
        "--add-data", f"{build_dir / 'baileys-server'};baileys-server",
        "--add-data", f"{build_dir / 'python'};python",
        "--add-data", f"{build_dir / 'venv'};venv",
        "--add-data", f"{build_dir / 'dashboard'};dashboard",
        "--add-data", f"{build_dir / 'conf.json.example'};.",
        "--add-data", f"{build_dir / 'requirements.txt'};.",
        "--add-data", f"{build_dir / 'LICENSE'};.",
        "--add-data", f"{build_dir / 'README.md'};.",
        "--add-data", f"{build_dir / 'Start-Gateway.py'};.",
        str(launcher_script)
    ]
    
    result = subprocess.run(cmd)
    return result.returncode == 0


def main():
    print("=" * 70)
    print("Busy Whatsapp Bridge - Standalone EXE Builder")
    print("=" * 70)
    print()
    print("This creates a single EXE file containing:")
    print("  - Python runtime (embedded)")
    print("  - Virtual environment with all dependencies")
    print("  - Application code")
    print("  - Baileys server")
    print("  - Dashboard files")
    print()
    print("Expected size: 80-100 MB")
    print("=" * 70)
    print()
    
    # Check if PyInstaller is installed
    try:
        import PyInstaller
        print("PyInstaller found")
    except ImportError:
        print("Installing PyInstaller...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
    
    # Create temporary build directory
    with tempfile.TemporaryDirectory() as tmpdir:
        build_dir = Path(tmpdir)
        
        # Prepare files
        launcher_script = prepare_build_dir(build_dir)
        
        # Build EXE
        if build_exe(launcher_script, build_dir):
            print("\n" + "=" * 70)
            print("SUCCESS!")
            print("=" * 70)
            print()
            
            output_exe = Path("dist") / "BusyWhatsappBridge-Standalone.exe"
            if output_exe.exists():
                size_mb = output_exe.stat().st_size / (1024 * 1024)
                print(f"Output: {output_exe}")
                print(f"Size: {size_mb:.1f} MB")
                print()
                print("This is a TRUE standalone EXE!")
                print("You can copy just this file and run it anywhere.")
                print("No installation needed.")
                print()
                print("Test it:")
                print(f"  {output_exe} --version")
                print(f"  {output_exe} --tray")
            
            return 0
        else:
            print("\n" + "=" * 70)
            print("BUILD FAILED!")
            print("=" * 70)
            return 1


if __name__ == "__main__":
    sys.exit(main())
