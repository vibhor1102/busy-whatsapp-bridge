#!/usr/bin/env python3
"""
Dashboard Build Manager
======================

Handles dashboard building intelligently for both development and production workflows.

Usage:
    python check-dashboard-build.py [--dev] [--build] [--check]

Modes:
    --check    : Just check if dashboard is built (default)
    --dev      : Start Vite dev server for hot-reload development
    --build    : Build production dashboard if needed or forced
    --force    : Force rebuild even if already built

Exit Codes:
    0 : Dashboard ready (built or building)
    1 : Dashboard not built and --build not specified
    2 : Build failed
"""

import argparse
import subprocess
import sys
import os
import time
from pathlib import Path
from datetime import datetime


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.absolute()


def get_dashboard_path() -> Path:
    """Get the dashboard-react directory path."""
    return get_project_root() / "dashboard-react"


def get_dist_path() -> Path:
    """Get the dist directory path."""
    return get_dashboard_path() / "dist"


def sync_dashboard_version() -> bool:
    """Keep dashboard-react/package.json aligned with root version.json."""
    root = get_project_root()
    version_file = root / "version.json"
    package_file = get_dashboard_path() / "package.json"

    try:
        version_data = json.loads(version_file.read_text(encoding="utf-8"))
        package_data = json.loads(package_file.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"[DASHBOARD] ERROR: Failed to read version metadata: {exc}")
        return False

    target_version = str(version_data.get("version", "")).strip()
    if not target_version:
        print("[DASHBOARD] ERROR: version.json does not contain a valid version")
        return False

    if str(package_data.get("version", "")).strip() == target_version:
        return True

    package_data["version"] = target_version
    try:
        package_file.write_text(json.dumps(package_data, indent=2) + "\n", encoding="utf-8")
    except Exception as exc:
        print(f"[DASHBOARD] ERROR: Failed to update package.json version: {exc}")
        return False

    print(f"[DASHBOARD] Synced dashboard package version to {target_version}")
    return True


def is_dashboard_built() -> bool:
    """Check if dashboard is already built."""
    dist_path = get_dist_path()
    index_html = dist_path / "index.html"
    
    if not index_html.exists():
        return False
    
    # Check if dist is newer than src (basic staleness check)
    src_path = get_dashboard_path() / "src"
    if src_path.exists():
        dist_mtime = index_html.stat().st_mtime
        
        # Check if any src file is newer than dist
        for src_file in src_path.rglob("*.tsx"):
            if src_file.stat().st_mtime > dist_mtime:
                print(f"[DASHBOARD] Source file {src_file.name} is newer than build")
                return False
        
        for src_file in src_path.rglob("*.ts"):
            if src_file.stat().st_mtime > dist_mtime:
                print(f"[DASHBOARD] Source file {src_file.name} is newer than build")
                return False
    
    return True


def has_node_modules() -> bool:
    """Check if node_modules exists."""
    return (get_dashboard_path() / "node_modules").exists()


def install_dependencies() -> bool:
    """Install npm dependencies."""
    dashboard_path = get_dashboard_path()
    
    print("[DASHBOARD] Installing npm dependencies...")
    try:
        result = subprocess.run(
            ["npm", "install"],
            cwd=dashboard_path,
            capture_output=True,
            text=True,
            check=True
        )
        print("[DASHBOARD] Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[DASHBOARD] ERROR: Failed to install dependencies: {e}")
        print(f"[DASHBOARD] {e.stderr}")
        return False
    except FileNotFoundError:
        print("[DASHBOARD] ERROR: npm not found. Please install Node.js.")
        return False


def build_dashboard() -> bool:
    """Build the dashboard for production."""
    dashboard_path = get_dashboard_path()
    
    # First check if node_modules exists
    if not has_node_modules():
        if not install_dependencies():
            return False
    
    print("[DASHBOARD] Building for production...")
    print("[DASHBOARD] This may take 1-2 minutes...")
    
    try:
        result = subprocess.run(
            ["npm", "run", "build"],
            cwd=dashboard_path,
            capture_output=True,
            text=True,
            check=True
        )
        
        if result.returncode == 0:
            print("[DASHBOARD] [OK] Build completed successfully")
            return True
        else:
            print(f"[DASHBOARD] ERROR: Build failed")
            print(f"[DASHBOARD] {result.stderr}")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"[DASHBOARD] ERROR: Build failed: {e}")
        print(f"[DASHBOARD] {e.stderr}")
        return False
    except FileNotFoundError:
        print("[DASHBOARD] ERROR: npm not found. Please install Node.js.")
        return False


