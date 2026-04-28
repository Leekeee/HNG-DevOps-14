import time
import statistics
from collections import deque, defaultdict

# Configuration
WINDOW_SECONDS = 60          # sliding window size
BASELINE_WINDOW = 1800       # 30-minute rolling baseline
RECALC_INTERVAL = 60         # recalculate baseline every 60 seconds
MIN_DATA_POINTS = 60         # minimum points for current hour preference
Z_SCORE_THRESHOLD = 3.0
RATE_MULTIPLIER = 5.0        # 5x baseline mean threshold

# Per-IP sliding windows (60 seconds)
ip_windows = defaultdict(lambda: deque(maxlen=WINDOW_SECONDS))

# Global sliding window (60 seconds)
global_window = deque(maxlen=WINDOW_SECONDS)

# Per-IP error tracking
ip_error_windows = defaultdict(lambda: deque(maxlen=WINDOW_SECONDS))

# Rolling baseline - 30 minutes of per-second counts
baseline_window = deque(maxlen=BASELINE_WINDOW)
ip_baseline_windows = defaultdict(lambda: deque(maxlen=BASELINE_WINDOW))
error_baseline_windows = defaultdict(lambda: deque(maxlen=BASELINE_WINDOW))

# Per-hour slots
hourly_slots = defaultdict(list)
ip_hourly_slots = defaultdict(lambda: defaultdict(list))

# Cached baseline values
_cached_baseline = {"mean": 1.0, "std": 1.0, "last_calc": 0}
_ip_cached_baseline = defaultdict(lambda: {"mean": 1.0, "std": 1.0, "last_calc": 0})
_error_cached_baseline = defaultdict(lambda: {"mean": 0.1, "std": 0.1, "last_calc": 0})


def record_request(source_ip, status_code):
    now = int(time.time())
    
    # Update per-IP window
    ip_windows[source_ip].append(now)
    
    # Update global window
    global_window.append(now)
    
    # Track errors (4xx/5xx)
    if status_code >= 400:
        ip_error_windows[source_ip].append(now)
    
    # Update baseline windows with current per-second counts
    current_hour = time.localtime(now).tm_hour
    
    # Count requests in last second
    ip_count = sum(1 for t in ip_windows[source_ip] if t == now)
    global_count = sum(1 for t in global_window if t == now)
    error_count = sum(1 for t in ip_error_windows[source_ip] if t == now)
    
    baseline_window.append(global_count)
    ip_baseline_windows[source_ip].append(ip_count)
    error_baseline_windows[source_ip].append(error_count)
    
    # Update hourly slots
    hourly_slots[current_hour].append(global_count)
    ip_hourly_slots[source_ip][current_hour].append(ip_count)


def _get_baseline(cached, rolling_window, hourly_data):
    now = time.time()
    
    # Recalculate every 60 seconds
    if now - cached["last_calc"] < RECALC_INTERVAL:
        return cached["mean"], cached["std"]
    
    current_hour = time.localtime(now).tm_hour
    hour_data = hourly_data.get(current_hour, [])
    
    # Prefer current hour if enough data
    if len(hour_data) >= MIN_DATA_POINTS:
        data = hour_data
    elif len(rolling_window) >= 2:
        data = list(rolling_window)
    else:
        return cached["mean"], cached["std"]
    
    mean = max(statistics.mean(data), 1.0)  # floor of 1.0
    std = max(statistics.stdev(data) if len(data) >= 2 else 1.0, 0.5)  # floor of 0.5
    
    cached["mean"] = mean
    cached["std"] = std
    cached["last_calc"] = now
    
    return mean, std


def get_global_baseline():
    return _get_baseline(
        _cached_baseline,
        baseline_window,
        hourly_slots
    )


def get_ip_baseline(source_ip):
    return _get_baseline(
        _ip_cached_baseline[source_ip],
        ip_baseline_windows[source_ip],
        ip_hourly_slots[source_ip]
    )


def get_error_baseline(source_ip):
    return _get_baseline(
        _error_cached_baseline[source_ip],
        error_baseline_windows[source_ip],
        defaultdict(list)
    )


def get_current_rate(window):
    now = int(time.time())
    return sum(1 for t in window if now - t <= 1)


def is_anomalous_ip(source_ip):
    if len(ip_windows[source_ip]) < 10:
        return False, None
    
    mean, std = get_ip_baseline(source_ip)
    current_rate = get_current_rate(ip_windows[source_ip])
    
    z_score = (current_rate - mean) / std if std > 0 else 0
    rate_multiplier = current_rate / mean if mean > 0 else 0
    
    if z_score > Z_SCORE_THRESHOLD:
        return True, f"z_score={z_score:.2f}"
    if rate_multiplier > RATE_MULTIPLIER:
        return True, f"rate={rate_multiplier:.2f}x_baseline"
    
    return False, None


def is_anomalous_global():
    if len(global_window) < 10:
        return False, None
    
    mean, std = get_global_baseline()
    current_rate = get_current_rate(global_window)
    
    z_score = (current_rate - mean) / std if std > 0 else 0
    rate_multiplier = current_rate / mean if mean > 0 else 0
    
    if z_score > Z_SCORE_THRESHOLD:
        return True, f"z_score={z_score:.2f}"
    if rate_multiplier > RATE_MULTIPLIER:
        return True, f"rate={rate_multiplier:.2f}x_baseline"
    
    return False, None


def is_error_surge(source_ip):
    if len(ip_error_windows[source_ip]) < 5:
        return False
    
    mean, std = get_error_baseline(source_ip)
    current_error_rate = get_current_rate(ip_error_windows[source_ip])
    
    return current_error_rate > (mean * 3)
