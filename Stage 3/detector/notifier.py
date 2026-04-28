import os
import urllib.request
import json
import time

SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")

def _post(message):
    if not SLACK_WEBHOOK_URL:
        print("No Slack webhook configured")
        return
    
    data = json.dumps({"text": message}).encode("utf-8")
    req = urllib.request.Request(
        SLACK_WEBHOOK_URL,
        data=data,
        headers={"Content-Type": "application/json"}
    )
    urllib.request.urlopen(req)

def send_ban_alert(source_ip, condition, current_rate, baseline_mean, duration):
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())
    message = (
        f":rotating_light: *IP BAN*\n"
        f"*IP:* `{source_ip}`\n"
        f"*Condition:* `{condition}`\n"
        f"*Current Rate:* `{current_rate:.2f} req/s`\n"
        f"*Baseline Mean:* `{baseline_mean:.2f} req/s`\n"
        f"*Ban Duration:* `{duration}`\n"
        f"*Timestamp:* `{timestamp}`"
    )
    _post(message)

def send_unban_alert(source_ip, duration):
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())
    message = (
        f":white_check_mark: *IP UNBANNED*\n"
        f"*IP:* `{source_ip}`\n"
        f"*Ban Duration Served:* `{duration}s`\n"
        f"*Timestamp:* `{timestamp}`"
    )
    _post(message)

def send_global_alert(condition, current_rate, baseline_mean):
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())
    message = (
        f":warning: *GLOBAL TRAFFIC ANOMALY*\n"
        f"*Condition:* `{condition}`\n"
        f"*Current Rate:* `{current_rate:.2f} req/s`\n"
        f"*Baseline Mean:* `{baseline_mean:.2f} req/s`\n"
        f"*Timestamp:* `{timestamp}`\n"
        f"*Action:* Monitor only — no IP block"
    )
    _post(message)
