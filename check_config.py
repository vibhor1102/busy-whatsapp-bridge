#!/usr/bin/env python3
"""Check configuration and AppData setup."""
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from app.config import get_local_appdata_path, get_roaming_appdata_path, get_config_path

# Get paths using centralized functions
local_appdata = get_local_appdata_path()
roaming_appdata = get_roaming_appdata_path()
config_file = get_config_path()

print("Busy Whatsapp Bridge Configuration Check")
print("=" * 50)
print()

print("ROAMING CONFIG (User-specific, follows user):")
print(f"  Directory: {roaming_appdata}")
print(f"  Config File: {config_file}")
print(f"  Exists: {roaming_appdata.exists()}")
print(f"  Config Exists: {config_file.exists()}")
print()

print("LOCAL DATA (Machine-specific, not roamed):")
print(f"  Directory: {local_appdata}")
print(f"  Exists: {local_appdata.exists()}")
print()

if roaming_appdata.exists():
    print("Files in roaming config dir:")
    for f in roaming_appdata.iterdir():
        if f.is_dir():
            print(f"  - {f.name}/")
        else:
            print(f"  - {f.name}")
    print()

if local_appdata.exists():
    print("Files in local data dir:")
    for f in local_appdata.iterdir():
        if f.is_dir():
            print(f"  - {f.name}/")
            # List contents of subdirectories
            if f.name in ['data', 'auth']:
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
