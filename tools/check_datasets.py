import os
import requests
import json
from dotenv import load_dotenv

def check_datasets():
    load_dotenv()
    token = os.getenv("GFW_API_TOKEN")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    url = "https://gateway.api.globalfishingwatch.org/v3/datasets"
    params = {
        "limit": 5,
        "offset": 0
    }
    
    print(f"Querying {url}")
    
    try:
        res = requests.get(url, headers=headers, params=params)
        print(f"Status: {res.status_code}")
        
        if res.status_code == 200:
            data = res.json()
            print(json.dumps(data, indent=2))
        else:
            print(res.text)
            
    except Exception as e:
        print(e)

if __name__ == "__main__":
    check_datasets()
