import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()
GFW_API_TOKEN = os.getenv("GFW_API_TOKEN")

HEADERS = {
    "Authorization": f"Bearer {GFW_API_TOKEN}",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0"
}

def get_track_for_mmsi(mmsi_str):
    print(f"Searching for MMSI: {mmsi_str}")
    url = "https://gateway.api.globalfishingwatch.org/v3/vessels/search"
    res = requests.get(url, headers=HEADERS, params={
        "query": f"mmsi:{mmsi_str}",
        "datasets[0]": "public-global-vessel-identity:latest"
    })
    
    if res.status_code != 200:
        print("Search failed:", res.status_code, res.text)
        return
        
    data = res.json()
    entries = data.get("entries", [])
    if not entries:
        print("No vessel found.")
        return
        
    # extract id from selfReportedInfo
    vid = None
    for e in entries:
        sr = e.get("selfReportedInfo", [])
        if sr:
            vid = sr[0].get("id")
            break
            
    if not vid:
        print("No valid internal ID found.")
        return
        
    print(f"Found internal ID: {vid}")
    
    # fetch events
    url_events = "https://gateway.api.globalfishingwatch.org/v3/events"
    params = {
        "datasets[0]": "public-global-fishing-events:latest",
        "datasets[1]": "public-global-port-visits:latest",
        "datasets[2]": "public-global-encounters:latest",
        "datasets[3]": "public-global-loitering-events:latest",
        "vessels[0]": vid,
        "start-date": "2020-01-01T00:00:00Z",
        "end-date": "2024-12-31T23:59:59Z",
        "limit": 500,
        "offset": 0
    }
    
    res_events = requests.get(url_events, headers=HEADERS, params=params)
    if res_events.status_code != 200:
        print("Events fetch failed:", res_events.status_code, res_events.text)
        return
        
    ev_data = res_events.json()
    events = ev_data.get("entries", [])
    print(f"Got {len(events)} events.")
    
    positions = []
    for e in events:
        if "position" in e:
            lat = e["position"]["lat"]
            lon = e["position"]["lon"]
            # basic range check
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                positions.append({
                    "time": e["start"],
                    "lat": lat,
                    "lon": lon,
                    "type": e.get("type", "unknown")
                })
        elif "boundingBox" in e and e.get("type") == "fishing":
            # For fishing events, we can use the center of the bounding box
            bbox = e["boundingBox"] # [minLon, minLat, maxLon, maxLat]
            lat = (bbox[1] + bbox[3]) / 2.0
            lon = (bbox[0] + bbox[2]) / 2.0
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                positions.append({
                    "time": e["start"],
                    "lat": lat,
                    "lon": lon,
                    "type": "fishing"
                })
                
    positions.sort(key=lambda x: x["time"])
    
    print(f"Extracted {len(positions)} valid positions.")
    if positions:
        print("First 3 positions:")
        for p in positions[:3]:
            print(p)
            
        tracks = {
            mmsi_str: positions
        }
        with open("fixtures/vessel_tracks.json", "w") as f:
            json.dump(tracks, f, indent=2)
        print("Saved to fixtures/vessel_tracks.json")
    else:
        print("No valid positions extracted.")

if __name__ == "__main__":
    get_track_for_mmsi("591104229")
