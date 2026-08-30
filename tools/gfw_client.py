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

def test_events():
    url = "https://gateway.api.globalfishingwatch.org/v3/events"
    
    params = {
        "datasets[0]": "public-global-fishing-events:latest",
        "start-date": "2024-01-01",
        "end-date": "2024-12-31",
        "limit": 5,
        "offset": 0
    }
    
    res = requests.get(url, headers=HEADERS, params=params)
    if res.status_code == 200:
        data = res.json()
        if not os.path.exists("fixtures"):
            os.makedirs("fixtures")
        with open("fixtures/gfw_vessels.json", "w") as f:
            json.dump(data, f, indent=2)
        print("Saved Events to fixtures/gfw_vessels.json")
    else:
        print("Error", res.text)

if __name__ == "__main__":
    test_events()
