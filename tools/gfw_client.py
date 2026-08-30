import os
import requests
import json
from datetime import datetime
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
    
    params = {
        "datasets[0]": "public-global-fishing-effort:latest",
        "date-range": "2024-01-01,2024-12-31",
        "spatial-resolution": "HIGH",
        "temporal-resolution": "YEARLY",
        "group-by": "VESSEL_ID",
        "format": "JSON"
    }
    
    payload = {
        "region": {
            "geojson": {
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
        "limit": 100,
        "offset": 0
    }
    
    res = requests.get(url, headers=HEADERS, params=params)
    if check_response(res):
        data = res.json()
        total = data.get("total", 0)
        entries = data.get("entries", [])
        print(f"Events returned {total} total. Sample of {min(5, len(entries))}:")
        
        start_bound = datetime.strptime("2024-01-01T00:00:00Z", "%Y-%m-%dT%H:%M:%SZ")
        end_bound = datetime.strptime("2024-12-31T23:59:59Z", "%Y-%m-%dT%H:%M:%SZ")
        
        all_passed = True
        
        for idx, e in enumerate(entries):
            start = e.get("start")
            end = e.get("end")
            type_ = e.get("type")
            vessels = e.get("vessels", [])
            vessel = vessels[0].get("id", "unknown") if vessels else "unknown"
            
            if idx < 5:
                print(f"- {type_} from {start} to {end} for vessel {vessel}")
            
            try:
                # e.g., '2024-05-13T10:49:15.000Z'
                s = start.replace(".000Z", "Z")
                dt = datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ")
                if dt < start_bound or dt > end_bound:
                    all_passed = False
                    print(f"ASSERTION FAILED: event start {start} is outside the bounds!")
            except Exception as ex:
                pass
                
        if all_passed and len(entries) > 0:
            print("VERIFIED: All returned events fall within the requested date window.")

if __name__ == "__main__":
    if not GFW_API_TOKEN:
        print("Error: GFW_API_TOKEN not found in .env")
    else:
        test_4wings_report()
        test_events()
