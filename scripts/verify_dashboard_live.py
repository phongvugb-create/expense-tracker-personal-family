import base64
import json
import urllib.request
from dotenv import dotenv_values

cfg = dotenv_values(".env")
user = cfg.get("GRAFANA_ADMIN_USER", "admin")
pwd = cfg.get("GRAFANA_ADMIN_PASSWORD", "admin")

auth_header = "Basic " + base64.b64encode(f"{user}:{pwd}".encode()).decode()
req = urllib.request.Request(
    "http://127.0.0.1:3000/api/dashboards/uid/expense-tracker-system-overview",
    headers={"Authorization": auth_header}
)

with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode())
    dash = data.get("dashboard", {})
    print(f"Loaded Dashboard: {dash.get('title')} (UID: {dash.get('uid')})")
    for p in dash.get("panels", []):
        print(f"  - Panel {p.get('id'):2d}: {p.get('title'):<50} [{p.get('type')}]")
