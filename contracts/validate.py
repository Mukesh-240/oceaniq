def validate_payload(doc):
    """
    Validates a scoring payload against the dashboard schema.
    Raises ValueError if validation fails.
    """
    if not isinstance(doc, list):
        raise ValueError("Payload must be a list of candidates")
        
    for suspect in doc:
        factors = suspect.get("factors", [])
        if len(factors) != 5:
            raise ValueError(f"Candidate {suspect.get('mmsi')} has {len(factors)} factors, expected 5")
            
        labels = [f.get("label") for f in factors]
        expected_labels = [
            "Proximity to origin", 
            "Timing overlap", 
            "Trajectory consistency", 
            "Drift agreement", 
            "AIS discrepancy"
        ]
        
        if labels != expected_labels:
            raise ValueError(f"Factor labels do not match expected order. Got {labels}")
            
        for f in factors:
            score = f.get("score")
            if score is None or not (0 <= score <= 100):
                raise ValueError(f"Score for {f.get('label')} must be between 0 and 100")
                
        # Range check geometries if present
        track = suspect.get("track", [])
        for point in track:
            lat = point.get("lat")
            lon = point.get("lon")
            if lat is not None and not (-90 <= lat <= 90):
                raise ValueError(f"Invalid latitude: {lat}")
            if lon is not None and not (-180 <= lon <= 180):
                raise ValueError(f"Invalid longitude: {lon}")
                
        time_window = suspect.get("time_window")
        if time_window:
            start = time_window.get("start")
            end = time_window.get("end")
            if start and end and start >= end:
                raise ValueError("time_window.start must be strictly less than end")
                
    return True
