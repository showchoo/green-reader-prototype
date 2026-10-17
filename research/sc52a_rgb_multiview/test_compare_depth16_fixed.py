"""Synthetic archive comparison: stability is not absolute accuracy."""
import csv
import io
import json
import struct
import tempfile
import unittest
import zipfile
from pathlib import Path

from compare_depth16_fixed import read_session, compare


def synthetic_session(path, offsets, code=2, motion=0., corrupt=False):
    assert len(offsets)>=4
    root="Putt_000/Scan_01_DEPTH16"
    w,h=24,24
    with zipfile.ZipFile(path,"w") as z:
        z.writestr(root+"/camera2_calibration.json",json.dumps({
            "camera_id":"4","width":w,"height":h}))
        z.writestr(root+"/camera2_depth_summary.json",json.dumps({
            "frame_count":len(offsets)+1,"width":w,"height":h}))
        rows=io.StringIO()
        writer=csv.writer(rows)
        writer.writerow(["index","image_timestamp_ns","width","height"])
        for index,shift in enumerate([None]+list(offsets),start=1):
            writer.writerow([index,index*200000000,w,h])
            packed=(0 if shift is None else int(1000+shift)|(code<<13))
            raw=struct.pack("<H",packed)*w*h
            if corrupt and index==3:raw=raw[:100]
            z.writestr(root+"/depth_%04d.bin"%index,raw)
        z.writestr(root+"/camera2_depth_frames.csv",rows.getvalue())
        grav=io.StringIO()
        gw=csv.writer(grav)
        gw.writerow(["sensor_timestamp_ns","gx","gy","gz"])
        for i in range(1,len(offsets)+2):
            gw.writerow([i*200000000,0.,0.+motion*i,9.8])
        z.writestr(root+"/camera2_gravity.csv",grav.getvalue())


class FixedDepth16ComparisonTests(unittest.TestCase):
    def test_zero_drift_fixed_readout_not_certified(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"fixed.zip"
            synthetic_session(p,[0,0,0,0,0,0])
            x=read_session(p)
            self.assertEqual(x["frames_nonempty"],6)
            self.assertEqual(x["same_image_pixel_span_p50_mm"],0)
            self.assertEqual(x["center_100x100_median_range_span_mm"],0)
            self.assertEqual(x["depth_nonzero_confidence_counts"][2],24*24*6)
            self.assertFalse(x["metric_slope_certified"])

    def test_steady_common_shift_is_separate_from_pixel_span(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"moving.zip"
            synthetic_session(p,[0,1,2,3,4,5])
            x=read_session(p)
            self.assertEqual(x["same_image_pixel_span_p50_mm"],5.)
            self.assertEqual(x["early_late_same_image_pixel_shift_median_mm"],1.)
            self.assertFalse(x["metric_slope_certified"])

    def test_no_camera_mix_and_no_false_product_pass(self):
        with tempfile.TemporaryDirectory() as d:
            a=Path(d)/"handheld.zip"; b=Path(d)/"fixed.zip"
            synthetic_session(a,[0,2,4,6,8,10],motion=.02)
            synthetic_session(b,[0,0,1,0,0,1],motion=.0001)
            out=compare(a,b)
            self.assertGreater(out["handheld"]["recorded_gravity_direction_max_change_degrees"],
                               out["fixed"]["recorded_gravity_direction_max_change_degrees"])
            self.assertFalse(out["commercial_putting_accuracy_certified"])
            self.assertTrue(out["comparison_is_not_calibrated_absolute_accuracy"])

    def test_corrupt_frame_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"broken.zip"
            synthetic_session(p,[0,0,0,0,0,0],corrupt=True)
            with self.assertRaises(ValueError):
                read_session(p)


if __name__=="__main__":
    unittest.main()
