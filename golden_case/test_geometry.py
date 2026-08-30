"""Self-checks for the golden-case geometry and scoring helpers.

    python golden_case/test_geometry.py

Lives in golden_case/ rather than tests/ because tests/ is Agent B's lane.
Plain asserts, no pytest dependency, so it runs anywhere.
"""

import copy
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_golden_case import (  # noqa: E402
    WEIGHTS, _douglas_peucker, assert_lonlat, hull_polygon, mask_to_polygon,
    score_candidate, transpose_geometry, validate,
)


def t1_lonlat_accepts_valid():
    g = {"type": "Polygon", "coordinates": [[[69.1, 18.5], [69.2, 18.5],
                                             [69.2, 18.6], [69.1, 18.5]]]}
    assert_lonlat(g, "t1")
    print("1. valid [lon,lat] polygon accepted                     OK")


def t2_lonlat_catches_swap():
    # Honest limitation: for a scene at 59.8N 4.7E both values are <90, so a
    # swap is numerically legal and NO range check can catch it. Only the class
    # where the swap pushes slot 2 past 90 is detectable. Test that class.
    g = {"type": "Polygon", "coordinates": [[[18.5, 169.1], [18.6, 169.2],
                                             [18.6, 169.3], [18.5, 169.1]]]}
    try:
        assert_lonlat(g, "t2")
    except ValueError:
        print("2. swapped [lat,lon] rejected (detectable class)        OK")
        return
    raise AssertionError("swap was NOT detected")


def t3_lonlat_rejects_out_of_range():
    cases = {
        "lon>180": [[[200.0, 18.5], [201.0, 18.5], [200.0, 18.6], [200.0, 18.5]]],
        "lat>90": [[[69.1, 95.0], [69.2, 95.0], [69.2, 96.0], [69.1, 95.0]]],
    }
    for why, coords in cases.items():
        try:
            assert_lonlat({"type": "Polygon", "coordinates": coords}, "t3")
        except ValueError:
            continue
        raise AssertionError(f"{why} was not rejected")
    print("3. out-of-range lon/lat rejected                        OK")


def t4_douglas_peucker_reduces():
    t = np.linspace(0, 2 * np.pi, 400)
    circle = np.column_stack([np.cos(t), np.sin(t)])
    out = _douglas_peucker(circle, 0.05)
    assert len(out) < len(circle), "DP did not reduce vertices"
    assert len(out) >= 4, f"DP over-simplified to {len(out)}"
    print(f"4. Douglas-Peucker 400 -> {len(out)} vertices               OK")


def t5_hull_closes_ring():
    g = hull_polygon([0.0, 1.0, 1.0, 0.0, 0.5], [0.0, 0.0, 1.0, 1.0, 0.5])
    ring = g["coordinates"][0]
    assert ring[0] == ring[-1], "hull ring is not closed"
    assert len(ring) >= 4, ring
    print(f"5. convex hull closed, {len(ring)} vertices                   OK")


def t6_mask_polygon_from_real_shape():
    mask = np.zeros((256, 256), np.uint8)
    ys, xs = np.ogrid[:256, :256]
    mask[((ys - 128) / 30.0) ** 2 + ((xs - 128) / 60.0) ** 2 <= 1] = 255
    g = mask_to_polygon(mask, lambda x, y: (69.0 + x * 1e-4, 18.5 - y * 1e-4))
    assert_lonlat(g, "t6")
    ring = g["coordinates"][0]
    assert ring[0] == ring[-1], "polygon ring not closed"
    assert len(ring) >= 5, f"only {len(ring)} vertices for an ellipse"
    print(f"6. mask -> polygon, {len(ring)} vertices, lon/lat valid        OK")


