from django.test import TestCase
from apps.core.geo import distance_meters, is_within_radius


class GeoTests(TestCase):
    def test_distance_and_radius(self):
        # Mumbai approx
        lat1, lon1 = 19.0760, 72.8777
        # Nearby point (~100m away)
        lat2, lon2 = 19.0769, 72.8785
        d = distance_meters(lat1, lon1, lat2, lon2)
        self.assertTrue(d > 0)
        self.assertTrue(is_within_radius(lat2, lon2, lat1, lon1, radius_meters=1000))
        self.assertFalse(is_within_radius(lat2, lon2, lat1, lon1, radius_meters=1))