def start_dev_server() -> subprocess.Popen:
    """Start Vite development server for hot-reload."""
    dashboard_path = get_dashboard_path()
    
    # Check if node_modules exists
    if not has_node_modules():
        if not install_dependencies():
            return None
    
    print("[DASHBOARD] Starting Vite development server...")
    print("[DASHBOARD] Hot-reload enabled at http://localhost:5173")
    
    try:
        # Start dev server in background
        process = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=dashboard_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
        )
        
        # Wait a moment for server to start
        time.sleep(3)
        
        # Check if process is still running
        if process.poll() is None:
            print("[DASHBOARD] [OK] Dev server started")
            return process
        else:
            stdout, stderr = process.communicate()
            print(f"[DASHBOARD] ERROR: Dev server failed to start")
            print(f"[DASHBOARD] {stderr}")
            return None
            
    except FileNotFoundError:
        print("[DASHBOARD] ERROR: npm not found. Please install Node.js.")
        return None


def check_and_build(force: bool = False, auto_build: bool = True) -> bool:
    """
    Check if dashboard is built and optionally build it.
    
    Args:
        force: Force rebuild even if already built
        auto_build: Automatically build if not present
    
    Returns:
        True if dashboard is ready (built or building)
    """
    if not sync_dashboard_version():
        return False

    if force:
        print("[DASHBOARD] Force rebuild requested...")
        return build_dashboard()
    
    if is_dashboard_built():
        print("[DASHBOARD] [OK] Dashboard is built and up-to-date")
        return True
    
    if not auto_build:
        print("[DASHBOARD] [WARN] Dashboard not built. Run with --build to build it.")
        return False
    
    print("[DASHBOARD] Dashboard needs to be built...")
    return build_dashboard()


def main():
    parser = argparse.ArgumentParser(
        description="Dashboard Build Manager for Busy Whatsapp Bridge"
    )
    
    parser.add_argument(
        "--check", "-c",
        action="store_true",
        help="Just check if dashboard is built (exit code 1 if not)"
    )
    
    parser.add_argument(
        "--build", "-b",
        action="store_true",
        help="Build production dashboard if needed"
    )
    
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Force rebuild even if already built"
    )
    
    parser.add_argument(
        "--dev", "-d",
        action="store_true",
        help="Start Vite dev server for development"
    )
    
    parser.add_argument(
        "--install", "-i",
        action="store_true",
        help="Only install dependencies, don't build"
    )
    
    args = parser.parse_args()
    
    # Check if dashboard directory exists
    dashboard_path = get_dashboard_path()
    if not dashboard_path.exists():
        print(f"[DASHBOARD] ERROR: Dashboard directory not found: {dashboard_path}")
        sys.exit(2)

    if not sync_dashboard_version():
        sys.exit(2)
    
    # Handle different modes
    if args.install:
        success = install_dependencies()
        sys.exit(0 if success else 2)
    
    if args.dev:
        # Start dev server and exit (process keeps running)
        process = start_dev_server()
        if process:
            print("[DASHBOARD] Dev server PID:", process.pid)
            # Don't exit - let the dev server run
            try:
                process.wait()
            except KeyboardInterrupt:
                print("\n[DASHBOARD] Stopping dev server...")
                process.terminate()
                sys.exit(0)
        else:
            sys.exit(2)
    
    if args.force or args.build:
        # Build mode
        success = check_and_build(force=args.force, auto_build=True)
        sys.exit(0 if success else 2)
    
    # Default: just check
    if is_dashboard_built():
        print("[DASHBOARD] [OK] Dashboard is built")
        sys.exit(0)
    else:
        print("[DASHBOARD] [WARN] Dashboard is not built")
        print("[DASHBOARD] Run: python check-dashboard-build.py --build")
        sys.exit(1)


if __name__ == "__main__":
    main()
