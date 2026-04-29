import time
import statistics
from collections import deque, defaultdict

# ── Configuration ──────────────────────────────────────────────────────────────
# How many seconds of timestamps to keep per IP and globally.
# Acts as the "short-term memory" — what is happening right now?
WINDOW_SECONDS = 60

# How many seconds of per-second counts to keep for baseline calculation.
# 1800 = 30 minutes. This is the "long-term memory" — what is normal?
BASELINE_WINDOW = 1800

# How often (in seconds) to recalculate mean and stddev from the baseline window.
# Recalculating every second would waste CPU — every 60s is a good balance.
RECALC_INTERVAL = 60

# Minimum number of data points in the current hour's slot before we
# trust it over the 30-minute rolling window. Prevents cold-start false positives.
MIN_DATA_POINTS = 60

# Detection thresholds
Z_SCORE_THRESHOLD = 3.0   # Flag if current rate is 3 standard deviations above mean
RATE_MULTIPLIER   = 5.0   # Flag if current rate is 5x the baseline mean
# ──────────────────────────────────────────────────────────────────────────────


# ── Sliding Windows ────────────────────────────────────────────────────────────
# Each deque stores raw timestamps of recent requests.
# maxlen=60 means the oldest timestamp auto-evicts when a new one is added —
# this is the "sliding" mechanism. No manual cleanup needed.

# Per-IP: one deque per IP address, tracking that IP's last 60 seconds of requests
ip_windows = defaultdict(lambda: deque(maxlen=WINDOW_SECONDS))

# Global: one deque tracking ALL requests across ALL IPs for the last 60 seconds
# Used to detect distributed attacks where no single IP looks suspicious
global_window = deque(maxlen=WINDOW_SECONDS)

# Per-IP error tracking: only stores timestamps of 4xx/5xx responses
# Used for error surge detection
ip_error_windows = defaultdict(lambda: deque(maxlen=WINDOW_SECONDS))
# ──────────────────────────────────────────────────────────────────────────────


# ── Rolling Baseline Windows ───────────────────────────────────────────────────
# These store per-second request *counts* (not raw timestamps) over 30 minutes.
# Every second, we append how many requests arrived that second.
# This gives us the data needed to calculate mean and stddev.

baseline_window      = deque(maxlen=BASELINE_WINDOW)  # Global counts
ip_baseline_windows  = defaultdict(lambda: deque(maxlen=BASELINE_WINDOW))
error_baseline_windows = defaultdict(lambda: deque(maxlen=BASELINE_WINDOW))
# ──────────────────────────────────────────────────────────────────────────────


# ── Per-Hour Slots ─────────────────────────────────────────────────────────────
# Traffic patterns differ by time of day (3am vs 2pm look very different).
# We store counts per hour so the baseline can prefer current-hour data
# when enough exists — making detection time-aware.
hourly_slots    = defaultdict(list)
ip_hourly_slots = defaultdict(lambda: defaultdict(list))
# ──────────────────────────────────────────────────────────────────────────────


# ── Cached Baseline Values ─────────────────────────────────────────────────────
# Recalculating statistics on every request would be expensive.
# Instead we cache mean/std and only recalculate every RECALC_INTERVAL seconds.
# Floor values (mean=1.0, std=0.5) prevent division-by-zero and avoid
# hair-trigger sensitivity on servers with very low traffic.
_cached_baseline    = {"mean": 1.0, "std": 1.0, "last_calc": 0}
_ip_cached_baseline = defaultdict(lambda: {"mean": 1.0, "std": 1.0, "last_calc": 0})
_error_cached_baseline = defaultdict(lambda: {"mean": 0.1, "std": 0.1, "last_calc": 0})
# ──────────────────────────────────────────────────────────────────────────────


def record_request(source_ip, status_code):
    """
    Called on every incoming request.
    Updates all sliding windows and baseline data structures.
    status_code is needed to track error rates separately.
    """
    now = int(time.time())

    # Add this request's timestamp to the per-IP sliding window
    ip_windows[source_ip].append(now)

    # Add to the global sliding window (all IPs combined)
    global_window.append(now)

    # If this was an error response, track it separately for error surge detection
    if status_code >= 400:
        ip_error_windows[source_ip].append(now)

    current_hour = time.localtime(now).tm_hour

    # Count how many requests arrived in this exact second (the per-second bucket)
    ip_count     = sum(1 for t in ip_windows[source_ip] if t == now)
    global_count = sum(1 for t in global_window if t == now)
    error_count  = sum(1 for t in ip_error_windows[source_ip] if t == now)

    # Append current-second counts to the 30-minute rolling baseline windows
    baseline_window.append(global_count)
    ip_baseline_windows[source_ip].append(ip_count)
    error_baseline_windows[source_ip].append(error_count)

    # Also store in per-hour slots for time-aware baseline selection
    hourly_slots[current_hour].append(global_count)
    ip_hourly_slots[source_ip][current_hour].append(ip_count)


