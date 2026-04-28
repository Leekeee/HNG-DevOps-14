import time
import threading
import blocker
import notifier
import audit

# Ban durations in seconds — 10min, 30min, 2hours, then permanent
BAN_DURATIONS = [600, 1800, 7200]
offence_count = {}

def get_ban_duration(source_ip):
    count = offence_count.get(source_ip, 0)
    if count >= len(BAN_DURATIONS):
        return None  # permanent ban
    return BAN_DURATIONS[count]

def schedule_unban(source_ip, condition, current_rate, baseline_mean):
    duration = get_ban_duration(source_ip)
    offence_count[source_ip] = offence_count.get(source_ip, 0) + 1

    if duration is None:
        audit.log(
            "BAN_PERMANENT",
            ip=source_ip,
            condition=condition,
            rate=current_rate,
            baseline=baseline_mean,
            duration="permanent"
        )
        notifier.send_ban_alert(
            source_ip, condition, current_rate,
            baseline_mean, "permanent"
        )
        return

    audit.log(
        "BAN",
        ip=source_ip,
        condition=condition,
        rate=current_rate,
        baseline=baseline_mean,
        duration=f"{duration}s"
    )
    notifier.send_ban_alert(
        source_ip, condition, current_rate,
        baseline_mean, f"{duration}s"
    )

    def unban():
        time.sleep(duration)
        blocker.unblock(source_ip)
        audit.log(
            "UNBAN",
            ip=source_ip,
            condition=condition,
            rate=current_rate,
            baseline=baseline_mean,
            duration=f"{duration}s"
        )
        notifier.send_unban_alert(source_ip, duration)

    thread = threading.Thread(target=unban, daemon=True)
    thread.start()
