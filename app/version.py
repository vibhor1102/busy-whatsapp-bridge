"""
Version Management

Single source of truth for application version.
Used by setup.py, Inno Setup, and throughout the application.
"""

__version__ = "1.0.0"
__version_info__ = (1, 0, 0)

# Compatibility aliases
VERSION = __version__
VERSION_INFO = __version_info__


def get_version():
    """Get version string."""
    return __version__


def get_version_info():
    """Get version tuple (major, minor, patch)."""
    return __version_info__


def parse_version(version_str):
    """Parse version string to tuple."""
    parts = version_str.split('.')
    return tuple(int(p) for p in parts)


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
