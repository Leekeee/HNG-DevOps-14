import time
import psutil
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import blocker
import baseline

app = FastAPI()
START_TIME = time.time()

def get_uptime():
    seconds = int(time.time() - START_TIME)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours}h {minutes}m {secs}s"

def get_top_ips(n=10):
    ip_rates = {}
    for ip, window in baseline.ip_windows.items():
        now = int(time.time())
        rate = sum(1 for t in window if now - t <= 1)
        ip_rates[ip] = rate
    return sorted(ip_rates.items(), key=lambda x: x[1], reverse=True)[:n]

@app.get("/", response_class=HTMLResponse)
def index():
    blocked = list(blocker.BLOCKED_IPS)
    global_mean, global_std = baseline.get_global_baseline()
    global_rate = baseline.get_current_rate(baseline.global_window)
    top_ips = get_top_ips()
    cpu = psutil.cpu_percent()
    memory = psutil.virtual_memory().percent
    uptime = get_uptime()

    blocked_rows = "".join(
        f"<tr><td>{ip}</td></tr>"
        for ip in blocked
    ) or "<tr><td colspan='1'>None</td></tr>"

    top_ip_rows = "".join(
        f"<tr><td>{ip}</td><td>{rate}</td></tr>"
        for ip, rate in top_ips
    ) or "<tr><td colspan='2'>No traffic yet</td></tr>"

    return f"""
    <html>
    <head>
        <title>DDoS Detection Dashboard</title>
        <meta http-equiv="refresh" content="3">
        <style>
            body {{ font-family: monospace; background: #0d1117; color: #c9d1d9; padding: 20px; }}
            h1 {{ color: #58a6ff; }}
            h2 {{ color: #8b949e; border-bottom: 1px solid #21262d; padding-bottom: 5px; }}
            table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
            th {{ background: #161b22; color: #58a6ff; padding: 8px; text-align: left; }}
            td {{ padding: 8px; border-bottom: 1px solid #21262d; }}
            .metric {{ display: inline-block; background: #161b22; padding: 15px 25px;
                      margin: 10px; border-radius: 8px; text-align: center; }}
            .metric-value {{ font-size: 2em; color: #58a6ff; }}
            .metric-label {{ font-size: 0.8em; color: #8b949e; }}
            .status-ok {{ color: #3fb950; }}
            .status-alert {{ color: #f85149; }}
        </style>
    </head>
    <body>
        <h1>🛡️ DDoS Detection Dashboard</h1>
        <p class="status-ok">● System Status: Running | Uptime: {uptime}</p>

        <div>
            <div class="metric">
                <div class="metric-value">{global_rate}</div>
                <div class="metric-label">Global req/s</div>
            </div>
            <div class="metric">
                <div class="metric-value">{len(blocked)}</div>
                <div class="metric-label">Banned IPs</div>
            </div>
            <div class="metric">
                <div class="metric-value">{global_mean:.2f}</div>
                <div class="metric-label">Baseline Mean</div>
            </div>
            <div class="metric">
                <div class="metric-value">{global_std:.2f}</div>
                <div class="metric-label">Baseline Stddev</div>
            </div>
            <div class="metric">
                <div class="metric-value">{cpu}%</div>
                <div class="metric-label">CPU Usage</div>
            </div>
            <div class="metric">
                <div class="metric-value">{memory}%</div>
                <div class="metric-label">Memory Usage</div>
            </div>
        </div>

        <h2>Banned IPs ({len(blocked)})</h2>
        <table>
            <tr><th>IP Address</th></tr>
            {blocked_rows}
        </table>

        <h2>Top 10 Source IPs</h2>
        <table>
            <tr><th>IP Address</th><th>Current req/s</th></tr>
            {top_ip_rows}
        </table>

        <p style="color:#8b949e; font-size:0.8em;">
            Last updated: {time.strftime("%Y-%m-%dT%H:%M:%S")} | Auto-refreshes every 3 seconds
        </p>
    </body>
    </html>
    """

@app.get("/status")
def status():
    global_mean, global_std = baseline.get_global_baseline()
    return {
        "status": "running",
        "uptime": get_uptime(),
        "global_rate": baseline.get_current_rate(baseline.global_window),
        "blocked_ips": list(blocker.BLOCKED_IPS),
        "baseline_mean": global_mean,
        "baseline_std": global_std,
        "cpu_percent": psutil.cpu_percent(),
        "memory_percent": psutil.virtual_memory().percent,
        "top_ips": get_top_ips()
    }

@app.get("/baseline-history", response_class=HTMLResponse)
def baseline_history():
    history = baseline.baseline_history
    
    if not history:
        return "<html><body><p>No baseline data yet — wait a few minutes.</p></body></html>"
    
    times  = [h["time"] for h in history]
    means  = [h["mean"] for h in history]
    
    times_js = str(times)
    means_js = str(means)
    
    return f"""
    <html>
    <head>
        <title>Baseline History</title>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js"></script>
        <meta http-equiv="refresh" content="60">
        <style>
            body {{ background: #0d1117; color: #c9d1d9; font-family: monospace; padding: 20px; }}
            h1 {{ color: #58a6ff; }}
        </style>
    </head>
    <body>
        <h1>Baseline Mean Over Time</h1>
        <p>Updates every 60 seconds. Each point = one baseline recalculation.</p>
        <canvas id="chart" width="900" height="400"></canvas>
        <script>
            const ctx = document.getElementById('chart').getContext('2d');
            new Chart(ctx, {{
                type: 'line',
                data: {{
                    labels: {times_js},
                    datasets: [{{
                        label: 'Effective Mean (req/s)',
                        data: {means_js},
                        borderColor: '#58a6ff',
                        backgroundColor: 'rgba(88,166,255,0.1)',
                        borderWidth: 2,
                        pointRadius: 3,
                        tension: 0.3
                    }}]
                }},
                options: {{
                    responsive: true,
                    scales: {{
                        y: {{
                            beginAtZero: true,
                            ticks: {{ color: '#8b949e' }},
                            grid: {{ color: '#21262d' }}
                        }},
                        x: {{
                            ticks: {{ color: '#8b949e', maxTicksLimit: 15 }},
                            grid: {{ color: '#21262d' }}
                        }}
                    }},
                    plugins: {{
                        legend: {{ labels: {{ color: '#c9d1d9' }} }}
                    }}
                }}
            }});
        </script>
    </body>
    </html>
    """
