import json
import os
from pathlib import Path

def _find_version_file():
    """Find version.json in the project root."""
    # Start from current file and go up
    current = Path(__file__).resolve()
    # Check parent (app/), grandparent (root/)
    # Or just look for version.json in the current working directory or relative to this script
    
    # Strategy 1: Relative to this file (app/version.py -> ../version.json)
    root_path = current.parent.parent
    ver_file = root_path / "version.json"
    if ver_file.exists():
        return ver_file
        
    # Strategy 2: Check CWD
    ver_file = Path("version.json")
    if ver_file.exists():
        return ver_file
        
    return None

def _load_version_data():
    """Load version data from JSON."""
    ver_file = _find_version_file()
    if ver_file:
        try:
            with open(ver_file, 'r') as f:
                return json.load(f)
        except:
            pass
    return {"version": "0.0.0-fallback"} # Fallback

_data = _load_version_data()

__version__ = _data.get("version", "0.0.0-fallback")

def parse_version(version_str):
    """Parse version string to tuple."""
    try:
        parts = version_str.split('.')
        return tuple(int(p) for p in parts)
    except:
        return (0, 0, 0)

__version_info__ = parse_version(__version__)

# Compatibility aliases
VERSION = __version__
VERSION_INFO = __version_info__


def get_version():
    """Get version string."""
    return __version__


def get_version_info():
    """Get version tuple (major, minor, patch)."""
    return __version_info__


def compare_versions(v1, v2):
    """
    Compare two version strings.
    Returns: -1 if v1 < v2, 0 if equal, 1 if v1 > v2
    """
    v1_tuple = parse_version(v1) if isinstance(v1, str) else v1
    v2_tuple = parse_version(v2) if isinstance(v2, str) else v2
    
    # Pad with zeros to match lengths
    max_len = max(len(v1_tuple), len(v2_tuple))
    v1_padded = v1_tuple + (0,) * (max_len - len(v1_tuple))
    v2_padded = v2_tuple + (0,) * (max_len - len(v2_tuple))
    
    if v1_padded < v2_padded:
        return -1
    elif v1_padded > v2_padded:
        return 1
    else:
        return 0
