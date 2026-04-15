# HNG DevOps Stage 0 — Hardened Linux Server Setup

**Author:** Gbemi.L  
**Track:** DevOps  
**Task:** Provision, secure, and configure a live hardened Linux server with Nginx, SSL, and strict access controls.

---

## Table of Contents

1. [Real-World Scenario](#real-world-scenario)
2. [Key Concepts Explained Simply](#key-concepts-explained-simply)
3. [Architecture Overview](#architecture-overview)
4. [Prerequisites](#prerequisites)
5. [Phase 0 — Launch AWS EC2 Instance](#phase-0--launch-aws-ec2-instance)
6. [Phase 1 — Connect and Update](#phase-1--connect-and-update)
7. [Phase 2 — Install All Packages](#phase-2--install-all-packages)
8. [Phase 3 — Create the hngdevops User](#phase-3--create-the-hngdevops-user)
9. [Phase 4 — Configure Sudoers](#phase-4--configure-sudoers)
10. [Phase 5 — SSH Key Setup for hngdevops](#phase-5--ssh-key-setup-for-hngdevops)
11. [Phase 6 — UFW Firewall](#phase-6--ufw-firewall)
12. [Phase 7 — Nginx Web Server](#phase-7--nginx-web-server)
13. [Phase 8 — SSL with Let's Encrypt (Certbot)](#phase-8--ssl-with-lets-encrypt-certbot)
14. [Phase 9 — 301 HTTP to HTTPS Redirect](#phase-9--301-http-to-https-redirect)
15. [Phase 10 — Harden SSHD (Last Step)](#phase-10--harden-sshd-last-step)
16. [Phase 11 — Add Grading Bot SSH Key](#phase-11--add-grading-bot-ssh-key)
17. [Phase 12 — Final Verification Checklist](#phase-12--final-verification-checklist)
18. [Troubleshooting](#troubleshooting)

---

## Real-World Scenario

### "You just joined a startup as their first DevOps engineer"

Imagine you've been hired by a fintech startup called **PayStack clone** that is launching a new payment API. Your job on Day 1 is to set up the production web server that will serve their API and landing page.

The CTO tells you:

> "We need a server that is locked down tight. Only our developers should be able to SSH in — and only with their keys, no passwords. The website must run over HTTPS. If anything goes wrong with the firewall or SSH, you need to be able to fix it without giving your developers full root access."

This is **exactly** what this task simulates. Here is how each piece maps to the real world:

| Task Component | Real-World Equivalent |
|---|---|
| Creating `hngdevops` user | Creating a `deploy` or `devops` user for your team |
| Restricting sudo to `sshd` and `ufw` only | Giving your team just enough access to diagnose issues without full root |
| Disabling password SSH | Preventing brute-force attacks (hackers try millions of passwords per second) |
| UFW firewall — ports 22, 80, 443 only | Closing every door in your building except the front door, fire exit, and delivery bay |
| Nginx serving `/` and `/api` | A real production web server handling your landing page and API routes |
| Let's Encrypt SSL | The green padlock in your browser — without it, Chrome shows "Not Secure" and users leave |
| 301 redirect HTTP → HTTPS | Making sure nobody accidentally visits the insecure version of your site |

In production companies like Flutterwave, Paystack, or any SaaS startup, a junior DevOps engineer's first task is often exactly this — provisioning and hardening a server before the developers deploy their code onto it.

---

## Key Concepts Explained Simply

### What is UFW?

**UFW stands for Uncomplicated Firewall.** Think of your server as a building with 65,535 doors (called ports). By default, anyone on the internet can knock on any door. UFW is the security guard who stands at the entrance and has a list of which doors are allowed to open.

```
Without UFW:
Internet ──► [Door 22] OPEN (SSH)
         ──► [Door 80] OPEN (HTTP)  
         ──► [Door 3306] OPEN (MySQL — dangerous!)
         ──► [Door 8080] OPEN (Dev server — dangerous!)
         ──► ... 65,532 more open doors

With UFW (default deny):
Internet ──► [Door 22]   OPEN  ✅ (you allowed it)
         ──► [Door 80]   OPEN  ✅ (you allowed it)
         ──► [Door 443]  OPEN  ✅ (you allowed it)
         ──► [Door 3306] SLAM  ❌ (blocked — attacker gets nothing)
         ──► [Door 8080] SLAM  ❌ (blocked — attacker gets nothing)
         ──► ... all others slammed shut
```

The key command is `ufw default deny incoming` — this is the "slam all doors by default" instruction. Then you selectively open only what you need.

---

### What is /usr/sbin/?

The Linux filesystem has multiple folders for programs (called binaries). Here is a simple map:

```
/bin/         — Basic tools every user needs (ls, cat, cp)
/usr/bin/     — More user tools (python3, curl, git)
/sbin/        — System admin tools, usually need root (shutdown, ifconfig)
/usr/sbin/    — More system admin tools (sshd, ufw, nginx)
```

The `s` in `sbin` stands for **system**. These are tools that manage the operating system itself — not just files and text, but networking, services, and security.

When the sudoers file says `/usr/sbin/sshd` and `/usr/sbin/ufw`, it is saying: "hngdevops is allowed to run these specific system tools as root — and nothing else." It is like giving a technician a key to one specific room in a building, not the master key.

**Why does the path matter?** Sudo matches rules by the exact binary path. If you write `/usr/sbin/ufw` in sudoers but the actual `ufw` binary lives at `/usr/bin/ufw`, the rule silently fails and sudo asks for a password instead. Always verify with `which ufw` and `which sshd` first.

---

### What is SSH and Why Keys Instead of Passwords?

SSH (Secure Shell) is how you connect to a remote server over the internet — like a secure telephone line between your laptop and the server.

**Password authentication** is like a combination lock. If someone tries enough combinations (automated tools can try millions per second), they will eventually get in. This is called a **brute-force attack**.

**Key-based authentication** is like a physical key and lock. You have a private key (stays on your laptop, never shared), and the server has a public key (like a padlock — safe to share). The server checks: "does this person's private key match the public key I have on file?" Without the private key file, it is mathematically impossible to get in — no amount of guessing helps.

```
Password Auth:          Key Auth:
                        
Attacker types:         Attacker needs:
"password123"   ❌      Your actual .pem file  ❌ (they don't have it)
"admin"         ❌      Mathematically impossible to guess
"qwerty"        ❌      
... 10 million more     Server says: "Who are you? No key = no entry."
Eventually: ✅ IN       
```

Disabling password auth (`PasswordAuthentication no`) removes the combination lock entirely and keeps only the physical key lock.

---

### What is Nginx?

Nginx (pronounced "engine-x") is a web server. Think of it as a receptionist in a large office building.

When someone visits your website, their browser sends a request to your server. Nginx receives that request and decides where to route it:

```
Browser requests https://yourdomain.com/        
    → Nginx checks: "I have a rule for /"
    → Returns: index.html (the static page)

Browser requests https://yourdomain.com/api     
    → Nginx checks: "I have a rule for /api"
    → Returns: JSON response

Browser requests http://yourdomain.com/         
    → Nginx checks: "This is HTTP, not HTTPS"
    → Returns: 301 redirect to https://
```

Nginx is one of the most widely used web servers in the world. Companies like Cloudflare, Netflix, and Dropbox use it to handle millions of requests per second.

---

### What is SSL/TLS and Why Does It Matter?

When you visit a site over plain HTTP, your data travels across the internet in plain text — like sending a postcard. Anyone along the route (your ISP, a hacker on the same WiFi, a government) can read it.

HTTPS adds SSL/TLS encryption — like putting your postcard inside a sealed envelope that only the recipient can open.

**Let's Encrypt** is a free, automated, and open Certificate Authority (CA). A CA is a trusted organisation that vouches for your identity — they say: "We verified that this domain belongs to this server." Browsers trust Let's Encrypt, so when they see your certificate, they show the green padlock instead of "Not Secure."

**Self-signed certificates** are certificates you sign yourself — like writing your own reference letter. Browsers don't trust them and show a scary warning page.

---

### What is a 301 vs 302 Redirect?

When someone types `http://yourdomain.com`, you want to send them to `https://yourdomain.com`. There are different ways to do this:

| Redirect Type | Meaning | Browser Behaviour | SEO Impact |
|---|---|---|---|
| 301 Moved Permanently | "This page has moved forever" | Browser remembers and goes directly next time | Full SEO value transferred |
| 302 Found (Temporary) | "This page has moved for now" | Browser asks again every time | SEO value not transferred |
| Rewrite hack | Nginx internally rewrites URL | Looks like redirect but is not | Inconsistent |

For HTTPS redirects, you always want 301 — it is permanent, clean, and correct. The proper way in Nginx is:

```nginx
return 301 https://$host$request_uri;
```

Not a `rewrite` rule — a proper `return 301`.

---

### What is Sudo and the Principle of Least Privilege?

`sudo` means "superuser do" — it lets a regular user run a specific command as root (the all-powerful admin account).

**The Principle of Least Privilege** is a security concept that means: give every user or process only the minimum permissions it needs to do its job — nothing more.

```
Bad sudoers (too much access):
hngdevops ALL=(ALL) ALL
→ hngdevops can run ANY command as root
→ One mistake or hack = entire server compromised

Good sudoers (least privilege):
hngdevops ALL=(root) NOPASSWD:/usr/sbin/sshd,/usr/sbin/ufw
→ hngdevops can ONLY run sshd and ufw as root
→ Even if hngdevops account is hacked, damage is limited
```

This is exactly how real companies configure their DevOps users — enough access to diagnose and manage the specific services they own, nothing more.

---

## Architecture Overview

```
                        INTERNET
                           │
                    [Your Domain]
               yourname.duckdns.org
                           │
                    ┌──────▼──────┐
                    │  AWS EC2    │
                    │  (Ubuntu)   │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │    UFW      │  ← Only ports 22, 80, 443
                    │  Firewall   │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
         Port 22       Port 80      Port 443
           SSH         HTTP         HTTPS
              │            │            │
         ┌────▼────┐  ┌────▼────────────▼────┐
         │  SSHD   │  │        Nginx          │
         │ (keys   │  │  /  → index.html      │
         │  only)  │  │  /api → JSON response │
         └────┬────┘  │  http → 301 → https   │
              │       └───────────────────────┘
         ┌────▼────┐
         │hngdevops│  ← Only sudo: sshd, ufw
         │  user   │
         └─────────┘
```

---

## Prerequisites

Before starting, you need:

- An AWS account (free tier)
- A DuckDNS account (free) at https://www.duckdns.org
- Your SSH key `.pem` file saved locally
- A terminal (Mac/Linux) or PuTTY (Windows)

---

## Phase 0 — Launch AWS EC2 Instance

### In the AWS Console:

1. Go to **EC2 → Launch Instance**
2. Name: `hng-devops-stage0`
3. AMI: **Ubuntu Server 24.04 LTS** (Free tier eligible)
4. Instance type: **t2.micro** (Free tier — 750 hours/month)
5. Key pair: **Create new key pair**
   - Name: `hngdevops-key`
   - Type: ED25519
   - Format: `.pem`
   - Download and save it safely
6. Network settings → **Edit**:
   - Auto-assign public IP: **Enabled**
   - Create new security group with these inbound rules:

| Type  | Port | Source    |
|-------|------|-----------|
| SSH   | 22   | 0.0.0.0/0 |
| HTTP  | 80   | 0.0.0.0/0 |
| HTTPS | 443  | 0.0.0.0/0 |

7. Storage: 8GB gp3 (default)
8. Click **Launch Instance**

### Fix key permissions on your local machine:

```bash
chmod 400 ~/.ssh/hngdevops-key.pem
```

### Set up your DuckDNS domain:

1. Go to https://www.duckdns.org and sign in with Google/GitHub
2. Create a subdomain (e.g. `gbemihng14`)
3. Paste your EC2 public IP and click **Update IP**
4. Verify DNS propagated:

```bash
dig +short gbemihng14.duckdns.org
# Must return your EC2 IP
```

---

## Phase 1 — Connect and Update

```bash
# Connect as ubuntu (default AWS user)
ssh -i ~/.ssh/hngdevops-key.pem ubuntu@YOUR_EC2_PUBLIC_IP

# Update the system
sudo apt update && sudo apt upgrade -y
```

---

## Phase 2 — Install All Packages

Install everything upfront so you don't hit permission issues later:

```bash
sudo apt install -y nginx ufw certbot python3-certbot-nginx curl
```

---

## Phase 3 — Create the hngdevops User

```bash
# Create the user
sudo adduser --gecos "" hngdevops
# Set a strong password when prompted

# Verify the user was created
id hngdevops
```

---

## Phase 4 — Configure Sudoers

This is the most critical security step. The sudoers rule must match the task spec exactly.

```bash
# Write the rule
echo 'hngdevops ALL=(root) NOPASSWD:/usr/sbin/sshd,/usr/sbin/ufw' | \
  sudo tee /etc/sudoers.d/hngdevops

# Set correct permissions on the file
sudo chmod 0440 /etc/sudoers.d/hngdevops

# Validate — must say "parsed OK"
sudo visudo -c -f /etc/sudoers.d/hngdevops
```

### Verify binary paths match:

```bash
which sshd   # Must return /usr/sbin/sshd
which ufw    # Must return /usr/sbin/ufw
```

> **Important:** If `which` returns a different path (e.g. `/usr/bin/ufw`), update the sudoers file accordingly. A path mismatch silently breaks the rule.

### Test the sudo rules work:

```bash
sudo -u hngdevops sudo sshd -T | head -3   # Must work without password
sudo -u hngdevops sudo ufw status           # Must work without password
```

---

## Phase 5 — SSH Key Setup for hngdevops

```bash
# Create .ssh directory
sudo mkdir -p /home/hngdevops/.ssh

# Copy your existing key (same .pem file works for both users)
sudo cp /home/ubuntu/.ssh/authorized_keys /home/hngdevops/.ssh/authorized_keys

# Fix permissions — SSH is strict about this
sudo chmod 700 /home/hngdevops/.ssh
sudo chmod 600 /home/hngdevops/.ssh/authorized_keys
sudo chown -R hngdevops:hngdevops /home/hngdevops/.ssh

# Verify
sudo cat /home/hngdevops/.ssh/authorized_keys
```

---

## Phase 6 — UFW Firewall

```bash
# Reset to clean state
sudo ufw --force reset

# Default: deny all incoming traffic
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow only the 3 required ports
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Enable the firewall
sudo ufw --force enable

# Verify
sudo ufw status verbose
```

### Expected output:

```
Status: active
Default: deny (incoming), allow (outgoing)

To                         Action      From
--                         ------      ----
22/tcp                     ALLOW IN    Anywhere
80/tcp                     ALLOW IN    Anywhere
443/tcp                    ALLOW IN    Anywhere
```

> **AWS Note:** UFW and AWS Security Groups are two independent firewall layers. Both must allow the port for traffic to reach your server. The Security Group was configured in Phase 0.

---

## Phase 7 — Nginx Web Server

### Create the web root:

```bash
sudo mkdir -p /var/www/hngdevops
```

### Create the HTML page:

```bash
sudo nano /var/www/hngdevops/index.html
```

Paste the following — replace `Gbemi.L` with your exact HNG username (casing matters):

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gbemi.L</title>
</head>
<body>
    <h1>Gbemi.L</h1>
    <p>HNG DevOps Track — Stage 0</p>
</body>
</html>
```

Save with `Ctrl+X → Y → Enter`

### Create the Nginx config:

```bash
sudo nano /etc/nginx/sites-available/hngdevops
```

Paste the following — replace `gbemihng14.duckdns.org` with your actual domain and `Gbemi.L` with your exact HNG username:

```nginx
server {
    listen 80;
    listen [::]:80;
    server_name gbemihng14.duckdns.org;

    root /var/www/hngdevops;
    index index.html;

    location / {
        try_files $uri $uri/ =404;
    }

    location /api {
        default_type application/json;
        add_header Content-Type 'application/json; charset=utf-8' always;
        return 200 '{"message":"HNGI14 Stage 0","track":"DevOps","username":"Gbemi.L"}';
    }
}
```

### Enable the site:

```bash
# Create symlink to enable
sudo ln -s /etc/nginx/sites-available/hngdevops /etc/nginx/sites-enabled/

# Remove default site
sudo rm -f /etc/nginx/sites-enabled/default

# Test config — must say "test is successful"
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx
```

### Verify Nginx is serving:

```bash
curl -s http://gbemihng14.duckdns.org | grep "Gbemi.L"
curl -s http://gbemihng14.duckdns.org/api
```

---

## Phase 8 — SSL with Let's Encrypt (Certbot)

> **Why not self-signed?** Self-signed certificates are not trusted by browsers or automated tools. The grading bot's HTTP client will reject a self-signed cert and fail you. Let's Encrypt is free, trusted, and renews automatically.

Before running Certbot, confirm DNS resolves to your server:

```bash
dig +short gbemihng14.duckdns.org
# Must return your EC2 IP
```

Run Certbot:

```bash
sudo certbot --nginx \
  -d gbemihng14.duckdns.org \
  --non-interactive \
  --agree-tos \
  -m your@email.com
```

Certbot will automatically:
- Verify you own the domain
- Obtain a valid certificate from Let's Encrypt
- Update your Nginx config with SSL directives
- Set up auto-renewal via a cron job

### Verify SSL:

```bash
curl -vI https://gbemihng14.duckdns.org 2>&1 | grep -i issuer
# Must show: issuer: C=US, O=Let's Encrypt
```

---

## Phase 9 — 301 HTTP to HTTPS Redirect

Certbot may have added a redirect. Check first:

```bash
sudo cat /etc/nginx/sites-available/hngdevops | grep -E "301|redirect|return"
```

If no 301 redirect exists, add it manually. Open the config:

```bash
sudo nano /etc/nginx/sites-available/hngdevops
```

Find the port 80 `server` block (the one without SSL directives) and replace its contents with this single line:

```nginx
server {
    listen 80;
    listen [::]:80;
    server_name gbemihng14.duckdns.org;

    return 301 https://$host$request_uri;
}
```

> **Why `$host` and not `$server_name`?** `$host` captures the actual hostname from the request, which handles edge cases like `www.` prefixes more gracefully. It is the correct production pattern.

Save and reload:

```bash
sudo nginx -t && sudo systemctl reload nginx
```

### Verify the 301:

```bash
curl -I http://gbemihng14.duckdns.org
```

Expected output:

```
HTTP/1.1 301 Moved Permanently
Location: https://gbemihng14.duckdns.org/
```

---

## Phase 10 — Harden SSHD (Last Step)

> **Critical:** Always harden SSHD **last** — after everything else is working and tested. Hardening SSH first is the most common cause of getting permanently locked out.

Back up the config first:

```bash
sudo cp /etc/ssh/sshd_config /etc/ssh/sshd_config.bak
```

Open and edit:

```bash
sudo nano /etc/ssh/sshd_config
```

Find each directive, remove the `#` if present, and set the correct value:

```
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
AuthorizedKeysFile .ssh/authorized_keys .ssh/authorized_keys2
PermitEmptyPasswords no
KbdInteractiveAuthentication no
```

Add at the very bottom of the file:

```
AllowUsers hngdevops ubuntu
```

Save with `Ctrl+X → Y → Enter`, then test and restart:

```bash
# Test config — no output means no errors
sudo sshd -t

# Restart SSH service (Ubuntu 24.04 uses "ssh" not "sshd")
sudo systemctl restart ssh
```

### Test connections before closing your current terminal:

Open a **new terminal** on your local machine and test both users:

```bash
# Test ubuntu still works
ssh -i ~/.ssh/hngdevops-key.pem ubuntu@YOUR_EC2_IP

# Test hngdevops works
ssh -i ~/.ssh/hngdevops-key.pem hngdevops@YOUR_EC2_IP
```

Only close your original terminal once both succeed.

Once confirmed, remove `ubuntu` from `AllowUsers` to match the spec:

```bash
sudo nano /etc/ssh/sshd_config
# Change: AllowUsers hngdevops ubuntu
# To:     AllowUsers hngdevops

sudo sshd -t && sudo systemctl restart ssh
```

---

## Phase 11 — Add Grading Bot SSH Key

The grading bot SSHes into your server as `hngdevops` to verify configuration. Its public key is posted in the `#track-devops` Slack channel.

Add it without overwriting your own key (note the `>>` append operator):

```bash
sudo sh -c 'echo "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIMY5tseRHC4RfDEZv72ggwi1RpYJZLJmZkcKt/zxcfaJ jameskefaslungu@gmail.com" >> /home/hngdevops/.ssh/authorized_keys'
```

Verify both keys are present:

```bash
sudo cat /home/hngdevops/.ssh/authorized_keys
# Must show 2 lines — your key and the bot's key
```

---

## Phase 12 — Final Verification Checklist

Run this full check before submitting:

```bash
SERVER="gbemihng14.duckdns.org"

echo "=== 1. Username visible on page ==="
curl -s https://$SERVER | grep "Gbemi.L"

echo "=== 2. API HTTP status ==="
curl -o /dev/null -s -w "%{http_code}\n" https://$SERVER/api

echo "=== 3. API JSON response ==="
curl -s https://$SERVER/api

echo "=== 4. HTTP to HTTPS redirect ==="
curl -I http://$SERVER 2>/dev/null | grep -E "HTTP|Location"

echo "=== 5. SSL certificate issuer ==="
curl -vI https://$SERVER 2>&1 | grep -i issuer

echo "=== 6. UFW firewall status ==="
sudo ufw status verbose

echo "=== 7. sudo sshd -T as hngdevops (no password) ==="
sudo -u hngdevops sudo sshd -T | head -3

echo "=== 8. sudo ufw status as hngdevops (no password) ==="
sudo -u hngdevops sudo ufw status

echo "=== 9. Nginx active ==="
sudo systemctl is-active nginx
```

### What passing looks like:

| Check | Expected Result |
|---|---|
| Username on page | `Gbemi.L` visible in HTML |
| API status | `200` |
| API JSON | `{"message":"HNGI14 Stage 0","track":"DevOps","username":"Gbemi.L"}` |
| HTTP redirect | `HTTP/1.1 301 Moved Permanently` |
| SSL issuer | `Let's Encrypt` |
| UFW status | Active, ports 22/80/443 only |
| sudo sshd -T | No password prompt |
| sudo ufw status | No password prompt |
| Nginx | `active` |

---

## Troubleshooting

### Locked out of SSH

Use **EC2 Instance Connect** in the AWS Console as an emergency backdoor:
- EC2 → Instances → Connect → EC2 Instance Connect → username: `ubuntu`

### UFW locked me out on port 22

If UFW is enabled before allowing port 22:

```bash
# From EC2 Instance Connect
sudo ufw allow 22/tcp
sudo ufw status
```

### Certbot fails — domain not resolving

```bash
# Check DNS
dig +short yourdomain.duckdns.org
# If wrong IP — go to duckdns.org and update

# If correct but still fails, wait 2-3 minutes and retry
```

### sudo still asking for password

```bash
# Check the file exists and has correct content
sudo cat /etc/sudoers.d/hngdevops

# Verify binary paths match exactly
which sshd && which ufw

# Validate syntax
sudo visudo -c -f /etc/sudoers.d/hngdevops
```

### EC2 IP changed after restart

Stop/start changes your public IP. Fix it:

```bash
# Go to DuckDNS and update the IP
# Or allocate an Elastic IP in AWS (free while attached to running instance):
# AWS Console → EC2 → Elastic IPs → Allocate → Associate with instance
```

### Nginx config test fails

```bash
sudo nginx -t
# Read the error — it shows the exact file and line number

# Common issue: missing semicolon or bracket
# Always check: nginx -t before reloading
```

---

## Important Notes

- **Never stop your EC2 instance before grading is confirmed.** Stopping changes the public IP and breaks DNS.
- **Username casing is exact.** `Gbemi.L` ≠ `gbemi.l` ≠ `GBEMI.L`. The grading bot does an exact string match with no feedback on failure.
- **SSH service name on Ubuntu 24.04** is `ssh`, not `sshd`. Use `sudo systemctl restart ssh`.
- **Two firewall layers on AWS:** UFW (OS level) and Security Groups (AWS level). Both must allow the port.
- **Certbot auto-renewal** is set up automatically. Certificates expire every 90 days and renew automatically via a cron job at `/etc/cron.d/certbot`.

---

*This README documents the complete setup for HNG DevOps Stage 0. All configurations are production-grade and reflect real-world hardened server practices.*
