import json
import urllib.parse
import urllib.request

queries = [
    'pg_up',
    'pg_stat_database_xact_commit{datname="expense_tracker"}',
    'pg_stat_database_xact_rollback{datname="expense_tracker"}',
    'pg_stat_activity_count',
    'pg_database_size_bytes{datname="expense_tracker"}',
    'pg_stat_bgwriter_buffers_alloc_total',
    'pg_stat_checkpointer_num_timed_total',
    'pg_stat_checkpointer_write_time_total'
]

print("=== PostgreSQL Exporter Verification ===")
for q in queries:
    url = "http://127.0.0.1:9090/api/v1/query?query=" + urllib.parse.quote(q)
    try:
        with urllib.request.urlopen(url) as r:
            data = json.loads(r.read().decode())
            results = data.get("data", {}).get("result", [])
            if results:
                sample = results[0]["value"][1]
                print(f"[OK] {q:<60} => count: {len(results)}, sample value: {sample}")
            else:
                print(f"[EMPTY] {q:<60} => no data")
    except Exception as e:
        print(f"[ERROR] {q:<60} => {e}")
