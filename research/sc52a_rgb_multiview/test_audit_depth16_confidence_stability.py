"""Synthetic DEPTH16 archive regression tests; no private camera pixels."""
import csv
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from audit_depth16_confidence_stability import audit,pixels,percentile,frame_summary

ROOT="Session_SYNTHETIC/Putt_000/Scan_01_DEPTH16/"
W,H=16,8

def csv_text(fields,rows):
    f=io.StringIO()
    writer=csv.DictWriter(f,fieldnames=fields)
    writer.writeheader();writer.writerows(rows)
    return f.getvalue()

def encoded(distance,code):
    return (code<<13)|(distance & 8191)

def raw(values):
    return b"".join(int(v).to_bytes(2,"little") for v in values)

def fixture(path,camera="4",conf=3,shift=0,bad_csv=False,
            bad_size=False,missing=False,intrinsic_shift=0,wrong_frame_count=False):
    frames=[[0]*(W*H),[encoded(1000+shift,conf)]*(W*H),
            [encoded(1002+shift,conf)]*(W*H)]
    rows=[]
    for index,data in enumerate(frames,1):
        s=frame_summary(data,W,H)
        rows.append({"index":index,"image_timestamp_ns":str(index*200_000_000+1_000_000_000),
                     "width":W,"height":H,
                     "valid_pixels":s["valid_pixels"]+(1 if bad_csv and index==2 else 0),
                     "confident_pixels":s["confident_pixels"],
                     "coverage":f"{s['valid_pixels']/(W*H):.6f}"})
    files={
        "camera2_calibration.json":json.dumps({"width":W,"height":H,"camera_id":camera,
              "sensor_orientation_degrees":90,
              "lens_intrinsic_calibration":[12+intrinsic_shift,13,8,4,0]}),
        "camera2_depth_summary.json":json.dumps({"width":W,"height":H,
                                      "frame_count":4 if wrong_frame_count else 3}),
        "camera2_depth_frames.csv":csv_text(("index","image_timestamp_ns","width",
              "height","valid_pixels","confident_pixels","coverage"),rows),
        "record_identity.json":"{}"}
    for index,frame in enumerate(frames,1):
        if missing and index==2:continue
        blob=raw(frame)
        if bad_size and index==2:blob=blob[:-2]
        files[f"depth_{index:04d}.bin"]=blob
    with zipfile.ZipFile(path,"w",zipfile.ZIP_DEFLATED) as z:
        for name,blob in files.items():z.writestr(ROOT+name,blob)

class DepthEvidenceTests(unittest.TestCase):
    def test_android_depth16_confidence_codes(self):
        for code in range(8):
            with self.subTest(code=code):
                s=frame_summary([encoded(1200,code)]*(W*H),W,H)
                self.assertEqual(s["valid_pixels"],128)
                self.assertEqual(s["confident_pixels"],128 if code==0 or code>=5 else 0)
                self.assertEqual(s["confidence_code_counts_valid"][code],128)

    def test_invalid_range_not_counted_even_when_code_zero(self):
        s=frame_summary([0]*(W*H),W,H)
        self.assertEqual((s["valid_pixels"],s["confident_pixels"]),(0,0))

    def test_low_confidence_stability_not_metric_accuracy(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"one.zip";fixture(path)
            s=audit(path)["sessions"][0]
            self.assertEqual(s["nonempty_frames"],2)
            self.assertEqual(s["confidence_code_counts_valid"][3],2*W*H)
            self.assertEqual(s["roi"]["center"]["median_first_last_signed_difference_mm"],2)
            self.assertEqual(s["roi"]["center"]["median_pixel_mad_mm"],1)
            self.assertFalse(s["certified_metric_grade_available"])

    def test_pair_uses_signed_depth_deltas_not_unsigned_wrap(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,b=Path(tmp)/"a.zip",Path(tmp)/"b.zip"
            fixture(a,shift=7000,conf=2);fixture(b,shift=0,conf=2)
            result=audit(a,b)
            self.assertEqual(result["pair"]["roi"]["center"]["median_signed_difference_mm"],-7000)
            self.assertEqual(result["pair"]["roi"]["center"]["median_abs_difference_mm"],7000)
            self.assertFalse(result["physical_grade_accuracy_certified"])

    def test_metadata_mismatch_disables_pair(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,b=Path(tmp)/"a.zip",Path(tmp)/"b.zip"
            fixture(a);fixture(b,intrinsic_shift=.02)
            p=audit(a,b)["pair"]
            self.assertFalse(p["geometry_metadata_compatible"])
            self.assertEqual(p["roi"],{})

    def test_bad_csv_missing_bin_raw_size_and_summary_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            for kind,opts in (("counter",{"bad_csv":True}),
                              ("raw_size",{"bad_size":True}),
                              ("missing",{"missing":True}),
                              ("count",{"wrong_frame_count":True})):
                with self.subTest(kind=kind):
                    path=Path(tmp)/(kind+".zip");fixture(path,**opts)
                    with self.assertRaises(ValueError):audit(path)

    def test_little_endian_and_percentiles(self):
        self.assertEqual(list(pixels(raw([0x1234,0x2000,0xffff,0]),2,2)),
                         [0x1234,0x2000,0xffff,0])
        self.assertEqual(percentile([1,2,3,4],50),2.5)
        self.assertEqual(percentile([2],95),2)
        self.assertIsNone(percentile([],50))

if __name__=="__main__":unittest.main()
