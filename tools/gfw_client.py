import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()
GFW_API_TOKEN = os.getenv("GFW_API_TOKEN")

HEADERS = {
    "Authorization": f"Bearer {GFW_API_TOKEN}",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"
}

def check_response(res):
    print(f"Status: {res.status_code}")
    if res.status_code != 200:
        print(f"Error Body: {res.text[:300]}")
    return res.status_code == 200

def test_4wings_report():
    print("\n--- Testing 4wings Report ---")
    url = "https://gateway.api.globalfishingwatch.org/v3/4wings/report"
    
    # 4wings requires all params in the URL query string
    params = {
        "datasets[0]": "public-global-fishing-effort:latest",
        "date-range": "2024-01-01,2024-12-31",
        "spatial-resolution": "HIGH",
        "temporal-resolution": "YEARLY",
        "group-by": "VESSEL_ID",
        "format": "JSON"
    }
    
    payload = {
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [
                    [68.0, 18.0],
                    [73.0, 18.0],
                    [73.0, 23.0],
                    [68.0, 23.0],
                    [68.0, 18.0]
                ]
            ]
        }
    }
    
    res = requests.post(url, headers=HEADERS, params=params, json=payload)
    if check_response(res):
        data = res.json()
        entries = data.get("entries", [])
        print(f"4wings returned {len(entries)} rows.")
        if entries:
            print("Sample row:", entries[0])

def test_events():
    print("\n--- Testing Events Filter ---")
    url = "https://gateway.api.globalfishingwatch.org/v3/events"
    
    params = {
        "datasets[0]": "public-global-fishing-events:latest",
        "start-date": "2024-01-01",
        "end-date": "2024-12-31",
        "vessels[0]": "440825000",
        "limit": 5,
        "offset": 0
    }
    
    res = requests.get(url, headers=HEADERS, params=params)
    if check_response(res):
        data = res.json()
        total = data.get("total", 0)
        entries = data.get("entries", [])
        print(f"Events returned {total} total. Sample of {len(entries)}:")
        for e in entries:
            start = e.get("start")
            end = e.get("end")
            type_ = e.get("type")
            vessel = e.get("vessels", [{}])[0].get("id", "unknown")
            print(f"- {type_} from {start} to {end} for vessel {vessel}")

if __name__ == "__main__":
    if not GFW_API_TOKEN:
        print("Error: GFW_API_TOKEN not found in .env")
    else:
        test_4wings_report()
        test_events()
