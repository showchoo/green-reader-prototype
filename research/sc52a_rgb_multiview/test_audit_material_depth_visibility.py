"""Synthetic comparisons only; no private user frames committed."""
import unittest
import numpy as np
from audit_material_depth_visibility import audit_images

H,W=120,160
INTR=[205.,205.,W/2,H/2,0.]
SUB=[45,30,100,85]
BG=[110,35,150,90]

def pair(visible_rise_mm=0,background_drift_mm=-3,blocked=False):
    yy,xx=np.indices((H,W))
    ray=np.sqrt(1+((xx-INTR[2])/INTR[0])**2+((yy-INTR[3])/INTR[1])**2)
    empty=1000*ray
    board=(1000+background_drift_mm)*ray
    board=board.copy()
    sx=(xx>=SUB[0])&(xx<SUB[2])&(yy>=SUB[1])&(yy<SUB[3])
    board[sx]-=visible_rise_mm*ray[sx]
    if blocked:board[sx]=np.nan
    return empty,board

class MaterialDepthVisibilityTests(unittest.TestCase):
    def test_opaque_like_35mm_depth_step_is_visible_but_not_height_certified(self):
        e,b=pair(visible_rise_mm=35)
        r=audit_images(e,b,INTR,SUB,BG,operator_rise_mm=35)
        self.assertEqual(r["status"],"negative_depth_step_observed_but_unverified",r)
        self.assertAlmostEqual(r["subject_median_background_corrected_optical_z_delta_mm"],-35,delta=.1)
        self.assertGreater(r["subject_negative_at_least_25mm_fraction"],.99)
        self.assertFalse(r["physical_height_estimated_or_certified"])
        self.assertFalse(r["optical_material_is_translucent_verified"])

    def test_unresolved_35mm_surface_with_stable_depth_does_not_get_height(self):
        e,b=pair(visible_rise_mm=0)
        r=audit_images(e,b,INTR,SUB,BG,operator_rise_mm=35)
        self.assertEqual(r["status"],"operator_elevated_surface_not_resolved_in_depth",r)
        self.assertAlmostEqual(r["subject_median_background_corrected_optical_z_delta_mm"],0,delta=.1)
        self.assertFalse(r["infrared_passes_through_object_verified"])
        self.assertFalse(r["physical_height_estimated_or_certified"])

    def test_no_operator_height_does_not_invent_translucent_object(self):
        e,b=pair(visible_rise_mm=0)
        r=audit_images(e,b,INTR,SUB,BG)
        self.assertEqual(r["status"],"ambiguous_depth_response",r)
        self.assertIsNone(r["operator_reported_rise_mm"])

    def test_partial_echo_depth_is_not_misclassified_as_a_measured_step(self):
        e,b=pair(visible_rise_mm=13)
        r=audit_images(e,b,INTR,SUB,BG,operator_rise_mm=35)
        self.assertEqual(r["status"],"ambiguous_depth_response",r)
        self.assertFalse(r["slope_accuracy_certified"])

    def test_heavy_occlusion_fails_instead_of_zero_depth_confusion(self):
        e,b=pair(visible_rise_mm=35,blocked=True)
        with self.assertRaisesRegex(ValueError,"Insufficient stable overlapping"):
            audit_images(e,b,INTR,SUB,BG,operator_rise_mm=35)

    def test_roi_must_not_overlap_background(self):
        e,b=pair()
        with self.assertRaisesRegex(ValueError,"must not overlap"):
            audit_images(e,b,INTR,SUB,[95,50,140,100],35)

    def test_mismatched_frames_and_malformed_roi_fail(self):
        e,b=pair()
        with self.assertRaisesRegex(ValueError,"Unaligned depth arrays"):
            audit_images(e,b[:-1],INTR,SUB,BG,35)
        with self.assertRaisesRegex(ValueError,"Invalid image rectangle"):
            audit_images(e,b,INTR,[160,30,180,90],BG,35)

if __name__=="__main__":unittest.main()
