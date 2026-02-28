import os
from pathlib import Path

file_path = Path(r"c:\Program Files\BusyWhatsappBridge\app\main.py")
dashboard_path = file_path.parent.parent / "dashboard-react" / "dist"
assets_path = dashboard_path / "assets"

print(f"File path: {file_path}")
print(f"Dashboard path: {dashboard_path}")
print(f"Dashboard exists: {dashboard_path.exists()}")
print(f"Index exists: {(dashboard_path / 'index.html').exists()}")
print(f"Assets exists: {assets_path.exists()}")

if dashboard_path.exists():
    print(f"Contents of {dashboard_path}:")
    for item in dashboard_path.iterdir():
        print(f"  - {item.name}")
