import subprocess
import audit

BLOCKED_IPS = set()

def block(source_ip, condition, current_rate, baseline_mean):
    if source_ip in BLOCKED_IPS:
        return
    
    BLOCKED_IPS.add(source_ip)
    subprocess.run([
        "iptables", "-A", "INPUT",
        "-s", source_ip,
        "-j", "DROP"
    ])
    
    audit.log(
        "BAN",
        ip=source_ip,
        condition=condition,
        rate=current_rate,
        baseline=baseline_mean
    )

def unblock(source_ip):
    if source_ip not in BLOCKED_IPS:
        return
    
    BLOCKED_IPS.discard(source_ip)
    subprocess.run([
        "iptables", "-D", "INPUT",
        "-s", source_ip,
        "-j", "DROP"
    ])
