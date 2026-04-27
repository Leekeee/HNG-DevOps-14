from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import blocker
import baseline

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
def index():
    blocked = list(blocker.BLOCKED_IPS)
    offence_counts = baseline.ip_windows

    rows = "".join(
        f"<tr><td>{ip}</td><td>{len(offence_counts.get(ip, []))}</td></tr>"
        for ip in blocked
    )

    return f"""
    <html>
    <head><title>DDoS Detection Dashboard</title></head>
    <body>
        <h1>DDoS Detection Dashboard</h1>
        <h2>System Status: Running</h2>
        <h2>Blocked IPs ({len(blocked)})</h2>
        <table border="1">
            <tr><th>IP Address</th><th>Requests in Window</th></tr>
            {rows}
        </table>
    </body>
    </html>
    """

@app.get("/status")
def status():
    return {
        "status": "running",
        "blocked_ips": list(blocker.BLOCKED_IPS),
        "monitored_ips": len(baseline.ip_windows)
    }
