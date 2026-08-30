import json
from datetime import datetime

MAX_GAP_HOURS = 72

def parse_time(t_str):
    if not t_str:
        return None
    t_str = t_str.replace(".000Z", "Z")
    return datetime.strptime(t_str, "%Y-%m-%dT%H:%M:%SZ")

def get_vessel_candidates(origin_bbox, time_window, events_data_path="fixtures/gfw_vessels.json"):
    """
    Parses GFW events to find candidate vessels, applying client-side filtering.
    
    Args:
        origin_bbox: [minLon, minLat, maxLon, maxLat]
        time_window: dict with 'start' and 'end' ISO strings
        events_data_path: path to the JSON response (fixture or live)
        
    Returns:
        List of candidate dictionaries
    """
    window_start = parse_time(time_window['start'])
    window_end = parse_time(time_window['end'])
    
    with open(events_data_path, "r") as f:
        data = json.load(f)
        
    entries = data.get("entries", [])
    
    candidates_map = {}
    
    for e in entries:
        start_t = parse_time(e.get("start"))
        end_t = parse_time(e.get("end"))
        type_ = e.get("type", "unknown")
        
        # Date filter is overlap-based, so filter client-side if we want events starting in window
        if start_t and (start_t < window_start or start_t > window_end):
            continue
            
        vessels = e.get("vessels", [])
        if not vessels:
            continue
            
        vessel = vessels[0]
        v_id = vessel.get("id", "unknown")
        mmsi = vessel.get("mmsi", v_id) # fallback to id if mmsi missing
        name = vessel.get("name", "Unknown Vessel")
        flag = vessel.get("flag", "UNK")
        
        if mmsi not in candidates_map:
            candidates_map[mmsi] = {
                "mmsi": mmsi,
                "name": name,
                "flag": flag,
                "positions": [], # In a real implementation, we'd fetch actual AIS tracks
                "gap_events": []
            }
            
        # Bound AIS-gap duration: reject gaps longer than MAX_GAP_HOURS
        if type_ == "gap":
            if start_t and end_t:
                duration_hours = (end_t - start_t).total_seconds() / 3600.0
                if duration_hours <= MAX_GAP_HOURS:
                    candidates_map[mmsi]["gap_events"].append({
                        "start": start_t.isoformat(),
                        "end": end_t.isoformat(),
                        "duration_hours": duration_hours
                    })
        elif type_ == "fishing":
            # Will be overridden by real tracks below if available
            if start_t:
                candidates_map[mmsi]["positions"].append({
                    "lat": e.get("lat", (origin_bbox[1]+origin_bbox[3])/2),
                    "lon": e.get("lon", (origin_bbox[0]+origin_bbox[2])/2),
                    "time": start_t.isoformat()
                })
                
    # B6: Load real ship tracks if available to replace synthetic/proxy paths
    tracks_path = "fixtures/vessel_tracks.json"
    if __import__("os").path.exists(tracks_path):
        with open(tracks_path, "r") as f:
            real_tracks = json.load(f)
            
        for c_mmsi, candidate in candidates_map.items():
            if c_mmsi in real_tracks:
                # Range check [lon, lat] before appending
                valid_positions = []
                for p in real_tracks[c_mmsi]:
                    lat, lon = p.get("lat"), p.get("lon")
                    if lat is not None and lon is not None:
                        if -90 <= lat <= 90 and -180 <= lon <= 180:
                            valid_positions.append(p)
                candidate["positions"] = valid_positions
                
    return list(candidates_map.values())

if __name__ == "__main__":
    with open("fixtures/drift_origin.json", "r") as f:
        origin_data = json.load(f)
        
    candidates = get_vessel_candidates(
        origin_data["origin_bbox"], 
        origin_data["time_window"]
    )
    
    print(f"Found {len(candidates)} candidates.")
    for c in candidates:
        print(f"- {c['name']} (MMSI: {c['mmsi']}): {len(c['gap_events'])} valid gaps")
