import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()
GFW_API_TOKEN = os.getenv("GFW_API_TOKEN")
HEADERS = {
    "Authorization": f"Bearer {GFW_API_TOKEN}",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

def test_tracks():
    # Attempting to get track for MMSI 591104229
    url = "https://gateway.api.globalfishingwatch.org/v3/vessels/search"
    params = {
        "query": "mmsi:591104229",
        "datasets[0]": "public-global-vessel-identity:latest",
    }
    res = requests.get(url, headers=HEADERS, params=params)
    if res.status_code == 200:
        data = res.json()
        entries = data.get("entries", [])
        if entries:
            vid = entries[0]["id"]
            print(f"Found vessel id {vid}")
            
            # Now let's try getting tracks
            track_url = f"https://gateway.api.globalfishingwatch.org/v3/vessels/{vid}/tracks"
            track_params = {
                "datasets[0]": "public-global-vessel-tracks:latest",
                "start-date": "2024-01-01T00:00:00Z",
                "end-date": "2024-01-31T00:00:00Z"
            }
            tres = requests.get(track_url, headers=HEADERS, params=track_params)
            print("Tracks status:", tres.status_code)
            if tres.status_code == 200:
                print("Tracks successfully retrieved!")
                # print a snippet
                print(str(tres.json())[:300])
            else:
                print(tres.text)
        else:
            print("No vessel found.")
    else:
        print("Search status:", res.status_code, res.text)

if __name__ == "__main__":
    test_tracks()
