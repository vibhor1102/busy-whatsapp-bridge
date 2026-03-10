#!/usr/bin/env python
"""Sync dashboard-react/package.json version with the root version.json."""

from __future__ import annotations

import json
from pathlib import Path
import sys


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    version_file = root / "version.json"
    package_file = root / "dashboard-react" / "package.json"

    if not version_file.exists():
        print("[VERSION] version.json not found")
        return 1

    if not package_file.exists():
        print("[VERSION] dashboard-react/package.json not found")
        return 1

    version_data = json.loads(version_file.read_text(encoding="utf-8"))
    package_data = json.loads(package_file.read_text(encoding="utf-8"))

    target_version = version_data.get("version", "").strip()
    if not target_version:
        print("[VERSION] version.json is missing a valid version")
        return 1

    current_version = str(package_data.get("version", "")).strip()
    if current_version == target_version:
        print(f"[VERSION] dashboard-react/package.json already at {target_version}")
        return 0

    package_data["version"] = target_version
    package_file.write_text(
        json.dumps(package_data, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"[VERSION] synced dashboard-react/package.json: {current_version or '<empty>'} -> {target_version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
