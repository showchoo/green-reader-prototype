"""Synthetic negative controls; private field recordings never enter GitHub."""
import unittest
import numpy as np
from audit_single_view_local_surface import estimate_local_surface,sensitivity

W,H=160,120
INTR=[205.,204.,W/2,H/2,0.]
OUTER=(20,145,10,115)
EXCLUDED=(44,116,27,94)
INNER=(60,102,43,80)

def synthetic(rise_mm=0.,noise_mm=0):
    yy,xx=np.indices((H,W))
    xn=(xx-INTR[2])/INTR[0];yn=(yy-INTR[3])/INTR[1]
    ray=np.sqrt(1+xn*xn+yn*yn)
    normal=np.array([.6,.05,.798435])
    normal/=np.linalg.norm(normal)
    dot=normal[0]*xn+normal[1]*yn+normal[2]
    u=(xx-W/2)/(W/2);v=(yy-H/2)/(H/2)
    # Smooth vendor-like optical depth bias, independent of requested rise.
    optical=1000/dot+4*u*u-3*v*v+2*u*v+u*u*u
    raised=(xx>=45)&(xx<115)&(yy>=28)&(yy<93)
    optical=optical-(rise_mm/dot)*raised
    return optical*ray

class SyntheticLocalSurfaceTests(unittest.TestCase):
    def run_estimate(self,depth,degree=3):
        return estimate_local_surface(depth,INTR,OUTER,EXCLUDED,INNER,degree,2)

    def test_raised_surface_35_and_70mm_are_distinguishable(self):
        a=self.run_estimate(synthetic(35.))
        b=self.run_estimate(synthetic(70.))
        self.assertAlmostEqual(a["local_normal_projected_contrast_mm"],35.,delta=2.)
        self.assertAlmostEqual(b["local_normal_projected_contrast_mm"],70.,delta=2.)
        self.assertAlmostEqual(b["local_normal_projected_contrast_mm"]/
                               a["local_normal_projected_contrast_mm"],2.,delta=.08)
        self.assertFalse(a["real_surface_height_independently_verified"])
        self.assertFalse(b["physical_grade_accuracy_certified"])

    def test_blank_scene_negative_control_cannot_invent_35mm(self):
        r=self.run_estimate(synthetic(0.))
        self.assertLess(abs(r["local_normal_projected_contrast_mm"]),3.)
        self.assertFalse(r["operator_board_identity_verified"])

    def test_manual_roi_not_assumed_ground_truth(self):
        with self.assertRaisesRegex(ValueError,"ROI geometry not nested"):
            estimate_local_surface(synthetic(35.),INTR,OUTER,EXCLUDED,
                                   (0,8,0,8),3,2)
        with self.assertRaisesRegex(ValueError,"Invalid explicitly supplied region"):
            estimate_local_surface(synthetic(35.),INTR,OUTER,
                                   (-4,116,27,94),INNER,3,2)

    def test_blank_scene_sensitivity_never_certifies_accuracy(self):
        models=[{"name":"base","outer":OUTER,"excluded":EXCLUDED,"inner":INNER},
                {"name":"wider","outer":OUTER,"excluded":(40,119,25,96),
                 "inner":(62,100,45,77)}]
        r=sensitivity(synthetic(0.),INTR,models)
        self.assertEqual(r["trial_count"],6)
        self.assertFalse(r["physical_height_or_slope_accuracy_certified"])
        self.assertLess(abs(r["median_apparent_contrast_mm"]),4.)

if __name__=="__main__":unittest.main()