def _get_baseline(cached, rolling_window, hourly_data):
    """
    Core baseline calculation function.
    Returns (mean, std) — the two numbers that define "normal" traffic.

    Selection logic:
    1. If recalculated recently, return cached values (performance optimisation)
    2. If current hour has enough data (>=60 points), use it — most accurate
    3. Otherwise fall back to the full 30-minute rolling window
    4. Apply floor values to prevent division-by-zero and over-sensitivity
    """
    now = time.time()

    # Return cached values if we recalculated recently — avoids expensive
    # statistics operations on every single request
    if now - cached["last_calc"] < RECALC_INTERVAL:
        return cached["mean"], cached["std"]

    current_hour = time.localtime(now).tm_hour
    hour_data    = hourly_data.get(current_hour, [])

    # Prefer current hour's data when it has enough points.
    # This makes the baseline time-aware — 3am traffic is judged
    # against 3am norms, not against the average of all hours.
    if len(hour_data) >= MIN_DATA_POINTS:
        data = hour_data
    elif len(rolling_window) >= 2:
        data = list(rolling_window)
    else:
        # Not enough data yet — return cached (or default) values
        return cached["mean"], cached["std"]

    # Calculate mean and stddev from selected data window.
    # Floor values ensure we never divide by zero and never become
    # so sensitive that normal traffic fluctuations trigger alerts.
    mean = max(statistics.mean(data), 1.0)
    std  = max(statistics.stdev(data) if len(data) >= 2 else 1.0, 0.5)

    # Cache the results and record when we last calculated
    cached["mean"]      = mean
    cached["std"]       = std
    cached["last_calc"] = now

     # Record history for dashboard graph
    if cached is _cached_baseline:  # Only track global baseline
        record_baseline_history(mean)

    return mean, std


def is_anomalous_ip(source_ip):
    """
    Checks whether a specific IP's current request rate is anomalous.

    Two triggers — whichever fires first:
    1. Z-score > 3.0: the rate is more than 3 standard deviations above normal
    2. Rate > 5x baseline mean: even if std is low, a 5x spike is always suspicious

    Returns (bool, condition_string) so the caller knows WHY it was flagged.
    """
    # Need at least 10 data points before making any judgement —
    # too few points makes statistics meaningless
    if len(ip_windows[source_ip]) < 10:
        return False, None

    mean, std    = get_ip_baseline(source_ip)
    current_rate = get_current_rate(ip_windows[source_ip])

    # Z-score = how many standard deviations above the mean is the current rate?
    # A z-score of 3.0 means "this would naturally occur less than 0.3% of the time"
    z_score         = (current_rate - mean) / std if std > 0 else 0
    rate_multiplier = current_rate / mean if mean > 0 else 0

    if z_score > Z_SCORE_THRESHOLD:
        return True, f"z_score={z_score:.2f}"

    # 5x multiplier catches cases where std is very small but a spike
    # is clearly unusual even without a high z-score
    if rate_multiplier > RATE_MULTIPLIER:
        return True, f"rate={rate_multiplier:.2f}x_baseline"

    return False, None


def is_anomalous_global():
    """
    Same logic as is_anomalous_ip but applied to ALL traffic combined.
    Used to detect distributed attacks where many IPs each send
    a small number of requests — no single IP looks suspicious,
    but the global rate is way above normal.

    Global anomalies trigger Slack alerts only — no IP block,
    since there is no single IP to blame.
    """
    if len(global_window) < 10:
        return False, None

    mean, std    = get_global_baseline()
    current_rate = get_current_rate(global_window)

    z_score         = (current_rate - mean) / std if std > 0 else 0
    rate_multiplier = current_rate / mean if mean > 0 else 0

    if z_score > Z_SCORE_THRESHOLD:
        return True, f"z_score={z_score:.2f}"
    if rate_multiplier > RATE_MULTIPLIER:
        return True, f"rate={rate_multiplier:.2f}x_baseline"

    return False, None


def is_error_surge(source_ip):
    """
    Detects whether an IP is generating an unusual number of errors.
    An error surge (4xx/5xx rate > 3x baseline) suggests the IP may
    be probing for vulnerabilities or hammering broken endpoints.
    When detected, detection thresholds are automatically tightened.
    """
    if len(ip_error_windows[source_ip]) < 5:
        return False

    mean, std          = get_error_baseline(source_ip)
    current_error_rate = get_current_rate(ip_error_windows[source_ip])

    # Flag if error rate exceeds 3x the baseline error rate
    return current_error_rate > (mean * 3)


def get_current_rate(window):
    """
    Counts how many requests in the given window occurred in the last 1 second.
    This gives us a "requests per second" figure for the current moment.
    """
    now = int(time.time())
    return sum(1 for t in window if now - t <= 1)


def get_global_baseline():
    return _get_baseline(_cached_baseline, baseline_window, hourly_slots)


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


# Baseline history — stores (timestamp, mean) tuples for graphing
baseline_history = []

def record_baseline_history(mean):
    """Called every time baseline is recalculated. Stores up to 120 data points."""
    now = time.strftime("%H:%M:%S", time.localtime())
    baseline_history.append({"time": now, "mean": round(mean, 2)})
    if len(baseline_history) > 120:
        baseline_history.pop(0)

