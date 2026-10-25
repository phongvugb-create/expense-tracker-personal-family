"""
Lightweight Docker Container Stats Exporter for Expense Tracker
Communicates with Docker Engine API via /var/run/docker.sock
Exports real per-container CPU %, Memory bytes, and status.
"""
import http.client
import json
import logging
import os
import socket
import sys
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("docker_stats_exporter")

DOCKER_SOCKET = os.getenv("DOCKER_SOCKET", "/var/run/docker.sock")
CONTAINER_PREFIX = os.getenv("CONTAINER_PREFIX", "expense_tracker_")
SCRAPE_INTERVAL = float(os.getenv("SCRAPE_INTERVAL", "3.0"))
LISTEN_PORT = int(os.getenv("LISTEN_PORT", "9417"))

# Shared state protected by lock
latest_metrics_lock = threading.Lock()
latest_metrics_text = ""
scrape_count = 0
last_scrape_time = 0


class UnixHTTPConnection(http.client.HTTPConnection):
    def __init__(self, socket_path, timeout=5):
        super().__init__("localhost", timeout=timeout)
        self.socket_path = socket_path

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect(self.socket_path)


def query_docker_api(path: str):
    conn = UnixHTTPConnection(DOCKER_SOCKET, timeout=5)
    try:
        conn.request("GET", path)
        res = conn.getresponse()
        if res.status != 200:
            logger.warning(f"Docker API {path} returned status {res.status}")
            return None
        raw = res.read().decode("utf-8")
        return json.loads(raw)
    except Exception as e:
        logger.error(f"Error querying Docker API {path}: {e}")
        return None
    finally:
        conn.close()


