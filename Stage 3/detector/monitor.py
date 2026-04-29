import os
import time
import json
from pathlib import Path

LOG_PATH = "/var/log/nginx/hng-access.log"

def follow(log_path: str):
    """
    Generator that yields parsed log lines forever.
    Handles log rotation by watching the file's inode.
    """
    path = Path(log_path)

    # Wait until the file exists — Nginx may not have written
    # anything yet when the daemon first starts
    while not path.exists():
        print(f"[monitor] Waiting for log file at {log_path}...")
        time.sleep(2)

    file_handle = open(path, "r")
    # Seek to end on startup — only care about new lines,
    # not replaying history from before we launched
    file_handle.seek(0, 2)
    current_inode = os.stat(log_path).st_ino

    print(f"[monitor] Tailing {log_path} (inode {current_inode})")

    while True:
        line = file_handle.readline()

        if line:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                print(f"[monitor] Skipped malformed line: {line[:80]}")
            continue

        # No new line — check for log rotation before sleeping
        try:
            new_inode = os.stat(log_path).st_ino
        except FileNotFoundError:
            # File briefly missing during rotation — wait and retry
            time.sleep(0.5)
            continue

        if new_inode != current_inode:
            print(f"[monitor] Log rotation detected. Reopening file.")
            file_handle.close()
            file_handle = open(path, "r")
            current_inode = new_inode
        else:
            # No new data — sleep briefly to avoid burning CPU
            time.sleep(0.1)


def tail_log(callback):
    """
    Wrapper around follow() that maintains backward compatibility
    with the callback pattern used in main.py.
    """
    for entry in follow(LOG_PATH):
        callback(entry)
