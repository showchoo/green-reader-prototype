import unittest
import numpy as np
from audit_four_depth16_capture_pairings import (
    condition_labels, normal_angle_deg, normalized, evaluate_four,
)


class FourUnlabeledCaptureAuditTests(unittest.TestCase):
    def test_absent_labels_are_not_inferred_from_timestamps(self):
        self.assertIsNone(condition_labels(None))

    def test_unknown_or_unequal_conditions_rejected(self):
        for labels in (["level"]*4,
                       ["level","raised","level","none"],
                       ["raised","raised","raised","level"]):
            with self.assertRaises(ValueError):
                condition_labels(labels)

    def test_both_plausible_capture_sequences_accepted_if_user_confirms(self):
        self.assertEqual(condition_labels(
            ["level","raised","level","raised"]),
            ["level","raised","level","raised"])
        self.assertEqual(condition_labels(
            ["level","level","raised","raised"]),
            ["level","level","raised","raised"])

    def test_camera_orientation_change_not_target_grade(self):
        a=np.array([0,0,1],float)
        b=np.array([0,.02,1.],float)
        self.assertAlmostEqual(normal_angle_deg(a,b),1.1457628,places=5)
        self.assertFalse(normal_angle_deg(a,a)>.15)
        self.assertTrue(normal_angle_deg(a,b)>.15)

    def test_zero_norm_fails_closed(self):
        with self.assertRaises(ValueError):
            normalized([0,0,0])

    def test_four_distinct_archives_required(self):
        with self.assertRaises(ValueError):
            evaluate_four(["same.zip"]*4)

if __name__=="__main__":
    unittest.main()
