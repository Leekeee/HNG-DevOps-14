import baseline

def process(parsed, on_anomaly):
    source_ip = parsed.get("source_ip")
    
    if not source_ip:
        return
    
    baseline.record_request(source_ip)
    
    if baseline.is_anomalous(source_ip):
        on_anomaly(parsed)
