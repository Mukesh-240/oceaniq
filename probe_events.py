"""Probe every GFW event dataset at the transposed origin box.

The gaps-only query returns 0 candidates for the demo scenario. Before deciding
what the dashboard should show, ask whether ANY real vessel activity exists at
that location and window across the other public event datasets.

A failed request is NOT a zero result. An earlier version of this script
conflated the two and reported "ZERO real events" when in fact all five requests
had timed out - that is how a network problem gets published as evidence of
absence. Failures are now reported as UNKNOWN and never counted as zeros.
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "golden_case"))
from build_golden_case import gfw_post  # noqa: E402

payload = json.loads(Path("golden_case/expected_output.json").read_text())
geom = payload["origin_region"]["polygon"]
win = payload["origin_region"]["time_window"]
ring = geom["coordinates"][0]
print(f"origin box  lon {min(p[0] for p in ring):.4f}..{max(p[0] for p in ring):.4f}  "
      f"lat {min(p[1] for p in ring):.4f}..{max(p[1] for p in ring):.4f}")
print(f"demo window {win['start']} -> {win['end']}")
print(f"scenario    {payload.get('scenario')}\n")

DATASETS = {
    "gaps":        "public-global-gaps-events:latest",
    "fishing":     "public-global-fishing-events:latest",
    "loitering":   "public-global-loitering-events:latest",
    "encounters":  "public-global-encounters-events:latest",
    "port_visits": "public-global-port-visits-events:latest",
}

# A full year first: if a year at this location is empty, the 12h demo window
# cannot be anything but empty, and each request is slow.
WINDOWS = {"all of 2024": ("2024-01-01", "2024-12-31")}

results = {}
for wname, (d0, d1) in WINDOWS.items():
    print(f"--- {wname}: {d0} -> {d1} ---")
    for label, ds in DATASETS.items():
        body = {"datasets": [ds], "startDate": d0, "endDate": d1, "geometry": geom}
        st, res = None, None
        for attempt in range(3):
            st, res = gfw_post("/v3/events", {"limit": 50, "offset": 0}, body, timeout=90)
            if st in (200, 201):
                break
            time.sleep(4)
        if st in (200, 201):
            total = res.get("total", 0)
            print(f"  {label:<12} HTTP {st}  total={total}")
            results[(wname, label)] = (st, total, res.get("entries", []))
        else:
            print(f"  {label:<12} FAILED after 3 attempts: {str(res)[:100]}")
            results[(wname, label)] = (st, None, [])
    print()

answered = {k: v for k, v in results.items() if v[1] is not None}
failed = {k: v for k, v in results.items() if v[1] is None}
hits = {k: v for k, v in answered.items() if v[1] > 0}

print("=" * 70)
print(f"datasets answered: {len(answered)}   failed/unknown: {len(failed)}")
for (w, l), (st, total, entries) in hits.items():
    print(f"HIT  {w} / {l}: {total} events")
    for e in entries[:8]:
        v = e.get("vessel") or {}
        print(f"      {e.get('start', '')[:16]}  {v.get('name') or v.get('ssvid')}  "
              f"flag={v.get('flag')}  type={v.get('type')}")
for (w, l) in failed:
    print(f"UNKNOWN  {w} / {l}: request failed, result is NOT known to be zero")
if answered and not hits:
    print(f"\nGFW answered {len(answered)} dataset(s), reporting 0 events for each.")
if not answered:
    print("\nNO dataset answered. Nothing can be concluded about vessel presence.")

Path("probe_events_result.json").write_text(json.dumps(
    {f"{w}|{l}": {"http": v[0], "total": v[1]} for (w, l), v in results.items()},
    indent=2))
print("\nwritten: probe_events_result.json")
