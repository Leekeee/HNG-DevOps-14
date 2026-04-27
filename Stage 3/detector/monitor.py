import json
import time

LOG_PATH = "/var/log/nginx/hng-access.log"

def tail_log(callback):
    with open(LOG_PATH, "r") as f:
        f.seek(0, 2)  # jump to end of file
        while True:
            line = f.readline()
            if not line:
                time.sleep(0.2)
                continue
            try:
                entry = json.loads(line.strip())
                parsed = {
                    "source_ip":  entry.get("source_ip"),
                    "timestamp":  entry.get("timestamp"),
                    "path":       entry.get("path"),
                    "status":     entry.get("status"),
                }
                callback(parsed)
            except json.JSONDecodeError:
                continue  # skip malformed lines
