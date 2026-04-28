import threading
import time
import uvicorn
import monitor
import detector
import blocker
import unbanner
import baseline
import audit

def on_ip_anomaly(parsed, condition, current_rate, baseline_mean):
    source_ip = parsed.get("source_ip")
    
    # Don't re-ban already blocked IPs
    if source_ip in blocker.BLOCKED_IPS:
        return
    
    blocker.block(source_ip, condition, current_rate, baseline_mean)
    unbanner.schedule_unban(source_ip, condition, current_rate, baseline_mean)

def on_global_anomaly(condition, current_rate, baseline_mean):
    # Global anomaly — Slack alert only, no block
    from notifier import send_global_alert
    send_global_alert(condition, current_rate, baseline_mean)
    audit.log(
        "GLOBAL_ANOMALY",
        condition=condition,
        rate=current_rate,
        baseline=baseline_mean
    )

def baseline_recalc_logger():
    # Log baseline recalculation every 60 seconds
    while True:
        time.sleep(60)
        mean, std = baseline.get_global_baseline()
        audit.log(
            "BASELINE_RECALC",
            condition="global",
            rate=0,
            baseline=mean
        )

def handle_entry(parsed):
    detector.process(parsed, on_ip_anomaly, on_global_anomaly)

if __name__ == "__main__":
    print("Starting anomaly detection daemon...")
    
    # Start baseline recalculation logger
    recalc_thread = threading.Thread(
        target=baseline_recalc_logger,
        daemon=True
    )
    recalc_thread.start()
    
    # Start dashboard in background thread
    dashboard_thread = threading.Thread(
        target=uvicorn.run,
        args=("dashboard:app",),
        kwargs={"host": "0.0.0.0", "port": 8000},
        daemon=True
    )
    dashboard_thread.start()
    
    # Start tailing logs — this blocks forever
    monitor.tail_log(handle_entry)
