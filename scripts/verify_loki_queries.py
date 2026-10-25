import json
import urllib.parse
import urllib.request

def query_loki(query_str):
    params = urllib.parse.urlencode({
        "query": query_str,
        "limit": 50
    })
    url = f"http://127.0.0.1:3100/loki/api/v1/query_range?{params}"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        results = data.get("data", {}).get("result", [])
        lines = []
        for stream in results:
            labels = stream.get("stream", {})
            for val in stream.get("values", []):
                lines.append((val[0], labels, val[1]))
        return lines

if __name__ == "__main__":
    print("=== LOKI QUERY 1: {container=\"expense_tracker_backend\"} ===")
    logs1 = query_loki('{container="expense_tracker_backend"}')
    print(f"Total log lines returned: {len(logs1)}")
    for ts, labels, line in logs1[:5]:
        print(f"  [{ts}] container={labels.get('container')} | {line.strip()}")

    print("\n=== LOKI QUERY 2: {container=\"expense_tracker_backend\"} |= \"error\" ===")
    logs2 = query_loki('{container="expense_tracker_backend"} |= "error"')
    print(f"Total matching lines returned: {len(logs2)}")
    for ts, labels, line in logs2:
        print(f"  [{ts}] container={labels.get('container')} | {line.strip()}")
