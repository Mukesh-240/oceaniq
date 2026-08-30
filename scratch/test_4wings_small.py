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

def test_4wings_small():
    url = "https://gateway.api.globalfishingwatch.org/v3/4wings/report"
    
    params = {
        "datasets[0]": "public-global-fishing-effort:latest",
        "date-range": "2024-01-01,2024-01-02",
        "spatial-resolution": "HIGH",
        "temporal-resolution": "DAILY",
        "group-by": "VESSEL_ID",
        "format": "JSON"
    }
    
    # very small box in the arabian sea
    payload = {
        "region": {
            "geojson": {
                "type": "Polygon",
                "coordinates": [[
                    [69.0, 18.0],
                    [69.1, 18.0],
                    [69.1, 18.1],
                    [69.0, 18.1],
                    [69.0, 18.0]
                ]]
            }
        }
    }
    
    print("Sending 4wings request...")
    res = requests.post(url, headers=HEADERS, params=params, json=payload)
    print("Status:", res.status_code)
    if res.status_code == 200:
        print("Success! rows:", len(res.json().get('entries', [])))
    else:
        print("Failed:", res.text[:300])

if __name__ == "__main__":
    test_4wings_small()