def t7_transpose_preserves_shape():
    g = {"type": "Polygon", "coordinates": [[[4.70, 59.74], [4.75, 59.74],
                                             [4.75, 59.81], [4.70, 59.74]]]}
    moved = transpose_geometry(g, 64.4, -41.22)
    a, b = g["coordinates"][0], moved["coordinates"][0]
    w0 = max(p[0] for p in a) - min(p[0] for p in a)
    w1 = max(p[0] for p in b) - min(p[0] for p in b)
    h0 = max(p[1] for p in a) - min(p[1] for p in a)
    h1 = max(p[1] for p in b) - min(p[1] for p in b)
    assert abs(w0 - w1) < 1e-9 and abs(h0 - h1) < 1e-9, "transpose changed size"
    assert g["coordinates"][0][0][0] == 4.70, "original was mutated"
    assert_lonlat(moved, "t7")
    print(f"7. transpose preserves size ({w1:.3f} x {h1:.3f} deg)        OK")


def t8_gap_only_cannot_win():
    """POC requirement: an AIS gap alone must never top the ranking."""
    t0 = datetime(2024, 6, 15, 0, 0, tzinfo=timezone.utc)
    t1 = t0 + timedelta(hours=24)
    origin = (69.10, 18.52)
    far = [[70.5, 19.9], [70.6, 20.0]]          # distant, wrong course, no overlap
    near = [[69.08, 18.50], [69.10, 18.52]]     # closing on the origin, full overlap

    gap_only, _ = score_candidate(far, origin, t0, t1, 45.0,
                                  gap_hours=72.0, presence=(t1, t1))
    strong, _ = score_candidate(near, origin, t0, t1, 45.0,
                                gap_hours=0.0, presence=(t0, t1))
    assert strong > gap_only, f"gap-only {gap_only} outranked strong {strong}"
    print(f"8. gap-only {gap_only} loses to evidence-rich {strong}        OK")


def t9_validate_rejects_bad_payloads():
    good_track = {"type": "LineString", "coordinates": [[69.1, 18.5], [69.2, 18.6]]}
    base = {
        "satellite_image_url": "x.png",
        "spill_mask": {"type": "Polygon", "coordinates":
                       [[[69.1, 18.5], [69.2, 18.5], [69.2, 18.6], [69.1, 18.5]]]},
        "origin_region": {"polygon": {"type": "Polygon", "coordinates":
                          [[[69.0, 18.4], [69.3, 18.4], [69.3, 18.7], [69.0, 18.4]]]},
                          "time_window": {"start": "2024-06-15T00:00:00Z",
                                          "end": "2024-06-15T12:00:00Z"}},
        "candidate_ships": [{"id": "1", "name": "A", "track": good_track, "score": 50,
                             "factors": [{"label": l, "score": 50, "explanation": "x"}
                                         for l in WEIGHTS]}],
    }
    validate(base)                                    # the good one must pass

    bad = {}
    b = copy.deepcopy(base); b["candidate_ships"][0]["factors"].pop()
    bad["4 factors"] = b
    b = copy.deepcopy(base); b["candidate_ships"][0]["score"] = 120
    bad["score 120"] = b
    b = copy.deepcopy(base)
    b["origin_region"]["time_window"] = {"start": "2024-06-15T12:00:00Z",
                                         "end": "2024-06-15T00:00:00Z"}
    bad["reversed window"] = b
    b = copy.deepcopy(base)
    b["spill_mask"]["coordinates"] = [[[18.5, 169.1], [18.6, 169.2],
                                       [18.6, 169.3], [18.5, 169.1]]]
    bad["swapped lat/lon"] = b
    b = copy.deepcopy(base); del b["candidate_ships"][0]["name"]
    bad["missing name"] = b

    for label, doc in bad.items():
        try:
            validate(doc)
        except (ValueError, KeyError):
            continue
        raise AssertionError(f"validator ACCEPTED a bad payload: {label}")
    print(f"9. validator rejected all {len(bad)} bad payloads             OK")


if __name__ == "__main__":
    for fn in (t1_lonlat_accepts_valid, t2_lonlat_catches_swap,
               t3_lonlat_rejects_out_of_range, t4_douglas_peucker_reduces,
               t5_hull_closes_ring, t6_mask_polygon_from_real_shape,
               t7_transpose_preserves_shape, t8_gap_only_cannot_win,
               t9_validate_rejects_bad_payloads):
        fn()
    print("\nALL GEOMETRY / SCORING CHECKS PASSED")
