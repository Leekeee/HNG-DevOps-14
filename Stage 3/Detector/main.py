import uvicorn
import threading
import monitor
import detector
import blocker
import unbanner
import notifier

def on_anomaly(parsed):
    source_ip = parsed.get("source_ip")
    blocker.block(source_ip)
    unbanner.schedule_unban(source_ip)
    notifier.send_alert(source_ip, parsed)

def handle_entry(parsed):
    detector.process(parsed, on_anomaly)

if __name__ == "__main__":
    # run dashboard in background thread
    thread = threading.Thread(
        target=uvicorn.run,
        args=("dashboard:app",),
        kwargs={"host": "0.0.0.0", "port": 8000},
        daemon=True
    )
    thread.start()
    
    print("Starting anomaly detection daemon...")
    monitor.tail_log(handle_entry)
