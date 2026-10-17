import unittest
from physical_grade_reference_gate import physical_grade_reference


class PhysicalReferenceGateTests(unittest.TestCase):
    def test_rise_and_support_span_both_measured(self):
        r=physical_grade_reference(40,1000,1,5,True,True,True,True)
        self.assertTrue(r["reference_valid"])
        self.assertEqual(r["reference_grade_pct"],4.)
        self.assertGreater(r["reference_max_deviation_pp"],.12)
        self.assertLess(r["reference_max_deviation_pp"],.13)
        self.assertFalse(r["accuracy_certified"])

    def test_cardboard_length_is_not_a_measured_support_span(self):
        r=physical_grade_reference(40,1000,1,5,False,False,False,False)
        self.assertFalse(r["reference_valid"])
        self.assertIsNone(r["reference_grade_pct"])

    def test_unsure_shim_height_is_too_uncertain(self):
        r=physical_grade_reference(40,1000,5,10,True,True,True,True)
        self.assertFalse(r["reference_valid"])

    def test_unverified_level_baseline_is_rejected(self):
        r=physical_grade_reference(40,1000,1,5,True,True,True,False)
        self.assertFalse(r["reference_valid"])

    def test_invalid_physical_support_distance_rejected(self):
        with self.assertRaises(ValueError):
            physical_grade_reference(40,0,1,0,True,True,True,True)

    def test_nan_rejected(self):
        with self.assertRaises(ValueError):
            physical_grade_reference(float("nan"),1000,1,5,True,True,True,True)


if __name__=="__main__":
    unittest.main()
