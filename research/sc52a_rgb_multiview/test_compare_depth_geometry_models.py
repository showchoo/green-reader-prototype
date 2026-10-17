"""Synthetic plane geometries: model selection does NOT claim real grade truth."""
import unittest
import numpy as np
from compare_depth_geometry_models import (
    rays_from_calibration, evaluate_frame, region_points, robust_plane
)


class DepthModelSelectionTests(unittest.TestCase):
    def setUp(self):
        self.cal={"width":640,"height":480,
                  "lens_intrinsic_calibration":[535,535,317,245,0],
                  "lens_distortion":[0,0,0,0,0]}
        self.rays=rays_from_calibration(self.cal)
        n=np.array([.66,.03,.75])
        self.normal=n/np.linalg.norm(n)
        self.depth_z=1000/(self.rays@self.normal)

    def test_true_axial_plane_selects_axial(self):
        observed=np.rint(self.depth_z).astype(np.uint16)
        axial=evaluate_frame(observed,self.rays,"optical_axis")
        radial=evaluate_frame(observed,self.rays,"euclidean_range")
        for key in axial:
            self.assertLess(axial[key][0],1.)
            self.assertGreater(radial[key][0],5.)

    def test_true_radial_plane_selects_euclidean(self):
        radial=np.rint(self.depth_z*np.linalg.norm(
            self.rays,axis=2)).astype(np.uint16)
        good=evaluate_frame(radial,self.rays,"euclidean_range")
        wrong=evaluate_frame(radial,self.rays,"optical_axis")
        for key in good:
            self.assertLess(good[key][0],1.)
            self.assertGreater(wrong[key][0],5.)

    def test_missing_calibration_fails_closed(self):
        with self.assertRaises(ValueError):
            rays_from_calibration({"width":640,"height":480,
                                   "lens_intrinsic_calibration":[],
                                   "lens_distortion":[]})

    def test_no_ranges_has_no_plane(self):
        pts=region_points(np.zeros((480,640),dtype=np.uint16),
                          self.rays,(80,400,350,620),"optical_axis")
        self.assertEqual(len(pts),0)
        self.assertIsNone(robust_plane(pts))


if __name__=="__main__":
    unittest.main()
