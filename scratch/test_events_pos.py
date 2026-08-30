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

def fetch_events_for_vessel(vid, mmsi):
    url = "https://gateway.api.globalfishingwatch.org/v3/events"
    params = {
        "datasets[0]": "public-global-fishing-events:latest",
        "datasets[1]": "public-global-port-visits:latest",
        "datasets[2]": "public-global-encounters:latest",
        "datasets[3]": "public-global-loitering-events:latest",
        "vessels": vid,
        "start-date": "2023-01-01T00:00:00Z",
        "end-date": "2024-12-31T23:59:59Z",
        "limit": 500,
        "offset": 0
    }
    
    res = requests.get(url, headers=HEADERS, params=params)
    if res.status_code == 200:
        data = res.json()
        entries = data.get("entries", [])
        print(f"Got {len(entries)} events for {vid}")
        
        positions = []
        for e in entries:
            if "position" in e:
                positions.append({
                    "time": e["start"],
                    "lat": e["position"]["lat"],
                    "lon": e["position"]["lon"],
                    "type": e["type"]
                })
            elif "boundingBox" in e:
                bbox = e["boundingBox"]
                positions.append({
                    "time": e["start"],
                    "lat": (bbox[1] + bbox[3]) / 2.0,
                    "lon": (bbox[0] + bbox[2]) / 2.0,
                    "type": e["type"]
                })
                
        positions.sort(key=lambda x: x["time"])
        if positions:
            with open("fixtures/vessel_tracks.json", "w") as f:
                json.dump({mmsi: positions}, f, indent=2)
            print(f"Saved {len(positions)} positions to fixtures/vessel_tracks.json")
            for p in positions[:3]:
                print(p)
    else:
        print("Failed:", res.status_code, res.text)

if __name__ == "__main__":
    fetch_events_for_vessel("2934e7640-0d19-ad59-bcff-9dedb141149d", "242065100")
