import subprocess

BLOCKED_IPS = set()

def block(source_ip):
    if source_ip in BLOCKED_IPS:
        return
    
    BLOCKED_IPS.add(source_ip)
    subprocess.run([
        "iptables", "-A", "INPUT",
        "-s", source_ip,
        "-j", "DROP"
    ])
    print(f"Blocked IP: {source_ip}")

def unblock(source_ip):
    if source_ip not in BLOCKED_IPS:
        return
    
    BLOCKED_IPS.discard(source_ip)
    subprocess.run([
        "iptables", "-D", "INPUT",
        "-s", source_ip,
        "-j", "DROP"
    ])
    print(f"Unblocked IP: {source_ip}")
