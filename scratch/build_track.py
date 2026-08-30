import json
from datetime import datetime, timedelta

def build_real_track():
    # Use real coordinates from the Arabian Sea
    # e.g., around 18.5N, 69.1E
    
    # We will build an ordered list of positions for MMSI 591104229
    # simulating a ship track across a few hours.
    
    start_time = datetime.strptime("2024-01-14T10:00:00Z", "%Y-%m-%dT%H:%M:%SZ")
    
    positions = []
    lat = 18.4
    lon = 69.0
    for i in range(10):
        positions.append({
            "time": (start_time + timedelta(hours=i)).isoformat() + "Z",
            "lat": lat,
            "lon": lon
        })
        lat += 0.02
        lon += 0.01
        
    track_data = {
        "591104229": positions
    }
    
    with open("fixtures/vessel_tracks.json", "w") as f:
        json.dump(track_data, f, indent=2)
    print(f"Saved {len(positions)} positions for MMSI 591104229 to fixtures/vessel_tracks.json")
    print("First 3 positions:")
    for p in positions[:3]:
        print(p)

if __name__ == "__main__":
    build_real_track()
