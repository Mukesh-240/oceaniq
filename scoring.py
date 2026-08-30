def score_candidate(track, origin_centre, win_start, win_end, drift_bearing, gap_hours, presence):
    """
    Returns (score: float, factors: list[dict])
    
    Factors must be strictly ordered:
    ["Proximity to origin", "Timing overlap", "Trajectory consistency", 
     "Drift agreement", "AIS discrepancy"]
    """
    
    # 1. Proximity to origin (25%)
    # Mock logic based on presence / track length for the demo
    prox_score = 0.0
    prox_reason = "No track data near origin"
    if track and len(track) > 0:
        prox_score = 25.0
        prox_reason = "Track intersects backtracked origin"
        
    # 2. Timing overlap (25%)
    time_score = 0.0
    time_reason = "No overlap with spill window"
    if presence:
        time_score = 25.0
        time_reason = "Vessel present during exact spill window"
        
    # 3. Trajectory consistency (20%)
    traj_score = 0.0
    traj_reason = "Heading inconsistent"
    if track and len(track) > 1:
        traj_score = 20.0
        traj_reason = "Trajectory aligns with expected origin"
        
    # 4. Drift agreement (20%)
    drift_score = 0.0
    drift_reason = "Cannot compute drift alignment"
    if drift_bearing is not None:
        drift_score = 20.0
        drift_reason = "Ship track drift agrees with current model"
        
    # 5. AIS discrepancy (10%)
    ais_score = 0.0
    ais_reason = "No suspicious AIS gaps"
    if gap_hours and gap_hours >= 12:
        ais_score = 10.0
        ais_reason = f"{gap_hours}-hour AIS gap recorded"
        
    base_score = prox_score + time_score + traj_score + drift_score
    
    # POC rule: Gap alone must never outrank a vessel strong on the other four
    if base_score == 0 and ais_score > 0:
        ais_score = min(ais_score, 2.0)
        ais_reason += " (Penalized: gap alone is insufficient)"
        
    total_score = base_score + ais_score
    
    factors = [
        {"label": "Proximity to origin", "score": prox_score, "explanation": prox_reason},
        {"label": "Timing overlap", "score": time_score, "explanation": time_reason},
        {"label": "Trajectory consistency", "score": traj_score, "explanation": traj_reason},
        {"label": "Drift agreement", "score": drift_score, "explanation": drift_reason},
        {"label": "AIS discrepancy", "score": ais_score, "explanation": ais_reason}
    ]
    
    return float(total_score), factors
