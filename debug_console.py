import time
import json
import threading

_lock = threading.Lock()
LOG_FILE = "console_log.txt"

def console_log(message, data=None, to_file=True):
    """No-op logger: disabled in production to avoid console/file spam.

    This intentionally does nothing. Keeping the function preserves
    callsites across the codebase but prevents terminal output and
    file writes. If you need to re-enable logging for debugging,
    reintroduce printing/writing here.
    """
    return None
