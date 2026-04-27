import time
import threading
import blocker

# ban durations in seconds — escalates with repeat offences
BAN_DURATIONS = [60, 300, 900, 3600]  # 1min, 5min, 15min, 1hour
offence_count = {}

def get_ban_duration(source_ip):
    count = offence_count.get(source_ip, 0)
    index = min(count, len(BAN_DURATIONS) - 1)
    return BAN_DURATIONS[index]

def schedule_unban(source_ip):
    duration = get_ban_duration(source_ip)
    offence_count[source_ip] = offence_count.get(source_ip, 0) + 1

    def unban():
        time.sleep(duration)
        blocker.unblock(source_ip)
        print(f"Unbanned {source_ip} after {duration}s")

    thread = threading.Thread(target=unban, daemon=True)
    thread.start()
