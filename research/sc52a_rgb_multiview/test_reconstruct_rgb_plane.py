"""Synthetic-only calibrated RGB geometry regression. No private room images."""
import unittest

import cv2
import numpy as np
from scipy.spatial.transform import Rotation

from reconstruct_rgb_plane import (
    S, projection, project, triangulate_pair, fit_height_plane, allowed_jpeg
)


class CalibratedStereoTest(unittest.TestCase):
    def make_scene(self):
        rng=np.random.default_rng(11)
        x=rng.uniform(-.8,.8,600)
        z=rng.uniform(-3.,-1.,600)
        true_grade_x=.025
        true_grade_z=-.013
        y=-.55+true_grade_x*x+true_grade_z*z
        xyz=np.column_stack((x,y,z))
        K=np.array([[480.,0.,320.],[0.,476.,240.],[0.,0.,1.]])
        q=Rotation.from_euler("x",-24,degrees=True).as_quat()
        P0=projection(np.array([0.,.2,0.]),q,K)
        P1=projection(np.array([.25,.2,0.]),q,K)
        return xyz,P0,P1

    def test_calibrated_geometry_round_trip_and_plane(self):
        xyz,P0,P1=self.make_scene()
        p0=project(P0,xyz)
        p1=project(P1,xyz)
        recovered,err,positive=triangulate_pair(P0,P1,p0,p1)
        self.assertTrue(positive.all())
        self.assertLess(np.max(err),1e-7)
        self.assertLess(np.max(np.linalg.norm(recovered-xyz,axis=1)),1e-6)
        # Inject a few tall objects to confirm spatial robust plane gate.
        rng=np.random.default_rng(12)
        clutter=np.column_stack((rng.uniform(-.5,.5,80),
                                 rng.uniform(-.3,.2,80),
                                 rng.uniform(-2.7,-1.2,80)))
        fit=fit_height_plane(np.vstack([recovered,clutter]),-.55)
        self.assertIsNotNone(fit)
        a,b,c=fit["plane"]
        self.assertAlmostEqual(a,.025,delta=.002)
        self.assertAlmostEqual(b,-.013,delta=.002)
        self.assertAlmostEqual(c,-.55,delta=.005)
        self.assertGreaterEqual(fit["inlier_count"],590)

    def test_camera_translation_required_for_triangulation(self):
        xyz,P0,P1=self.make_scene()
        p0,p1=project(P0,xyz),project(P1,xyz)
        recovered,err,positive=triangulate_pair(P0,P1,p0,p1)
        self.assertTrue(positive.all())
        self.assertLess(np.median(err),.000001)

    def test_image_validation_fail_closed(self):
        self.assertFalse(allowed_jpeg(b""))
        self.assertFalse(allowed_jpeg(b"\xff\xd8\xff\xd9"))
        self.assertFalse(allowed_jpeg(b"\xff\xd8"+bytes(1200)))
        self.assertTrue(allowed_jpeg(b"\xff\xd8"+bytes(1200)+b"\xff\xd9"))

    def test_insufficient_plane_coverage_refused(self):
        rng=np.random.default_rng(4)
        pts=np.column_stack((rng.uniform(-.1,.1,10),
                             np.ones(10)*-.55,
                             rng.uniform(-2,-1,10)))
        self.assertIsNone(fit_height_plane(pts,-.55))


if __name__=="__main__":
    unittest.main()
