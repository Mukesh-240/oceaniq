import unittest
from scoring import score_candidate

class TestScoring(unittest.TestCase):
    def test_gap_alone_cannot_win(self):
        # Candidate 1: Has a massive gap but nothing else (base score 0)
        score1, factors1 = score_candidate(
            track=[],
            origin_centre=[0,0],
            win_start="2024",
            win_end="2025",
            drift_bearing=None,
            gap_hours=48,
            presence=False
        )
        
        # Candidate 2: Has proximity and timing but NO gap
        score2, factors2 = score_candidate(
            track=[{"lat": 0, "lon": 0}, {"lat": 1, "lon": 1}],
            origin_centre=[0,0],
            win_start="2024",
            win_end="2025",
            drift_bearing=45.0,
            gap_hours=0,
            presence=True
        )
        
        # Strong candidate should win despite having NO gap
        self.assertEqual(score2, 90.0)
        
        # Gap only candidate should be penalized
        self.assertLessEqual(score1, 2.0)
        self.assertIn("Penalized", factors1[4]["explanation"])
        
    def test_factor_labels_exact(self):
        _, factors = score_candidate([], [0,0], "", "", None, 0, False)
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
