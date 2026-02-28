#!/usr/bin/env python3
"""Check configuration and AppData setup."""
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from app.config import get_roaming_appdata_path, get_config_path

# Get paths using centralized functions
appdata = get_roaming_appdata_path()
config_file = get_config_path()

print("Busy Whatsapp Bridge Configuration Check")
print("=" * 50)
print()

print("APPDATA (User configuration and data):")
print(f"  Directory: {appdata}")
print(f"  Config File: {config_file}")
print(f"  Exists: {appdata.exists()}")
print(f"  Config Exists: {config_file.exists()}")
print()

if appdata.exists():
    print("Files in AppData dir:")
    for f in appdata.iterdir():
        if f.is_dir():
            print(f"  - {f.name}/")
            # List contents of subdirectories
            if f.name in ['data', 'auth', 'logs']:
                for subf in f.iterdir():
                    print(f"      - {subf.name}")
        else:
            print(f"  - {f.name}")
    print()

# Check install dir logs
install_dir = Path(__file__).parent
logs_dir = install_dir / "logs"
if logs_dir.exists():
    print("Files in install logs dir:")
    for f in logs_dir.iterdir():
        print(f"  - {f.name}")
    print()

print("=" * 50)
print("Check complete!")
