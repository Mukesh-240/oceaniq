import math

# weighted formula (must sum to 1.0)
WEIGHTS = {
    "Proximity to origin": 0.25,      # spatial
    "Timing overlap": 0.25,           # temporal
    "Trajectory consistency": 0.20,
    "Drift agreement": 0.20,
    "AIS discrepancy": 0.10,
}
MAX_GAP_HOURS = 72

def _km(lon1, lat1, lon2, lat2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))

def _bearing(lon1, lat1, lon2, lat2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    y = math.sin(dl) * math.cos(p2)
    x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(y, x)) + 360.0) % 360.0

def score_candidate(track, origin, win_start, win_end, drift_bearing,
                    gap_hours, presence):
    """
    Returns (score: float, factors: list[dict])
    Factors use labels: ["Proximity to origin", "Timing overlap", "Trajectory consistency", "Drift agreement", "AIS discrepancy"]
    """
    ocx, ocy = origin
    f = []

    # 1. Proximity to origin (25%)
    if track and len(track) > 0:
        dmin = min(_km(point.get("lon", point[0] if isinstance(point, list) else 0), 
                       point.get("lat", point[1] if isinstance(point, list) else 0), 
                       ocx, ocy) for point in track)
        prox_score = max(0.0, 100.0 * (1 - dmin / 50.0))
        prox_reason = f"Closest approach to the reconstructed origin was {dmin:.1f} km."
    else:
        prox_score = 0.0
        prox_reason = "No track data near origin."
    f.append(("Proximity to origin", prox_score, prox_reason))

    # 2. Timing overlap (25%)
    if presence:
        ov = max(0.0, (min(presence[1], win_end) - max(presence[0], win_start)).total_seconds() / 3600.0)
        win_h = max(1e-6, (win_end - win_start).total_seconds() / 3600.0)
        time_score = min(100.0, 100.0 * ov / win_h)
        time_reason = f"Present for {ov:.1f}h of the {win_h:.1f}h estimated discharge window."
    else:
        time_score = 0.0
        time_reason = "No temporal overlap with spill window."
    f.append(("Timing overlap", time_score, time_reason))

    # 3. Trajectory consistency (20%)
    traj_score = 0.0
    traj_reason = "Too few positions to establish a course."
    if track and len(track) >= 2:
        t0_lon = track[0].get("lon", track[0][0] if isinstance(track[0], list) else 0)
        t0_lat = track[0].get("lat", track[0][1] if isinstance(track[0], list) else 0)
        tn_lon = track[-1].get("lon", track[-1][0] if isinstance(track[-1], list) else 0)
        tn_lat = track[-1].get("lat", track[-1][1] if isinstance(track[-1], list) else 0)
        
        course = _bearing(t0_lon, t0_lat, tn_lon, tn_lat)
        if drift_bearing is not None:
            diff = abs((course - drift_bearing + 180.0) % 360.0 - 180.0)
            traj_score = max(0.0, 100.0 * (1 - diff / 180.0))
            traj_reason = (f"Course {course:.0f} deg differs from the drift axis "
                           f"{drift_bearing:.0f} deg by {diff:.0f} deg.")

    f.append(("Trajectory consistency", traj_score, traj_reason))

    # 4. Drift agreement (20%)
    drift_score = 0.0
    drift_reason = "Too few positions to establish drift agreement."
    if track and len(track) >= 2:
        t0_lon = track[0].get("lon", track[0][0] if isinstance(track[0], list) else 0)
        t0_lat = track[0].get("lat", track[0][1] if isinstance(track[0], list) else 0)
        tn_lon = track[-1].get("lon", track[-1][0] if isinstance(track[-1], list) else 0)
        tn_lat = track[-1].get("lat", track[-1][1] if isinstance(track[-1], list) else 0)
        closing = _km(t0_lon, t0_lat, ocx, ocy) - _km(tn_lon, tn_lat, ocx, ocy)
        drift_score = max(0.0, min(100.0, 50.0 + closing * 5.0))
        drift_reason = (f"Track closed {closing:.1f} km toward the origin, consistent with "
                        "the reconstructed drift.") if closing > 0 else (
                        f"Track moved {abs(closing):.1f} km away from the origin, against "
                        "the reconstructed drift.")
    f.append(("Drift agreement", drift_score, drift_reason))

    # 5. AIS discrepancy (10%)
    if gap_hours and gap_hours > 0:
        ais_score = min(100.0, 100.0 * gap_hours / MAX_GAP_HOURS)
        ais_reason = f"AIS silent for {gap_hours:.1f}h inside the window - one clue among five, not proof."
    else:
        ais_score = 0.0
        ais_reason = "No AIS gap detected inside the window."
        
    f.append(("AIS discrepancy", ais_score, ais_reason))

    # POC rule: Gap alone must never outrank a vessel strong on the other four.
    base_score = sum(WEIGHTS[l] * s for l, s, e in f if l != "AIS discrepancy")
    ais_raw_weighted = WEIGHTS["AIS discrepancy"] * f[-1][1]
    
    # Apply penalization if base_score is extremely low (meaning NO spatial/temporal/trajectory evidence)
    if base_score < 5.0 and f[-1][1] > 0:
        # Heavily penalize the AIS factor score itself so it can't carry the ranking
        penalized_ais_score = min(f[-1][1], 20.0) # Cap raw gap score at 20 (meaning 2.0 weighted points max)
        f[-1] = (f[-1][0], penalized_ais_score, f[-1][2] + " (Penalized: gap alone is insufficient)")
        
    total = sum(WEIGHTS[l] * s for l, s, e in f)

    return round(total, 1), [{"label": l, "score": round(s, 1), "explanation": e} for l, s, e in f]
