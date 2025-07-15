"""
GLib wrapper for abstraction and easier testing.
"""

import logging
from typing import Any, Callable


def timeout_add(interval: int, callback: Callable[[], Any]) -> int:
    """
    Add a timeout callback using GLib.

    Args:
        interval: Timeout interval in milliseconds
        callback: Function to call when timeout expires

    Returns:
        Timer ID or 0 if GLib not available
    """
    try:
        import sys

        # Add the paths to some system packages
        sys.path.insert(1, "/usr/lib/python3.8/site-packages")
        from gi.repository import GLib  # type: ignore

        return GLib.timeout_add(interval, callback)
    except ImportError:
        logging.error("GLib not available - timeout_add ignored")
        return 0
