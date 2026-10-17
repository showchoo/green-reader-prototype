import csv
import io
import json
import struct
import tempfile
import unittest
import zipfile
from pathlib import Path

from inspect_camera2_depth16 import decode_depth16, inspect_zip


def build_zip(p, ranges=None, crop=False, frame_count=4):
    root="Putt_000/Scan_01_DEPTH16"
    w,h=12,12
    samples = ranges or [1400]*w*h
    with zipfile.ZipFile(p,"w") as z:
        status=dict(width=w,height=h,frame_count=frame_count,
                    stop_reason="max_frames",first_error="")
        calibration=dict(width=w,height=h,camera_id="4",
                         lens_intrinsic_calibration=[40,40,6,6,0],
                         lens_pose_rotation=[0,0,0,1],
                         lens_pose_translation=[0,0,0])
        z.writestr(root+"/camera2_depth_summary.json",json.dumps(status))
        z.writestr(root+"/camera2_calibration.json",json.dumps(calibration))
        dest=io.StringIO()
        writer=csv.writer(dest)
        writer.writerow("index,image_timestamp_ns,width,height")
        for i in range(1,frame_count+1):
            writer.writerow([i,i*100000000,w,h])
            if not(crop and i==3):
                bytes_=b"".join(struct.pack('<H',x) for x in samples)
                z.writestr(root+"/depth_%04d.bin"%i,bytes_)
        z.writestr(root+"/camera2_depth_frames.csv",dest.getvalue())


class RawDepth16Test(unittest.TestCase):
    def test_mm_and_high_confidence_codes(self):
        raw=struct.pack("<HHHH",1500,1500|(1<<13),
                        1600|(7<<13),0)
        d=decode_depth16(raw,2,2)
        self.assertEqual(d["median_mm"],1500)
        self.assertEqual(d["valid_fraction"],.75)
        self.assertEqual(d["min_mm"],1500)
        self.assertEqual(d["max_mm"],1600)
        self.assertEqual(d["invalid_conf_fraction_of_nonzero"],round(1/3,4))
        self.assertEqual(d["high_conf_fraction_of_nonzero"],round(2/3,4))

    def test_invalid_bytes_rejected(self):
        with self.assertRaises(ValueError):
            decode_depth16(b"\x00"*3,2,2)

    def check(self,**kwargs):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"session.zip"
            build_zip(path,**kwargs)
            return inspect_zip(path)["scans"][0]

    def test_valid_actual_format_is_not_accuracy_proof(self):
        report=self.check()
        self.assertEqual(report["status"],"DIRECT_DEPTH16_RANGE_FRAMES_CAPTURED")
        self.assertFalse(report["metric_slope_certified"])
        self.assertFalse(report["range_sensor_identity_tof_verified"])
        self.assertEqual(report["camera_id"],"4")
        self.assertEqual(report["center_range_spread_mm"],0.0)

    def test_missing_frame_fails_closed(self):
        report=self.check(crop=True)
        self.assertEqual(report["status"],"MALFORMED_OR_MISSING_DEPTH16_DATA")

    def test_empty_ranges_not_useful(self):
        report=self.check(ranges=[0]*144)
        self.assertEqual(report["status"],"DEPTH_FORMAT_AVAILABLE_BUT_NO_USEFUL_RANGE")


if __name__=="__main__":
    unittest.main()
