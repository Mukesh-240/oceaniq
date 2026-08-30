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

def fetch_events_for_mmsi(mmsi):
    url = "https://gateway.api.globalfishingwatch.org/v3/events"
    # Find events for this MMSI in 2024
    params = {
        "datasets[0]": "public-global-fishing-events:latest",
        "datasets[1]": "public-global-port-visits:latest",
        "datasets[2]": "public-global-encounters:latest",
        "datasets[3]": "public-global-loitering-events:latest",
        "vessels[0]": f"mmsi:{mmsi}",
        "start-date": "2024-01-01T00:00:00Z",
        "end-date": "2024-01-31T23:59:59Z",
        "limit": 50,
        "offset": 0
    }
    
    res = requests.get(url, headers=HEADERS, params=params)
    if res.status_code == 200:
        data = res.json()
        entries = data.get("entries", [])
        print(f"Got {len(entries)} events for MMSI {mmsi}")
        
        positions = []
        for e in entries:
            # gap/loitering/port have 'position', fishing has 'position' sometimes or 'boundingBox'
            if "position" in e:
                positions.append({
                    "time": e["start"],
                    "lat": e["position"]["lat"],
                    "lon": e["position"]["lon"],
                    "type": e["type"]
                })
        positions.sort(key=lambda x: x["time"])
        if positions:
            print("First 3 positions:")
            for p in positions[:3]:
                print(p)
    else:
        print("Failed:", res.status_code, res.text)

if __name__ == "__main__":
    # Wait, what was the MMSI in the example? PINGTAIRONG88-3 is just a name.
    # The instructions: "a real MMSI (e.g. 591104229, PINGTAIRONG88-3)"
    fetch_events_for_mmsi("591104229")
