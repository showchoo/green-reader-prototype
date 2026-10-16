import math
import unittest

from precision_budget import axial_error_mm, gravity_grade_error_pp, illustrative_budget


class StereoBudgetTest(unittest.TestCase):
    def test_depth_error_quadratic_with_range(self):
        self.assertAlmostEqual(
            axial_error_mm(2, 1000, .25, .5),
            4 * axial_error_mm(1, 1000, .25, .5))

    def test_one_px_at_two_meters_is_sixteen_mm_given_assumptions(self):
        self.assertAlmostEqual(axial_error_mm(2, 1000, .25, 1), 16.)

    def test_tenth_degree_tilt_matters_for_slope(self):
        self.assertAlmostEqual(gravity_grade_error_pp(.1), .174533,delta=.0001)

    def test_no_device_accuracy_certification(self):
        self.assertFalse(illustrative_budget()["calibrated_device_data"])

    def test_bad_inputs_fail(self):
        with self.assertRaises(ValueError):
            axial_error_mm(2,0,.25,.2)
        with self.assertRaises(ValueError):
            axial_error_mm(2,1000,.25,math.nan)


if __name__=="__main__":
    unittest.main()
