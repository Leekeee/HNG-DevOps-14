import monitor
import detector
import blocker
import notifier

def on_anomaly(parsed):
    source_ip = parsed.get("source_ip")
    blocker.block(source_ip)
    notifier.send_alert(source_ip, parsed)

def handle_entry(parsed):
    detector.process(parsed, on_anomaly)

if __name__ == "__main__":
    print("Starting anomaly detection daemon...")
    monitor.tail_log(handle_entry)
