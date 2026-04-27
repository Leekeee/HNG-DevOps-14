import time
import statistics
from collections import deque

WINDOW_SIZE = 300      # 5 minute sliding window
Z_SCORE_THRESHOLD = 3  # flag if 3 standard deviations above mean

# per-IP sliding windows
ip_windows = {}

def record_request(source_ip):
    now = int(time.time())
    if source_ip not in ip_windows:
        ip_windows[source_ip] = deque(maxlen=WINDOW_SIZE)
    ip_windows[source_ip].append(now)

def is_anomalous(source_ip):
    if source_ip not in ip_windows:
        return False
    
    window = ip_windows[source_ip]
    
    if len(window) < 10:  # not enough data yet
        return False
    
    now = int(time.time())
    
    # count requests per second bucket
    buckets = {}
    for ts in window:
        buckets[ts] = buckets.get(ts, 0) + 1
    
    counts = list(buckets.values())
    
    if len(counts) < 2:
        return False
    
    avg = statistics.mean(counts)
    std = statistics.stdev(counts)
    current = buckets.get(now, 0)
    
    if std == 0:
        return current > avg
    
    z_score = (current - avg) / std
    return z_score > Z_SCORE_THRESHOLD
