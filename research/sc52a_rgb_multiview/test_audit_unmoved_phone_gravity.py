"""Synthetic regression: the gravity estimator isn't proof of phone motion."""
import unittest
import numpy as np
from audit_unmoved_phone_gravity import (
    angle_deg, posture_interpretation, unit, audit
)


class UnmovedPhoneGravityAuditTests(unittest.TestCase):
    def test_1point2_deg_is_conflict_not_proof_of_device_motion(self):
        status=posture_interpretation(1.222,True)
        self.assertEqual(
            status,
            "FUSED_GRAVITY_DIRECTION_DISAGREES_WITH_FIXED_MOUNT_REPORT")
        self.assertNotIn("DEVICE_MOVED",status)

    def test_near_zero_sensor_change_has_no_large_conflict(self):
        self.assertEqual(
            posture_interpretation(.017,True),
            "NO_LARGE_INTER_SESSION_GRAVITY_CONFLICT_DETECTED")

    def test_sensor_orientation_from_gravity_vector_is_indirect(self):
        a=np.array([0.,0.,9.80665])
        b=np.array([.2092,0.,9.80665])
        self.assertAlmostEqual(angle_deg(a,b),1.222,places=2)
        self.assertEqual(np.linalg.norm(unit(a)),1.0)

    def test_negative_and_nan_are_rejected(self):
        for angle in (-1.0,float('nan')):
            with self.assertRaises(ValueError):
                posture_interpretation(angle,True)

    def test_requires_explicit_fixed_mount_statement(self):
        with self.assertRaises(ValueError):
            posture_interpretation(1.2,None)

    def test_duplicate_session_rejected_without_reading_private_file(self):
        with self.assertRaises(ValueError):
            audit(["identical.zip"]*4,True)


if __name__=="__main__":
    unittest.main()
