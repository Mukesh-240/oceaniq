import streamlit as st
import folium
from streamlit_folium import st_folium
import json
import os

st.set_page_config(layout="wide", page_title="OCEANIQ Dashboard")

st.title("OCEANIQ Dashboard: Investigating Spill Origins")

# --- CONTROLLED VALIDATION SCENARIO banner (read from the payload, not hardcoded) ---
_scen_payload = {}
if os.path.exists("golden_case/expected_output.json"):
    with open("golden_case/expected_output.json", "r") as _f:
        _scen_payload = json.load(_f)
_scenario = _scen_payload.get("scenario")
if _scenario:
    st.error(f"### {_scenario}")
    _detail = _scen_payload.get("scenario_detail")
    if _detail:
        st.caption(_detail)

# --- HONESTY CAVEATS ---
st.warning("""
**Disclaimer & Caveats (Hackathon POC):**
* **Heuristic look-alike screening** — not a trained classifier.
* **Demo georeferencing** — assumes a static anchor and pixel size.
* **Investigative leads, not a verdict** — this tool flags suspicious vessels, it does not prove guilt.
""")

def load_payload():
    path = "golden_case/expected_output.json"
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return {}

def load_origin():
    path = "fixtures/drift_origin.json"
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return {}

payload = load_payload()
origin_data = load_origin()

# B9: Provenance Banner
is_stand_in = "particles" not in origin_data or "drift_hours" not in origin_data
_prov = _scen_payload.get("provenance", {})
has_synthetic = "RECONSTRUCTED" in str(_prov.get("vessel_tracks", ""))
_track_note = _prov.get("vessel_tracks", "")

if is_stand_in or has_synthetic:
    alerts = []
    if is_stand_in:
        alerts.append("ORIGIN: STAND-IN, not a drift run.")
    if has_synthetic:
        alerts.append("TRACKS: Synthetic/mocked paths used.")
    elif _track_note:
        alerts.append("TRACKS: " + _track_note[:120])
        
    st.info("⚠️ **PROVENANCE NOTICE:** " + " | ".join(alerts))

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Geospatial View")
    
    # Initialize map
    _bb = origin_data.get("origin_bbox")
    _centre = [ (_bb[1]+_bb[3])/2, (_bb[0]+_bb[2])/2 ] if _bb else [18.5, 69.1]
    m = folium.Map(location=_centre, zoom_start=9)
    
    if origin_data and "origin_bbox" in origin_data:
        bbox = origin_data["origin_bbox"]
        folium.Rectangle(
            bounds=[[bbox[1], bbox[0]], [bbox[3], bbox[2]]],
            color="blue",
            fill=True,
            tooltip="Estimated Backtracked Origin"
        ).add_to(m)
        
    for suspect in payload.get('candidate_ships', []):
        track = suspect.get("track", [])
        if track:
            coords = track.get("coordinates", []) if isinstance(track, dict) else track
            points = [(c[1], c[0]) for c in coords]   # folium wants (lat, lon)
            folium.PolyLine(
                locations=points,
                color="orange",
                weight=2,
                tooltip=suspect.get("mmsi")
            ).add_to(m)
        
    st_folium(m, width=700, height=500)

with col2:
    st.subheader("Ranked Suspects")
    
    if not payload:
        st.info("No payload found in golden_case/expected_output.json")
        
    for idx, suspect in enumerate(payload.get('candidate_ships', [])):
        total_score = sum(f.get("score", 0) for f in suspect.get("factors", []))
        with st.expander(f"#{idx+1} MMSI: {suspect.get('mmsi')} (Score: {total_score})"):
            for f in suspect.get("factors", []):
                st.write(f"- **{f.get('label')}:** {f.get('score')} pts — {f.get('explanation', '')}")
