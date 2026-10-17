"""Synthetic-only packed Camera2 DEPTH16 confidence/repeatability regressions."""
import csv
import io
import json
import struct
import tempfile
import unittest
import zipfile
from pathlib import Path
import numpy as np

from audit_depth16_confidence import report, decode, confidence_fraction


def make_archive(filename, codes=(3,3,3), drop_index=None, empty_first=True):
    base="Putt_000/Scan_01_DEPTH16"
    w,h=12,12
    with zipfile.ZipFile(filename,"w") as z:
        z.writestr(base+"/camera2_calibration.json",json.dumps(dict(
            width=w,height=h,camera_id="4",
            lens_intrinsic_calibration=[50,50,6,6,0],
            lens_pose_translation=[0,0,0])))
        z.writestr(base+"/camera2_depth_summary.json",
                   json.dumps(dict(frame_count=4)))
        z.writestr(base+"/camera2_gravity.csv",
                   "sensor_timestamp_ns,gx,gy,gz\n"
                   "100000000,0,0,9.8\n200000000,0,0,9.8\n"
                   "300000000,0,0,9.8\n400000000,0,0,9.8\n")
        rows=io.StringIO()
        wtr=csv.writer(rows)
        wtr.writerow(["index","image_timestamp_ns","width","height"])
        for i in range(1,5):
            wtr.writerow([i, i*100000000,w,h])
            code=codes[i-2] if i>1 else 0
            radius=1000+i
            packed=0 if i==1 and empty_first else radius|(code<<13)
            if i!=drop_index:
                z.writestr(base+"/depth_%04d.bin"%i,
                    struct.pack("<H",packed)*w*h)
        z.writestr(base+"/camera2_depth_frames.csv",rows.getvalue())


class ConfidenceDecodeTests(unittest.TestCase):
    def test_bit_order(self):
        raw=struct.pack("<HHH",1028|(2<<13),1030|(3<<13),0)
        mm,c=decode(raw,3,1)
        self.assertEqual(mm.tolist(),[[1028,1030,0]])
        self.assertEqual(c.tolist(),[[2,3,0]])

    def test_android_confidence_mapping(self):
        scores=confidence_fraction(np.arange(8))
        self.assertEqual(scores[0],1.)
        self.assertEqual(scores[1],0.)
        self.assertAlmostEqual(scores[2],1/7)
        self.assertAlmostEqual(scores[3],2/7)
        self.assertAlmostEqual(scores[4],3/7)
        self.assertEqual(scores[5] >= .5,True)

    def case(self,**options):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"session.zip"
            make_archive(p,**options)
            return report(p)["scans"][0]

    def test_only_low_confidence_cannot_certify_grade(self):
        x=self.case()
        self.assertEqual(x["nonempty_frames"],3)
        self.assertEqual(x["empty_frame_ids"],[1])
        self.assertEqual(x["status"],"VALID_RANGE_BUT_ZERO_HIGH_CONFIDENCE")
        self.assertEqual(x["confidence_ge_50pct_count"],0)
        self.assertFalse(x["putting_grade_certified"])
        self.assertEqual(x["same_pixel_temporal_span_median_mm"],2)
        self.assertEqual(x["gravity_direction_change_max_degrees"],0)

    def test_high_confidence_still_not_accuracy_certification(self):
        x=self.case(codes=(0,0,0))
        self.assertGreater(x["confidence_ge_50pct_count"],0)
        self.assertEqual(x["status"],"RANGE_CAPTURED_EXACT_SLOPE_UNVERIFIED")
        self.assertFalse(x["putting_grade_certified"])

    def test_missing_frame_fails(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"session.zip"
            make_archive(p,drop_index=2)
            with self.assertRaises(KeyError):
                report(p)

    def test_bad_depth_bytes_fails(self):
        with self.assertRaises(ValueError):
            decode(b"\x00",1,1)


if __name__=="__main__":
    unittest.main()
