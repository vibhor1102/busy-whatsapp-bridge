#!/usr/bin/env python3
"""Check configuration and AppData setup."""
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from app.config import get_appdata_path, get_config_path

# Get paths using centralized functions
appdata = get_appdata_path()
config_file = get_config_path()

print(f"AppData Path: {appdata.parent}")
print(f"Config Dir: {appdata}")
print(f"Config File: {config_file}")
print(f"Config Dir Exists: {appdata.exists()}")
print(f"Config File Exists: {config_file.exists()}")

if appdata.exists():
    print(f"\nFiles in config dir:")
    for f in appdata.iterdir():
        if f.is_dir():
            print(f"  - {f.name}/")
        else:
            print(f"  - {f.name}")
    
    # Check data directory
    data_dir = appdata / "data"
    if data_dir.exists():
        print(f"\nFiles in data/:")
        for f in data_dir.iterdir():
            print(f"  - {f.name}")
    
    # Check logs directory
    logs_dir = appdata / "logs"
    if logs_dir.exists():
        print(f"\nFiles in logs/:")
        for f in logs_dir.iterdir():
            print(f"  - {f.name}")
else:
    print("\nConfig directory does NOT exist yet")
    print("It will be created when the application first runs")
