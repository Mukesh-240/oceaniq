import streamlit as st
import folium
from streamlit_folium import st_folium
import json
import os

st.set_page_config(layout="wide", page_title="OCEANIQ Dashboard")

st.title("OCEANIQ Dashboard: Investigating Spill Origins")

# --- HONESTY CAVEATS ---
st.warning("""
**Disclaimer & Caveats (Hackathon POC):**
* **Heuristic look-alike screening** — not a trained classifier.
* **Demo georeferencing** — assumes a static anchor and pixel size.
* **Investigative leads, not a verdict** — this tool flags suspicious vessels, it does not prove guilt.
""")

def load_fixtures():
    # Load all fixtures safely
    data = {}
    for fix in ["spill_seeds", "drift_origin", "expected_ranking"]:
        path = f"fixtures/{fix}.json"
        if os.path.exists(path):
            with open(path, "r") as f:
                data[fix] = json.load(f)
        else:
            data[fix] = [] if fix != "drift_origin" else {}
    return data

data = load_fixtures()

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Geospatial View")
    
    # Initialize map in the Arabian Sea roughly
    m = folium.Map(location=[18.5, 69.1], zoom_start=9)
    
    # 1. Plot Spill Polygon (from spill_seeds)
    if data["spill_seeds"]:
        points = [(p["lat"], p["lon"]) for p in data["spill_seeds"]]
        folium.Polygon(
            locations=points,
            color="red",
            fill=True,
            tooltip="Detected Spill Surface"
        ).add_to(m)
        
    # 2. Plot Backtracked Origin
    origin = data.get("drift_origin", {})
    if origin and "origin_bbox" in origin:
        bbox = origin["origin_bbox"]
        # bbox is [minLon, minLat, maxLon, maxLat]
        folium.Rectangle(
            bounds=[[bbox[1], bbox[0]], [bbox[3], bbox[2]]],
            color="blue",
            fill=True,
            tooltip="Estimated Backtracked Origin"
        ).add_to(m)
        
    st_folium(m, width=700, height=500)

with col2:
    st.subheader("Ranked Suspects")
    
    ranking = data.get("expected_ranking", [])
    if not ranking:
        st.info("No suspects found or fixtures missing.")
        
    for idx, suspect in enumerate(ranking):
        with st.expander(f"#{idx+1} {suspect['name']} (Score: {suspect['total_score']})"):
            st.write(f"**MMSI:** {suspect['mmsi']}")
            st.write(f"**Flag:** {suspect['flag']}")
            
            st.markdown("#### Evidence Breakdown")
            bd = suspect.get("breakdown", {})
            for clue, details in bd.items():
                score = details.get("score", 0)
                reason = details.get("reason", "N/A")
                st.write(f"- **{clue.capitalize()}:** {score} pts — {reason}")

