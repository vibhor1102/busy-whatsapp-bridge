import os
from pathlib import Path

# Check if config directory and file exist
appdata = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local'))
config_dir = appdata / "BusyWhatsappBridge"
config_file = config_dir / "conf.json"

print(f"AppData Path: {appdata}")
print(f"Config Dir: {config_dir}")
print(f"Config File: {config_file}")
print(f"Config Dir Exists: {config_dir.exists()}")
print(f"Config File Exists: {config_file.exists()}")

if config_dir.exists():
    print(f"\nFiles in config dir:")
    for f in config_dir.iterdir():
        print(f"  - {f.name}")
else:
    print("\nConfig directory does NOT exist yet")
    print("It will be created when the application first runs")
