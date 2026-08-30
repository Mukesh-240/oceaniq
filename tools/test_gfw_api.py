import os
import requests
import json
from dotenv import load_dotenv

def test_gfw_api():
    load_dotenv()
    token = os.getenv("GFW_API_TOKEN")
    
    if not token:
        print("Error: GFW_API_TOKEN not found in .env")
        return

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # First, let's list datasets to find the correct one
    datasets_url = "https://gateway.api.globalfishingwatch.org/v3/datasets"
    print("Fetching datasets...")
    try:
        ds_response = requests.get(datasets_url, headers=headers)
        if ds_response.status_code == 200:
            datasets = ds_response.json()
            # Find a vessel identity dataset
            vessel_datasets = [d['id'] for d in datasets if 'vessel' in d['id'].lower() and 'identity' in d['id'].lower()]
            print(f"Found vessel identity datasets: {vessel_datasets}")
            
            if not vessel_datasets:
                dataset_id = "public-global-vessel-identity:latest"
            else:
                dataset_id = vessel_datasets[0]
        else:
            print("Could not fetch datasets.")
            dataset_id = "public-global-vessel-identity:latest"
    except Exception as e:
        print(e)
        dataset_id = "public-global-vessel-identity:latest"

    # Now query vessels
    url = "https://gateway.api.globalfishingwatch.org/v3/vessels/search"
    params = {
        "query": "shipname:OCEANA",
        "datasets": dataset_id,
        "limit": 1,
        "offset": 0
    }

    print(f"\nQuerying GFW API: {url}")
    print(f"Params: {params}")
    
    try:
        response = requests.get(url, headers=headers, params=params)
        print(f"\nStatus Code: {response.status_code}")
        
        if response.status_code == 200:
            print("Success! Token is valid. Here is a sample payload:")
            data = response.json()
            print(json.dumps(data, indent=2))
        else:
            print("Failed.")
            print(response.text)
            
    except Exception as e:
        print(f"Error making request: {e}")

if __name__ == "__main__":
    test_gfw_api()
