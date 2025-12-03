import time
import json
import threading

_lock = threading.Lock()
LOG_FILE = "console_log.txt"

def console_log(message, data=None, to_file=True):
    """Simple console logger used for debugging stuck players.

    Prints a timestamped message and optionally appends a JSON line to `console_log.txt`.
    `data` should be JSON-serializable (convert numpy arrays to lists before passing).
    """
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    if data is None:
        print(f"[CONSOLE_LOG {ts}] {message}")
    else:
        try:
            j = json.dumps(data)
        except Exception:
            # Fallback to string representation
            j = str(data)
        print(f"[CONSOLE_LOG {ts}] {message} | {j}")

    if to_file:
        entry = {"ts": ts, "message": message, "data": data}
        try:
            with _lock:
                with open(LOG_FILE, "a", encoding="utf-8") as f:
                    f.write(json.dumps(entry, default=str) + "\n")
        except Exception:
            # Avoid crashing game due to logging failure
            pass
