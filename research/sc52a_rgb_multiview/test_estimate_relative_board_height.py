"""Pure synthetic plane-height tests. Never use private or operator recordings."""
import unittest
import numpy as np
from estimate_relative_board_height import analyze_depth_pair

W,H=160,120
INTR=[205.,204.,W/2.,H/2.,0.]

def fixture(board_rise_mm=70.,camera_background_shift_mm=3.,blind=False,
            no_board=False):
    y,x=np.mgrid[:H,:W]
    xn=(x-INTR[2])/INTR[0]
    yn=(y-INTR[3])/INTR[1]
    ray=np.sqrt(1+xn*xn+yn*yn)
    # Unit normal tilted about 37 deg. Board and floor are parallel planes.
    n=np.array([.6,0.,.8])
    ray_to_plane=n[0]*xn+n[1]*yn+n[2]
    d=1000.
    raised=(x>=45)&(x<115)&(y>=30)&(y<92)
    floor=(d/ray_to_plane)*ray
    shift=camera_background_shift_mm + (0 if no_board else board_rise_mm)*raised
    board=((d-shift)/ray_to_plane)*ray
    floor=np.rint(floor)
    board=np.rint(board)
    if blind:
        # Camera-visible loss of depth at some board candidate contour pixels.
        board[(x>=45)&(x<=58)&raised]=np.nan
    return floor,board

class NormalHeightTests(unittest.TestCase):
    def test_tilted_board_seventy_mm_and_global_mount_shift(self):
        empty,board=fixture()
        result=analyze_depth_pair(empty,board,INTR,real_measured_height_mm=70)
        self.assertEqual(result["status"],"preliminary_unverified_depth_difference",result)
        self.assertAlmostEqual(result["estimated_perpendicular_change_mm_preliminary"],70,delta=1.0)
        self.assertAlmostEqual(result["surrounding_background_raw_projected_normal_shift_mm"],-3.,delta=1)
        self.assertGreater(result["candidate_core_px"],100)
        self.assertLess(result["candidate_unknown_neighbor_fraction"],0.02)
        self.assertFalse(result["slope_accuracy_certified"])
        self.assertFalse(result["candidate_identified_as_physical_board"])

    def test_known_height_is_not_used_to_fit_result(self):
        empty,board=fixture()
        a=analyze_depth_pair(empty,board,INTR,real_measured_height_mm=70)
        b=analyze_depth_pair(empty,board,INTR,real_measured_height_mm=123)
        self.assertEqual(a["estimated_perpendicular_change_mm_preliminary"],
                         b["estimated_perpendicular_change_mm_preliminary"])
        self.assertTrue(a["operator_height_did_not_tune_estimator"])

    def test_blind_boundary_is_unresolved(self):
        empty,board=fixture(blind=True)
        r=analyze_depth_pair(empty,board,INTR,real_measured_height_mm=70)
        self.assertEqual(r["status"],"unresolved_boundary_preliminary_height_only",r)
        self.assertGreater(r["candidate_unknown_neighbor_fraction"],.15)
        self.assertFalse(r["camera_translation_independently_verified"])
        self.assertFalse(r["slope_accuracy_certified"])

    def test_only_global_translation_does_not_fabricate_board(self):
        empty,board=fixture(no_board=True)
        with self.assertRaisesRegex(ValueError,"No connected depth-change candidate"):
            analyze_depth_pair(empty,board,INTR,real_measured_height_mm=70)

    def test_different_camera_pixel_dimensions_rejected(self):
        empty,board=fixture()
        with self.assertRaisesRegex(ValueError,"Camera images not aligned"):
            analyze_depth_pair(empty,board[:-2],INTR)

if __name__=="__main__":unittest.main()