def collect_stats_loop():
    global latest_metrics_text, scrape_count, last_scrape_time
    last_cpu_samples = {}  # container_id -> (total_usage, system_usage)

    logger.info(f"Starting collector loop. Prefix='{CONTAINER_PREFIX}', Interval={SCRAPE_INTERVAL}s")

    while True:
        try:
            start_t = time.time()
            containers = query_docker_api("/v1.45/containers/json?all=1")
            if containers is None:
                # Try unversioned endpoint fallback
                containers = query_docker_api("/containers/json?all=1")

            lines = [
                "# HELP docker_container_cpu_percent Container CPU usage percentage",
                "# TYPE docker_container_cpu_percent gauge",
            ]
            cpu_lines = []
            mem_lines = [
                "# HELP docker_container_memory_bytes Container memory usage in bytes",
                "# TYPE docker_container_memory_bytes gauge",
            ]
            mem_limit_lines = [
                "# HELP docker_container_memory_limit_bytes Container memory limit in bytes",
                "# TYPE docker_container_memory_limit_bytes gauge",
            ]
            state_lines = [
                "# HELP docker_container_state Container running status (1 = running, 0 = stopped)",
                "# TYPE docker_container_state gauge",
            ]

            running_count = 0
            total_count = 0

            if containers and isinstance(containers, list):
                for c in containers:
                    c_id = c.get("Id", "")
                    names = c.get("Names", [])
                    raw_name = names[0].lstrip("/") if names else c_id[:12]

                    # Filter containers belonging to Expense Tracker
                    labels = c.get("Labels", {})
                    service_name = labels.get("com.docker.compose.service", raw_name.replace(CONTAINER_PREFIX, ""))
                    
                    if not (raw_name.startswith(CONTAINER_PREFIX) or labels.get("com.docker.compose.project") == "trien_khai_he_thong"):
                        continue

                    total_count += 1
                    state = c.get("State", "").lower()
                    is_running = 1 if state == "running" else 0
                    if is_running:
                        running_count += 1

                    state_lines.append(f'docker_container_state{{container="{raw_name}",service="{service_name}",state="{state}"}} {is_running}')

                    if not is_running:
                        continue

                    # Fetch real-time container stats
                    stats = query_docker_api(f"/v1.45/containers/{c_id}/stats?stream=false")
                    if stats is None:
                        continue

                    # Memory calculation
                    mem_stats = stats.get("memory_stats", {})
                    usage = mem_stats.get("usage", 0)
                    stats_dict = mem_stats.get("stats", {})
                    # cgroup v2 uses inactive_file, cgroup v1 uses cache or total_inactive_file
                    cache = stats_dict.get("inactive_file", stats_dict.get("cache", stats_dict.get("total_inactive_file", 0)))
                    used_bytes = max(0, usage - cache) if (usage > cache and cache > 0) else usage
                    limit_bytes = mem_stats.get("limit", 0)

                    mem_lines.append(f'docker_container_memory_bytes{{container="{raw_name}",service="{service_name}"}} {used_bytes}')
                    mem_limit_lines.append(f'docker_container_memory_limit_bytes{{container="{raw_name}",service="{service_name}"}} {limit_bytes}')

                    # CPU calculation
                    cpu_stats = stats.get("cpu_stats", {})
                    precpu_stats = stats.get("precpu_stats", {})
                    curr_total = cpu_stats.get("cpu_usage", {}).get("total_usage", 0)
                    curr_sys = cpu_stats.get("system_cpu_usage", 0)
                    online_cpus = cpu_stats.get("online_cpus") or len(cpu_stats.get("cpu_usage", {}).get("percpu_usage", [1])) or 1

                    cpu_pct = 0.0
                    if c_id in last_cpu_samples:
                        prev_total, prev_sys = last_cpu_samples[c_id]
                        delta_cpu = curr_total - prev_total
                        delta_sys = curr_sys - prev_sys
                        if delta_sys > 0 and delta_cpu >= 0:
                            cpu_pct = (delta_cpu / delta_sys) * online_cpus * 100.0
                    else:
                        # Fallback to docker precpu_stats if first iteration
                        prev_total = precpu_stats.get("cpu_usage", {}).get("total_usage", 0)
                        prev_sys = precpu_stats.get("system_cpu_usage", 0)
                        delta_cpu = curr_total - prev_total
                        delta_sys = curr_sys - prev_sys
                        if delta_sys > 0 and delta_cpu >= 0:
                            cpu_pct = (delta_cpu / delta_sys) * online_cpus * 100.0

                    last_cpu_samples[c_id] = (curr_total, curr_sys)
                    cpu_lines.append(f'docker_container_cpu_percent{{container="{raw_name}",service="{service_name}"}} {cpu_pct:.2f}')

            # Build final metrics text
            totals_lines = [
                "# HELP docker_containers_total Total Expense Tracker containers tracked",
                "# TYPE docker_containers_total gauge",
                f'docker_containers_total{{status="running"}} {running_count}',
                f'docker_containers_total{{status="total"}} {total_count}',
            ]

            full_payload = "\n".join(
                lines + cpu_lines +
                mem_lines +
                mem_limit_lines +
                state_lines +
                totals_lines +
                [""]
            )

            with latest_metrics_lock:
                latest_metrics_text = full_payload
                scrape_count += 1
                last_scrape_time = time.time()

            elapsed = time.time() - start_t
            sleep_time = max(0.5, SCRAPE_INTERVAL - elapsed)
            time.sleep(sleep_time)

        except Exception as e:
            logger.error(f"Error in collection loop: {e}", exc_info=True)
            time.sleep(2.0)


class MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/metrics":
            with latest_metrics_lock:
                output = latest_metrics_text.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
            self.send_header("Content-Length", str(len(output)))
            self.end_headers()
            self.wfile.write(output)
        elif self.path in ("/", "/health", "/healthz"):
            body = b"OK - Docker Stats Exporter is running\n"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # Silence per-request access logs to keep console clean
        pass


def run_server():
    server = HTTPServer(("0.0.0.0", LISTEN_PORT), MetricsHandler)
    logger.info(f"Serving Prometheus metrics at http://0.0.0.0:{LISTEN_PORT}/metrics")
    server.serve_forever()


if __name__ == "__main__":
    collector_thread = threading.Thread(target=collect_stats_loop, daemon=True)
    collector_thread.start()
    run_server()
