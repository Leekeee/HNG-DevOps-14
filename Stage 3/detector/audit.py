import time

AUDIT_LOG_PATH = "/app/audit.log"

def log(action, ip=None, condition=None, rate=None, baseline=None, duration=None):
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())
    
    parts = [f"[{timestamp}] {action}"]
    
    if ip:
        parts.append(f"ip={ip}")
    if condition:
        parts.append(f"condition={condition}")
    if rate is not None:
        parts.append(f"rate={rate:.2f}")
    if baseline is not None:
        parts.append(f"baseline={baseline:.2f}")
    if duration:
        parts.append(f"duration={duration}")
    
    entry = " | ".join(parts)
    
    print(entry)
    
    with open(AUDIT_LOG_PATH, "a") as f:
        f.write(entry + "\n")
