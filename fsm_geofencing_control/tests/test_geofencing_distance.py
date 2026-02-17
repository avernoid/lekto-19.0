from odoo.tests import TransactionCase
from ..utils.geo_utils import calculate_distance


class TestGeofencingDistance(TransactionCase):
    """Test distance calculation utility functions."""

    def test_distance_calculation_same_point(self):
        """Test distance between same point should be 0."""
        distance = calculate_distance(40.7128, -74.0060, 40.7128, -74.0060)
        self.assertAlmostEqual(distance, 0.0, places=2)

    def test_distance_calculation_known_distance(self):
        """Test distance calculation with known coordinates."""
        # New York to Los Angeles (approximately 3935 km = 3,935,000 m)
        distance = calculate_distance(40.7128, -74.0060, 34.0522, -118.2437)
        self.assertGreater(distance, 3900000)
        self.assertLess(distance, 4000000)

    def test_distance_calculation_short_distance(self):
        """Test distance calculation for short distances (1 km = 1000 m)."""
        # Two points approximately 1 km apart
        distance = calculate_distance(40.7128, -74.0060, 40.7218, -74.0060)
        self.assertGreater(distance, 900)
        self.assertLess(distance, 1100)

    def test_distance_calculation_zero_coordinates(self):
        """Test distance calculation with zero coordinates."""
        distance = calculate_distance(0, 0, 0, 0)
        self.assertAlmostEqual(distance, 0.0, places=2)

    def test_distance_calculation_negative_coordinates(self):
        """Test distance calculation with negative coordinates."""
        # Test with southern and western hemispheres
        distance = calculate_distance(-33.8688, 151.2093, -37.8136, 144.9631)
        # Sydney to Melbourne (approximately 714 km = 714,000 m)
        self.assertGreater(distance, 700000)
        self.assertLess(distance, 730000)
