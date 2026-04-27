import os
import urllib.request
import urllib.parse
import json

SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")

def send_alert(source_ip, parsed):
    if not SLACK_WEBHOOK_URL:
        print("No Slack webhook configured")
        return

    message = {
        "text": (
            f":rotating_light: *DDoS Alert*\n"
            f"*IP:* `{source_ip}`\n"
            f"*Path:* `{parsed.get('path')}`\n"
            f"*Status:* `{parsed.get('status')}`\n"
            f"*Timestamp:* `{parsed.get('timestamp')}`"
        )
    }

    data = json.dumps(message).encode("utf-8")
    req = urllib.request.Request(
        SLACK_WEBHOOK_URL,
        data=data,
        headers={"Content-Type": "application/json"}
    )
    urllib.request.urlopen(req)
