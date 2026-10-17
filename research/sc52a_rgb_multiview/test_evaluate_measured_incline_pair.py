"""Synthetic measured 2% incline, invalid reference and no false product PASS."""
import unittest
import numpy as np
from evaluate_measured_incline_pair import compare_normal_delta


class PairedNormalCalibrationTests(unittest.TestCase):
    def test_known_20mm_on_1000mm(self):
        a=np.array([0.,0.,1.])
        b=np.array([.02,0.,1.])
        b=b/np.linalg.norm(b)
        r=compare_normal_delta(a,b,20,1000)
        self.assertAlmostEqual(r["candidate_unsigned_grade_change_percent"],2.,places=3)
        self.assertAlmostEqual(r["unsigned_error_pp"],0.,places=3)
        self.assertFalse(r["certified_accuracy"])
        self.assertFalse(r["signed_grade_available"])

    def test_no_run_refuses_inferred_slope(self):
        with self.assertRaises(ValueError):
            compare_normal_delta([0,0,1],[0,0,1],20,0)

    def test_bad_negative_shim_refused(self):
        with self.assertRaises(ValueError):
            compare_normal_delta([0,0,1],[0,0,1],-5,1000)


if __name__=="__main__":
    unittest.main()
