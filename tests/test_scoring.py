import unittest
from datetime import datetime
from scoring import score_candidate

class TestScoring(unittest.TestCase):
    def test_gap_alone_cannot_win(self):
        # Adversarial Case: far from origin, wrong course, zero temporal overlap, 72h gap
        # Origin at 0, 0
        track_adversarial = [{"lon": 10.0, "lat": 10.0}, {"lon": 11.0, "lat": 11.0}]
        # Moving AWAY from origin: distance increases. Course is roughly 45 deg. Drift bearing is 225 deg (opposite)
        win_start = datetime(2024, 1, 1, 12, 0)
        win_end = datetime(2024, 1, 1, 18, 0)
        
        # Zero temporal overlap
        presence_adv = (datetime(2023, 1, 1, 0, 0), datetime(2023, 1, 1, 6, 0))
        
        score_adv, factors_adv = score_candidate(
            track=track_adversarial,
            origin=(0, 0),
            win_start=win_start,
            win_end=win_end,
            drift_bearing=225.0, # opposite to track course
            gap_hours=72,
            presence=presence_adv
        )
        
        # Evidence-rich candidate: starts far, moves exactly to origin, exact course, exact time, no gap
        track_good = [{"lon": -1.0, "lat": -1.0}, {"lon": 0.0, "lat": 0.0}] # Course 45 deg, closes to origin
        score_good, factors_good = score_candidate(
            track=track_good,
            origin=(0, 0),
            win_start=win_start,
            win_end=win_end,
            drift_bearing=45.0,
            gap_hours=0,
            presence=(win_start, win_end)
        )
        
        # The good candidate should score very high
        self.assertGreater(score_good, 80.0)
        
        # The adversarial candidate should score very low (loses heavily)
        self.assertLess(score_adv, score_good)
        self.assertLessEqual(score_adv, 5.0)
        
        # Ensure the penalty was applied to the explanation
        self.assertIn("Penalized", factors_adv[4]["explanation"])
        
    def test_factor_labels_exact(self):
        _, factors = score_candidate([], (0,0), datetime(2024, 1, 1), datetime(2024, 1, 2), 0.0, 0, False)
        labels = [f["label"] for f in factors]
        expected = [
            "Proximity to origin", 
            "Timing overlap", 
            "Trajectory consistency", 
            "Drift agreement", 
            "AIS discrepancy"
        ]
        self.assertEqual(labels, expected)

if __name__ == "__main__":
    unittest.main()
