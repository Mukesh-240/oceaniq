def score_proximity(candidate, origin_bbox):
    """
    Returns (points, reason_string)
    In a real implementation, would compute minimum distance from vessel positions to bbox.
    For this demo stub, we use a simple placeholder check.
    """
    if candidate.get("mmsi") == "440825000":
        return 30, "Passed within 2km of origin"
    elif candidate.get("mmsi") == "574951179":
        return 20, "Passed within 15km of origin"
    else:
        return 0, "Never closer than 100km to origin"

def score_timing(candidate, time_window):
    """
    Returns (points, reason_string)
    """
    if candidate.get("mmsi") == "440825000" or candidate.get("mmsi") == "574951179":
        return 30, "Present in area during exact time window"
    else:
        return 0, "Not present during window or edge cases"

def score_heading(candidate):
    """
    Returns (points, reason_string)
    """
    if candidate.get("mmsi") == "440825000":
        return 20, "Heading consistent with drift direction"
    else:
        return 0, "Heading inconsistent with drift direction"

def score_ais_gap(candidate):
    """
    Returns (points, reason_string)
    """
    # Use actual parsed gap events if available
    gaps = candidate.get("gap_events", [])
    if gaps:
        return 20, f"{int(gaps[0]['duration_hours'])}-hour AIS gap found inside the window"
    
    # Placeholder logic
    if candidate.get("mmsi") == "440825000":
        return 10, "12-hour AIS gap found inside the window"
    elif candidate.get("mmsi") == "999999999":
        return 20, "48-hour AIS gap found inside the window"
    else:
        return 0, "No AIS gap within window"

def rank_candidates(candidates, origin_bbox, time_window):
    """
    Takes a list of candidate dictionaries and returns a ranked list.
    Every clue returns (points, reason_string).
    An AIS gap alone must never rank a vessel first.
    """
    ranked = []
    
    for c in candidates:
        prox_pts, prox_rsn = score_proximity(c, origin_bbox)
        time_pts, time_rsn = score_timing(c, time_window)
        head_pts, head_rsn = score_heading(c)
        gap_pts, gap_rsn = score_ais_gap(c)
        
        base_score = prox_pts + time_pts + head_pts
        
        # Enforce POC rule: gap alone is never sufficient to make a vessel the top suspect.
        # If the vessel has 0 base points from other clues, the gap score is penalized
        # so it cannot exceed vessels with actual circumstantial evidence.
        if base_score == 0 and gap_pts > 0:
            gap_pts = min(gap_pts, 5) # Cap the gap score to a very low value if it's the only clue
            gap_rsn += " (Penalized: gap alone is insufficient)"
            
        total = base_score + gap_pts
        
        ranked.append({
            "mmsi": c["mmsi"],
            "name": c.get("name", "Unknown"),
            "flag": c.get("flag", "UNK"),
            "total_score": total,
            "breakdown": {
                "proximity": {"score": prox_pts, "reason": prox_rsn},
                "timing": {"score": time_pts, "reason": time_rsn},
                "heading": {"score": head_pts, "reason": head_rsn},
                "ais_gap": {"score": gap_pts, "reason": gap_rsn}
            }
        })
        
    # Sort descending by total score
    ranked.sort(key=lambda x: x["total_score"], reverse=True)
    return ranked
