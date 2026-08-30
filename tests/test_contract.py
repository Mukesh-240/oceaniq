import unittest
from contracts.validate import validate_payload

class TestContract(unittest.TestCase):
    def setUp(self):
        self.base_payload = [{
            "mmsi": "123",
            "factors": [
                {"label": "Proximity to origin", "score": 25.0},
                {"label": "Timing overlap", "score": 25.0},
                {"label": "Trajectory consistency", "score": 20.0},
                {"label": "Drift agreement", "score": 20.0},
                {"label": "AIS discrepancy", "score": 10.0}
            ],
            "track": [{"lat": 10.0, "lon": 10.0}],
            "time_window": {"start": "2024", "end": "2025"}
        }]

    def test_valid_payload(self):
        self.assertTrue(validate_payload(self.base_payload))
        
    def test_invalid_factors_count(self):
        # 4 factors instead of 5
        self.base_payload[0]["factors"].pop()
        with self.assertRaises(ValueError) as ctx:
            validate_payload(self.base_payload)
        self.assertIn("expected 5", str(ctx.exception))
        
    def test_score_out_of_bounds(self):
        # Score of 120
        self.base_payload[0]["factors"][0]["score"] = 120.0
        with self.assertRaises(ValueError) as ctx:
            validate_payload(self.base_payload)
        self.assertIn("must be between 0 and 100", str(ctx.exception))
        
    def test_swapped_lat_lon(self):
        # lat = 100
        self.base_payload[0]["track"] = [{"lat": 100.0, "lon": 10.0}]
        with self.assertRaises(ValueError) as ctx:
            validate_payload(self.base_payload)
        self.assertIn("Invalid latitude", str(ctx.exception))
        
    def test_reversed_window(self):
        # reversed time window
        self.base_payload[0]["time_window"] = {"start": "2025", "end": "2024"}
        with self.assertRaises(ValueError) as ctx:
            validate_payload(self.base_payload)
        self.assertIn("strictly less than end", str(ctx.exception))

if __name__ == "__main__":
    unittest.main()
