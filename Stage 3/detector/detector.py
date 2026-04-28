import baseline
import audit

def process(parsed, on_ip_anomaly, on_global_anomaly):
    source_ip = parsed.get("source_ip")
    status_code = parsed.get("status", 200)
    
    if not source_ip:
        return
    
    # Record request with status code
    baseline.record_request(source_ip, status_code)
    
    # Check per-IP anomaly
    anomalous, condition = baseline.is_anomalous_ip(source_ip)
    if anomalous:
        mean, std = baseline.get_ip_baseline(source_ip)
        current_rate = baseline.get_current_rate(baseline.ip_windows[source_ip])
        on_ip_anomaly(parsed, condition, current_rate, mean)
        return
    
    # Check error surge — tighten thresholds automatically
    if baseline.is_error_surge(source_ip):
        anomalous, condition = baseline.is_anomalous_ip(source_ip)
        if anomalous:
            mean, std = baseline.get_ip_baseline(source_ip)
            current_rate = baseline.get_current_rate(baseline.ip_windows[source_ip])
            on_ip_anomaly(parsed, f"error_surge+{condition}", current_rate, mean)
            return
    
    # Check global anomaly
    global_anomalous, global_condition = baseline.is_anomalous_global()
    if global_anomalous:
        mean, std = baseline.get_global_baseline()
        current_rate = baseline.get_current_rate(baseline.global_window)
        on_global_anomaly(global_condition, current_rate, mean)
