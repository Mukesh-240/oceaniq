import json

def extract_real_tracks():
    # Load the real GFW events payload generated in B1
    try:
        with open("fixtures/gfw_vessels.json", "r") as f:
            events_data = json.load(f)
    except FileNotFoundError:
        print("fixtures/gfw_vessels.json not found.")
        return

    tracks = {}
    entries = events_data.get("entries", [])
    
    for e in entries:
        # Extract vessel MMSI
        vessel = e.get("vessel", {})
        mmsi = vessel.get("ssvid") or vessel.get("id")
        if not mmsi:
            continue
            
        if mmsi not in tracks:
            tracks[mmsi] = []
            
        time_str = e.get("start")
        if not time_str:
            continue
            
        lat, lon = None, None
        if "position" in e:
            lat = e["position"].get("lat")
            lon = e["position"].get("lon")
        elif "boundingBox" in e:
            bbox = e["boundingBox"]
            lat = (bbox[1] + bbox[3]) / 2.0
            lon = (bbox[0] + bbox[2]) / 2.0
            
        if lat is not None and lon is not None:
            # Range check [lon, lat]
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                tracks[mmsi].append({
                    "time": time_str,
                    "lat": lat,
                    "lon": lon,
                    "type": e.get("type", "unknown")
                })
                
    # Sort positions by time
    for mmsi, positions in list(tracks.items()):
        if not positions:
            del tracks[mmsi]
        else:
            positions.sort(key=lambda x: x["time"])
            
    # Save the extracted tracks
    if tracks:
        with open("fixtures/vessel_tracks.json", "w") as f:
            json.dump(tracks, f, indent=2)
            
        print(f"Extracted {sum(len(p) for p in tracks.values())} real positions across {len(tracks)} vessels.")
        mmsi_sample = list(tracks.keys())[0]
        print(f"First 3 positions for {mmsi_sample}:")
        for p in tracks[mmsi_sample][:3]:
            print(p)
    else:
        print("No valid positions extracted from real events.")

if __name__ == "__main__":
    extract_real_tracks()
