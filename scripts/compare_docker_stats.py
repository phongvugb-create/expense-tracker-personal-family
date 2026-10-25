import json
import re
import subprocess
import urllib.request

def get_docker_stats():
    res = subprocess.run(["docker", "stats", "--no-stream", "--format", "{{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"], capture_output=True, text=True, check=True)
    stats = {}
    for line in res.stdout.strip().splitlines():
        parts = line.split("\t")
        if len(parts) >= 3:
            name, cpu, mem = parts[0], parts[1], parts[2]
            if name.startswith("expense_tracker_"):
                stats[name] = {"cpu": cpu, "mem": mem}
    return stats

def get_exporter_metrics():
    with urllib.request.urlopen("http://127.0.0.1:9417/metrics") as r:
        lines = r.read().decode("utf-8").splitlines()
    
    cpu_metrics = {}
    mem_metrics = {}
    for l in lines:
        if l.startswith("docker_container_cpu_percent"):
            m = re.search(r'container="([^"]+)".*\}\s+([0-9\.]+)', l)
            if m:
                cpu_metrics[m.group(1)] = float(m.group(2))
        elif l.startswith("docker_container_memory_bytes"):
            m = re.search(r'container="([^"]+)".*\}\s+([0-9\.]+)', l)
            if m:
                mem_metrics[m.group(1)] = float(m.group(2))
    return cpu_metrics, mem_metrics

def get_prometheus_metrics():
    with urllib.request.urlopen("http://127.0.0.1:9090/api/v1/query?query=docker_container_memory_bytes") as r:
        d = json.loads(r.read().decode())
        prom_mem = {item["metric"]["container"]: float(item["value"][1]) for item in d.get("data", {}).get("result", [])}
    return prom_mem

if __name__ == "__main__":
    cli_stats = get_docker_stats()
    exp_cpu, exp_mem = get_exporter_metrics()
    prom_mem = get_prometheus_metrics()

    print(f"{'Container Name':<38} | {'CLI CPU':<8} | {'Exp CPU %':<10} | {'CLI Mem Usage':<22} | {'Exp Mem (MiB)':<14} | {'Prometheus (MiB)':<16}")
    print("-" * 120)
    for name in sorted(cli_stats.keys()):
        c_stat = cli_stats[name]
        e_cpu = exp_cpu.get(name, 0.0)
        e_mem_bytes = exp_mem.get(name, 0.0)
        e_mem_mib = e_mem_bytes / (1024 * 1024)
        p_mem_mib = prom_mem.get(name, 0.0) / (1024 * 1024)
        print(f"{name:<38} | {c_stat['cpu']:<8} | {e_cpu:>8.2f}% | {c_stat['mem']:<22} | {e_mem_mib:>11.2f} MiB | {p_mem_mib:>13.2f} MiB")
