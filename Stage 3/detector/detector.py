import baseline
import audit


def process(parsed, on_ip_anomaly, on_global_anomaly):
    """
    Central processing function — called on every incoming log entry.

    Flow:
    1. Record the request in all baseline windows (always happens first)
    2. Check if this IP's rate is anomalous → trigger IP block + alert
    3. Check if this IP has an error surge → tighten thresholds and recheck
    4. Check if the global rate is anomalous → trigger alert only (no block)

    We record BEFORE checking so our decision includes the current request.
    Checking before recording would mean we're always one step behind.
    """
    source_ip   = parsed.get("source_ip")
    status_code = parsed.get("status", 200)

    if not source_ip:
        return

    # Step 1: Record the request — updates all sliding windows and baseline data
    baseline.record_request(source_ip, status_code)

    # Step 2: Per-IP anomaly check
    # Returns (True, condition) if z-score > 3.0 or rate > 5x mean
    anomalous, condition = baseline.is_anomalous_ip(source_ip)
    if anomalous:
        mean, std    = baseline.get_ip_baseline(source_ip)
        current_rate = baseline.get_current_rate(baseline.ip_windows[source_ip])
        # Pass condition string so blocker/notifier can include WHY it was flagged
        on_ip_anomaly(parsed, condition, current_rate, mean)
        return  # No need to check global if we already flagged this IP

    # Step 3: Error surge check
    # If this IP is generating lots of errors, tighten detection and recheck.
    # This catches slower probing attacks that wouldn't trigger the rate threshold.
    if baseline.is_error_surge(source_ip):
        anomalous, condition = baseline.is_anomalous_ip(source_ip)
        if anomalous:
            mean, std    = baseline.get_ip_baseline(source_ip)
            current_rate = baseline.get_current_rate(baseline.ip_windows[source_ip])
            on_ip_anomaly(parsed, f"error_surge+{condition}", current_rate, mean)
            return

    # Step 4: Global anomaly check
    # Even if no single IP looks suspicious, the combined traffic might be too high.
    # This catches distributed attacks (botnets) where each bot sends few requests.
    # Response: Slack alert only — there is no single IP to block.
    global_anomalous, global_condition = baseline.is_anomalous_global()
    if global_anomalous:
        mean, std    = baseline.get_global_baseline()
        current_rate = baseline.get_current_rate(baseline.global_window)
        on_global_anomaly(global_condition, current_rate, mean)
