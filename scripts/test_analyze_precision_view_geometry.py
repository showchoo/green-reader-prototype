"""Deterministic, self-contained tests for saved-scan view geometry audit."""
import csv
import io
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze_precision_view_geometry as analysis


HEADER = (
    "depth_timestamp_ns,camera_frame_timestamp_ns,source,"
    "camera_local_x_m,camera_local_y_m,camera_local_z_m,"
    "camera_world_qx,camera_world_qy,camera_world_qz,camera_world_qw,"
    "camera_forward_local_x,camera_forward_local_y,camera_forward_local_z,"
    "camera_right_local_x,camera_right_local_y,camera_right_local_z,"
    "projection_basis,projection_width,projection_height,"
    "intrinsics_fx,intrinsics_fy,intrinsics_cx,intrinsics_cy"
)


def pose(time, source="raw", t=3000000):
    return ",".join(map(str, [
        time, time+t, source, 0, 1, 0,
        0, 0, 0, 1, 0, -.6, -.8, 1, 0, 0,
        "raw_texture_scaled" if source=="raw" else "cpu_image_pixels",
        640, 480, 320, 320, 320, 240
    ]))


def sample_record():
    diag = "\n".join([
        "windows=1 attempts=3",
        "FRAME_POSE_V1_BEGIN records=2 dropped=0",
        HEADER, pose(100), pose(200,"full"),
        "FRAME_POSE_V1_END"
    ])
    rows = ["index,x_m,y_m,z_m,confidence,frame_timestamp_ns"]
    src = ["index,frame_timestamp_ns,depth_source"]
    for i in range(32):
        timestamp, source = (100, "raw") if i < 16 else (200,"full")
        lateral = (i%8-3.5)*.03
        axial = 1.4+(.01*i)
        rows.append(f"{i},{lateral},{1-.6*axial},{-.8*axial},0.9,{timestamp}")
        src.append(f"{i},{timestamp},{source}")
    return diag, "\n".join(rows)+"\n", "\n".join(src)+"\n"


