import unittest
from scoring import rank_candidates

class TestScoring(unittest.TestCase):
    def test_gap_alone_cannot_win(self):
        # Candidate 1: Has a massive 48h gap but nothing else (base score 0)
        gap_only_candidate = {
            "mmsi": "999999999",
            "name": "Gap Only",
            "gap_events": [{"duration_hours": 48}]
        }
        
        # Candidate 2: Has proximity and timing but NO gap
        strong_candidate = {
            "mmsi": "574951179", # Hardcoded in stub to get 20 prox + 30 timing = 50
            "name": "Strong Evidence",
            "gap_events": []
        }
        
        candidates = [gap_only_candidate, strong_candidate]
        
        # Dummy bbox and window
        ranked = rank_candidates(candidates, [0,0,1,1], {"start": "2024", "end": "2025"})
        
        # Strong candidate should win despite having NO gap
        self.assertEqual(ranked[0]["mmsi"], "574951179")
        self.assertEqual(ranked[0]["total_score"], 50)
        
        # Gap only candidate should be penalized
        self.assertEqual(ranked[1]["mmsi"], "999999999")
        self.assertLessEqual(ranked[1]["total_score"], 5)
        self.assertIn("Penalized", ranked[1]["breakdown"]["ais_gap"]["reason"])

if __name__ == "__main__":
    unittest.main()
