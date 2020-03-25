import unittest
from core.locationcalc import get_area_coord

class TestLocationCalc(unittest.TestCase):

    def test_equator_1000(self):
        self.assertEqual(get_area_coord('0.006735', '9.353520', 1000),
                         (-0.002265, 9.34452, 0.015735, 9.36252))

    def test_north_1000(self):
        self.assertEqual(get_area_coord('51.498305', '0.085904', 1000),
                         (51.489305, 0.071447, 51.507305, 0.100361))

    def test_south_1000(self):
        self.assertEqual(get_area_coord('-54.734692', '-67.200944', 1000),
                         (-54.743692, -67.216532, -54.725692, -67.185356))

if __name__ == "__main__":
  unittest.main()