class ViewGeometryAuditTests(unittest.TestCase):
    def test_matching_source_and_timestamp_and_pixel_basis(self):
        diag, points, sources = sample_record()
        x = analysis.analyze_scan("fixture", diag, points, sources, sample_step=1)
        self.assertEqual("geometry_ready", x["status"])
        self.assertEqual(2, x["pose_records"])
        self.assertEqual(32, x["sampled_points"])
        self.assertEqual(32, x["matched_sampled_points"])
        self.assertEqual(32, x["sampled_rays"])
        self.assertEqual(16, x["raw_rays"])
        self.assertEqual(16, x["full_rays"])
        self.assertEqual(1, x["pixel_inside_fraction"])
        self.assertAlmostEqual(3.0, x["depth_age_median_ms"], places=4)

    def test_missing_pose_does_not_claim_success(self):
        _, points, sources = sample_record()
        x = analysis.analyze_scan("legacy", "attempts=30", points, sources)
        self.assertEqual("legacy_no_pose", x["status"])
        self.assertEqual(0, x["pose_records"])

    def test_v85_without_local_camera_axes_is_inconclusive(self):
        diag, points, sources = sample_record()
        diag = diag.replace(
            HEADER,
            "depth_timestamp_ns,camera_frame_timestamp_ns,source,"
            "camera_local_x_m,camera_local_y_m,camera_local_z_m,"
            "camera_world_qx,camera_world_qy,camera_world_qz,camera_world_qw"
        )
        # Strip v8.6 columns from each pose row.
        old_rows = diag.splitlines()
        diag = "\n".join(x if not x.startswith(("100,","200,"))
                         else ",".join(x.split(",")[:10]) for x in old_rows)
        x = analysis.analyze_scan("v85", diag, points, sources, sample_step=1)
        self.assertEqual("insufficient_geometry", x["status"])
        self.assertEqual(32, x["matched_sampled_points"])
        self.assertEqual(0, x["sampled_rays"])

    def test_duplicate_pose_keys_are_rejected_not_guessed(self):
        diag, points, sources = sample_record()
        diag = diag.replace(
            "FRAME_POSE_V1_END", pose(100) + "\nFRAME_POSE_V1_END"
        )
        x = analysis.analyze_scan("dup", diag, points, sources, sample_step=1)
        self.assertEqual(1, x["duplicate_pose_keys"])
        self.assertEqual(1, x["pose_records"])
        self.assertEqual(16, x["matched_sampled_points"])

    def test_shared_voxels_cancel_true_spatial_grade_in_view_comparison(self):
        records = []
        for cell in range(12):
            base_height = cell * .008  # a truly sloping ground across cells
            for frame in (10, 20):
                records.append(("raw", cell, 0, 5.0, base_height, frame))
            for frame in (30, 40):
                records.append(("raw", cell, 0, 25.0, base_height, frame))
        n, difference = analysis.matched_view_height_shift(records)
        self.assertEqual(12, n)
        self.assertAlmostEqual(0.0, difference, places=5)

    def test_view_dependent_same_voxel_height_disagreement_is_diagnostic(self):
        records = []
        for cell in range(12):
            base_height = cell * .01
            for frame in (10, 20):
                records.append(("full", cell, 0, 5.0, base_height, frame))
            for frame in (30, 40):
                records.append(("full", cell, 0, 27.0, base_height + .025, frame))
        n, difference = analysis.matched_view_height_shift(records)
        self.assertEqual(12, n)
        self.assertAlmostEqual(25.0, difference, places=4)

    def test_no_common_voxel_or_no_distinct_frames_stays_inconclusive(self):
        records = [
            ("raw", 0, 0, 5., 0.0, 10),
            ("raw", 0, 0, 26., .03, 30),
            ("raw", 0, 0, 26., .03, 30),  # repeated pixel, NOT 2 frames
            ("raw", 1, 0, 5., 0.0, 10),
            ("raw", 2, 0, 26., .03, 30)
        ]
        n, diff = analysis.matched_view_height_shift(records)
        self.assertEqual(0, n)
        self.assertIsNone(diff)

    def test_pose_motion_statistics_do_not_fake_missing_samples(self):
        diag, points, sources = sample_record()
        baseline = analysis.analyze_scan("v86", diag, points, sources, sample_step=1)
        self.assertEqual("not_recorded", baseline["pose_motion_status"])
        self.assertEqual(0, baseline["matched_depth_pose_records"])
        self.assertEqual("", baseline["camera_translation_delta_p95_m"])

        columns = (
            ",nearest_camera_frame_timestamp_ns,nearest_camera_gap_ms,"
            "camera_translation_delta_m,camera_forward_delta_deg"
        )
        diag = diag.replace(HEADER, HEADER + columns)
        lines = diag.splitlines()
        for i, line in enumerate(lines):
            if line.startswith("100,"):
                lines[i] += ",100,0,0.023,1.5"
            elif line.startswith("200,"):
                lines[i] += ",198,0.000002,0.091,3.0"
        diag = "\n".join(lines)
        with_motion = analysis.analyze_scan("v87", diag, points, sources, sample_step=1)
        self.assertEqual("few_historical_frames", with_motion["pose_motion_status"])
        self.assertEqual(2, with_motion["matched_depth_pose_records"])
        self.assertEqual(0.057, with_motion["camera_translation_delta_median_m"])
        self.assertEqual(0.003, with_motion["camera_forward_delta_p95_deg"] / 1000, 5)

    def test_invalid_pose_motion_is_not_accepted(self):
        diag, points, sources = sample_record()
        suffix = (
            ",nearest_camera_frame_timestamp_ns,nearest_camera_gap_ms,"
            "camera_translation_delta_m,camera_forward_delta_deg"
        )
        diag = diag.replace(HEADER, HEADER + suffix)
        rows = diag.splitlines()
        for i, line in enumerate(rows):
            if line.startswith("100,"):
                rows[i] += ",100,101.0,0.01,1.0"  # exceeds allowed 80ms
            elif line.startswith("200,"):
                rows[i] += ",200,0.0,-0.20,1.0"  # invalid negative motion
        value = analysis.analyze_scan("invalid", "\n".join(rows), points, sources)
        self.assertEqual("not_recorded", value["pose_motion_status"])
        self.assertEqual(0, value["matched_depth_pose_records"])

    def test_zip_replay_does_not_need_camera_photo(self):
        diag, points, sources = sample_record()
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/"scan.zip"
            with zipfile.ZipFile(p, "w") as z:
                z.writestr("Session/Putt_001/Scan_01/collector_diagnostics.txt", diag)
                z.writestr("Session/Putt_001/Scan_01/precision_depth_points.csv", points)
                z.writestr("Session/Putt_001/Scan_01/precision_depth_sources.csv", sources)
                z.writestr("Session/Putt_001/Scan_01/camera.jpg", b"not a real JPEG")
            rows=list(analysis.archive_rows(p,sample_step=1))
            self.assertEqual(1,len(rows))
            self.assertEqual("geometry_ready", rows[0]["status"])


if __name__ == "__main__":
    unittest.main()
