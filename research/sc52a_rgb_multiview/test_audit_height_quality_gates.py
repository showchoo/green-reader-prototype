"""Synthetic-only research quality gates + independent 35mm holdout controls."""
import copy
import unittest

from audit_height_quality_gates import qualify_pair, imu_quality
from estimate_relative_board_height import analyze_depth_pair
from test_estimate_relative_board_height import fixture,INTR

def fake_imu(g=(0,0,9.8),a=(0,0,9.8),clock=True,raw=True,frames=12,drift=.01):
    return {
        "camera_sensor_timebases_comparable":clock,
        "raw_motion_diagnostics_available":raw,
        "frames":frames,
        "nonempty_depth_frames":frames,
        "directional_streams":{
            "gravity":{
                "capture_end_median_xyz":list(g),
                "capture_first_half_second_vs_last_half_second_deg":drift
            },
            "accelerometer":{
                "capture_end_median_xyz":list(a)
            }
        }
    }

class QualityGateTests(unittest.TestCase):
    def fake_height(self):
        return {
            "candidate_touches_image_edge":False,
            "candidate_unknown_neighbor_fraction":.01,
            "empty_floor_plane_fit_median_absolute_residual_mm":.9,
            "paired_pixels":14000,
            "surrounding_background_raw_projected_normal_shift_mm":-2.,
            "estimated_perpendicular_change_mm_preliminary":70.,
            "operator_measured_vertical_height_mm":70.
        }

    def qualify(self,h=None,e=None,b=None):
        return qualify_pair(h or self.fake_height(),e or fake_imu(),
                            b or fake_imu(),160,120)

    def test_good_observational_checks_do_not_certify_real_accuracy(self):
        r=self.qualify()
        self.assertTrue(r["research_quality_gates_passed"])
        self.assertFalse(r["camera_pose_independently_verified"])
        self.assertFalse(r["absolute_board_height_accuracy_verified"])
        self.assertFalse(r["software_approved_for_real_green_slope_output"])

    def test_rejects_real_capture_like_blind_contour_and_floor_residual(self):
        h=self.fake_height()
        h["candidate_unknown_neighbor_fraction"]=.531
        h["empty_floor_plane_fit_median_absolute_residual_mm"]=8.525
        h["paired_pixels"]=243524
        r=qualify_pair(h,fake_imu(),fake_imu(),640,480)
        self.assertFalse(r["research_quality_gates_passed"])
        self.assertIn("candidate_contour_not_fully_observable",r["quality_rejection_reasons"])
        self.assertIn("floor_is_not_well_approximated_by_one_local_plane",r["quality_rejection_reasons"])

    def test_angle_disagreement_rejected_even_with_ideal_depth(self):
        r=self.qualify(b=fake_imu(g=(.1,0,9.8),a=(.1,0,9.8)))
        self.assertFalse(r["research_quality_gates_passed"])
        self.assertIn("cross_session_gravity_direction_mismatch",r["quality_rejection_reasons"])
        self.assertIn("cross_session_accelerometer_direction_mismatch",r["quality_rejection_reasons"])

    def test_unknown_timebase_missing_streams_rejected(self):
        r=self.qualify(e=fake_imu(clock=False,raw=False))
        self.assertFalse(r["research_quality_gates_passed"])
        self.assertIn("empty_camera_imu_clock_unverified",r["quality_rejection_reasons"])
        self.assertIn("empty_raw_imu_missing_or_corrupted",r["quality_rejection_reasons"])

    def test_camera_shift_and_lost_overlap_block_research_qualification(self):
        h=self.fake_height()
        h["surrounding_background_raw_projected_normal_shift_mm"]=-25
        h["paired_pixels"]=200
        r=self.qualify(h=h)
        self.assertFalse(r["research_quality_gates_passed"])
        self.assertIn("insufficient_common_depth_pixels",r["quality_rejection_reasons"])
        self.assertIn("background_rigid_alignment_not_supported",r["quality_rejection_reasons"])

    def test_height_label_never_changes_any_quality_gate(self):
        h=self.fake_height()
        x=self.qualify(h=h)
        h["operator_measured_vertical_height_mm"]=999
        y=self.qualify(h=h)
        self.assertEqual(x,y)

    def test_missing_or_nan_critical_quality_fields_fail_closed(self):
        for field in ("candidate_unknown_neighbor_fraction",
                      "empty_floor_plane_fit_median_absolute_residual_mm",
                      "paired_pixels",
                      "surrounding_background_raw_projected_normal_shift_mm",
                      "estimated_perpendicular_change_mm_preliminary"):
            with self.subTest(field=field):
                h=self.fake_height()
                h[field]=float("nan")
                self.assertFalse(self.qualify(h=h)["research_quality_gates_passed"])

class NewHeightHoldoutTests(unittest.TestCase):
    def test_35mm_70mm_100mm_synthetic_board_height_proportionality(self):
        values=[]
        for rise in (35.,70.,100.):
            empty,board=fixture(board_rise_mm=rise)
            r=analyze_depth_pair(empty,board,INTR,real_measured_height_mm=rise)
            estimated=r["estimated_perpendicular_change_mm_preliminary"]
            self.assertAlmostEqual(estimated,rise,delta=1.5)
            self.assertFalse(r["slope_accuracy_certified"])
            self.assertFalse(r["camera_translation_independently_verified"])
            values.append(estimated)
        self.assertAlmostEqual(values[1]/values[0],2.,delta=.12)
        self.assertAlmostEqual(values[2]/values[1],100/70,delta=.10)

    def test_camera_only_scene_shift_without_board_is_rejected(self):
        empty,board=fixture(no_board=True)
        with self.assertRaisesRegex(ValueError,"No connected depth-change candidate"):
            analyze_depth_pair(empty,board,INTR)

if __name__=="__main__":
    unittest.main()
