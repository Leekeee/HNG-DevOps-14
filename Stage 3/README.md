# HNG DevOps Stage 3 — Anomaly Detection Engine

## Live URLs
- **Metrics Dashboard:** http://gbemihng14.duckdns.org/dashboard/
- **Server IP:** 13.50.1.135
- **Nextcloud:** http://13.50.1.135

## Language Choice
This project is implemented in **Python** because:
- Python's `collections.deque` provides an efficient, built-in sliding window structure
- The `statistics` module handles mean and standard deviation natively
- `subprocess` makes iptables integration straightforward
- FastAPI and Uvicorn provide a lightweight, high-performance web server
- Python is the standard language for DevOps tooling and scripting

## How the Sliding Window Works
Two deque-based windows track request rates in real time:
- **Per-IP window:** tracks timestamps of the last 60 seconds of requests per IP address
- **Global window:** tracks timestamps of all requests across all IPs for the last 60 seconds

Each window uses Python's `deque(maxlen=60)`. When a new request arrives, its timestamp is appended to the right. When the deque is full, the oldest timestamp is automatically evicted from the left — this is the sliding mechanism. No manual cleanup is needed.

To get the current rate, we count how many timestamps in the window fall within the last 1 second:
```python
rate = sum(1 for t in window if now - t <= 1)
```

## How the Baseline Works
- **Window size:** 30 minutes (1800 seconds) of per-second request counts
- **Recalculation interval:** every 60 seconds
- **Per-hour slots:** request counts are also stored per hour of the day
- **Preference logic:** if the current hour has at least 60 data points, the baseline uses that hour's data for higher accuracy. Otherwise it falls back to the full 30-minute rolling window.
- **Floor values:** mean is floored at 1.0 and stddev at 0.5 to prevent division-by-zero and avoid hair-trigger detection on quiet servers.

## Detection Logic
An IP or global rate is flagged as anomalous if either condition fires first:
1. **Z-score > 3.0:** `(current_rate - mean) / stddev > 3.0`
2. **Rate multiplier > 5x:** `current_rate / mean > 5.0`

Additionally, if an IP's 4xx/5xx error rate exceeds 3x its baseline error rate, its detection thresholds are automatically tightened.

## Blocking
- **Per-IP anomaly:** iptables DROP rule added + Slack alert within 10 seconds
- **Global anomaly:** Slack alert only, no block
- **Auto-unban schedule:** 10 min → 30 min → 2 hours → permanent

## Setup Instructions

### 1. Provision a VPS
Minimum: 2 vCPU, 2GB RAM. This project uses AWS EC2 t3.micro with Ubuntu 24.04.

### 2. Install Docker and Docker Compose
```bash
sudo apt-get update
sudo apt-get install -y docker.io docker-compose-v2
sudo usermod -aG docker $USER
newgrp docker
```

### 3. Clone the Repository
```bash
git clone https://github.com/Leekeee/HNG-DevOps-14.git
cd HNG-DevOps-14/Stage\ 3
```

### 4. Set Slack Webhook URL
```bash
echo 'export SLACK_WEBHOOK_URL=https://hooks.slack.com/services/your/url' >> ~/.bashrc
source ~/.bashrc
```

### 5. Build and Start the Stack
```bash
docker compose up --build -d
```

### 6. Verify
```bash
docker ps
curl http://localhost:8000
```

### 7. Open Firewall Ports
```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 8000/tcp
```

## Repository Structure

```
HNG-DevOps-14/
└── Stage 3/
    ├── docker-compose.yml
    ├── README.md
    ├── nginx/
    │   └── nginx.conf
    ├── Detector/
    │   ├── Dockerfile
    │   ├── requirements.txt
    │   ├── config.yaml
    │   ├── main.py
    │   ├── monitor.py
    │   ├── baseline.py
    │   ├── detector.py
    │   ├── blocker.py
    │   ├── unbanner.py
    │   ├── notifier.py
    │   ├── dashboard.py
    │   └── audit.py
    ├── docs/
    │   └── architecture.png
    └── screenshots/
```

## GitHub Repository
https://github.com/Leekeee/HNG-DevOps-14
