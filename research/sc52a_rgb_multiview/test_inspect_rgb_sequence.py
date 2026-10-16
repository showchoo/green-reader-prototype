import csv
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from inspect_rgb_sequence import evaluate_zip

FIELDS = ("index,ar_frame_timestamp_ns,cpu_image_timestamp_ns,"
          "android_camera_timestamp_ns,width,height,fx,fy,cx,cy,"
          "intrinsic_width,intrinsic_height,"
          "camera_tx,camera_ty,camera_tz,"
          "camera_qx,camera_qy,camera_qz,camera_qw,"
          "sensor_tx,sensor_ty,sensor_tz,"
          "sensor_qx,sensor_qy,sensor_qz,sensor_qw,"
          "ball_world_x,ball_world_y,ball_world_z,"
          "cup_world_x,cup_world_y,cup_world_z,tracking")

def create_zip(path, num=16, movement=.24, skip=None, image_delta_ns=0):
    prefix="Putt_001/Scan_01_20261016_134000"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr(prefix+"/rgb_capture_status.json",
                   json.dumps({"jpeg_saved":num,"slope_certified":False}))
        out=io.StringIO()
        writer=csv.writer(out)
        writer.writerow(FIELDS.split(","))
        for i in range(num):
            row=[str(i+1),str(100_000_000_000+i*125_000_000),
                 str(100_000_000_000+i*125_000_000+image_delta_ns),
                 str(100_000_000_000+i*125_000_000),
                 "1920","1080","1300","1300","960","540","1920","1080",
                 str(movement*i/max(1,num-1)),"0.7","0",
                 "0","0","0","1"]+[""]*7+["0","0","0","0","0","-1","TRACKING"]
            assert len(row)==len(FIELDS.split(","))
            writer.writerow(row)
            if skip != i+1:
                z.writestr(prefix+"/rgb_%04d.jpg"%(i+1),b"\xff\xd8\xff\xd9")
        z.writestr(prefix+"/rgb_frames.csv",out.getvalue())


class RgbResearchArchiveTest(unittest.TestCase):
    def run_case(self, **kwargs):
        with tempfile.TemporaryDirectory() as d:
            file=Path(d)/"session.zip"
            create_zip(file,**kwargs)
            return evaluate_zip(file)["scans"][0]

    def test_complete_synchronized_sequence_passes_research_readiness(self):
        r=self.run_case()
        self.assertEqual(r["status"],"READY_FOR_OFFLINE_MULTIVIEW_ATTEMPT")
        self.assertEqual(r["frame_count"],16)
        self.assertAlmostEqual(r["arcore_vio_travel_m"],.24,places=3)
        self.assertFalse(r["metric_slope_certified"])

    def test_missing_image_never_passes(self):
        r=self.run_case(skip=4)
        self.assertEqual(r["status"],"INSUFFICIENT_OR_INVALID_RESEARCH_CAPTURE")
        self.assertEqual(r["missing_jpeg_indices"],[4])

    def test_high_timestamp_delta_never_passes(self):
        r=self.run_case(image_delta_ns=80_000_000)
        self.assertEqual(r["status"],"INSUFFICIENT_OR_INVALID_RESEARCH_CAPTURE")
        self.assertEqual(r["max_frame_vs_image_timestamp_delta_ms"],80)

    def test_low_motion_does_not_claim_depth(self):
        r=self.run_case(movement=.03)
        self.assertEqual(r["status"],"INSUFFICIENT_OR_INVALID_RESEARCH_CAPTURE")
        self.assertFalse(r["metric_slope_certified"])

    def test_short_burst_requires_more_frames(self):
        r=self.run_case(num=6)
        self.assertEqual(r["status"],"INSUFFICIENT_OR_INVALID_RESEARCH_CAPTURE")


if __name__=="__main__":
    unittest.main()
