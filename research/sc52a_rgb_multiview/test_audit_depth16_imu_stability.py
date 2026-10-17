"""Synthetic ZIP regression tests: no private measurements or images."""
import csv
import io
import json
import math
import tempfile
import unittest
import zipfile
from pathlib import Path

from audit_depth16_imu_stability import analyze, compare, gyro_integral

ROOT="Session_SYNTHETIC/Putt_000/Scan_01_DEPTH16/"
TYPES=("gravity","accelerometer","gyroscope","gyroscope_uncalibrated")

def csv_text(keys,rows):
    out=io.StringIO()
    writer=csv.DictWriter(out,fieldnames=keys)
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue()

def fixture(path,source=1,gyro=True,move=False,broken=False,disorder=False,camera="4",shift=0):
    t0=2_000_000_000
    frames=[{"image_timestamp_ns":t0+i*200_000_000,
             "valid_pixels":0 if i==0 else 100,
             "confident_pixels":0 if i==0 else 1} for i in range(12)]
    readings=[];counts={}
    for kind in TYPES:
        n=151 if kind!="gyroscope" or gyro else 0
        counts[kind]=n
        for i in range(n):
            t=1_500_000_000+i*20_000_000
            if disorder and kind=="accelerometer" and i==30:t-=60_000_000
            x=(0.7 if i<5 else shift) if kind in ("gravity","accelerometer") else (0.1 if move else 0.01)
            readings.append({"sensor_type":kind,"sensor_timestamp_ns":t,
                             "callback_elapsed_ns":t+1_000_000,"x":x,"y":0,
                             "z":9.8 if kind in ("gravity","accelerometer") else 0,
                             "bias_x":"","bias_y":"","bias_z":"","accuracy":3})
    if broken:readings[0]["x"]="nan"
    meta={"camera_timestamp_source":source,
          "camera_vs_sensor_timestamp_comparable":source==1,
          "sensor_listener_registered":{k:v>0 for k,v in counts.items()},
          "per_sensor_sample_count":counts,
          "per_sensor_cap_dropped":{k:0 for k in counts},
          "per_sensor_out_of_order_dropped":{k:0 for k in counts}}
    files={
        "camera2_sensor_events.csv":csv_text(("sensor_type","sensor_timestamp_ns",
          "callback_elapsed_ns","x","y","z","bias_x","bias_y","bias_z","accuracy"),readings),
        "camera2_depth_frames.csv":csv_text(("image_timestamp_ns","valid_pixels","confident_pixels"),frames),
        "camera2_gravity.csv":"sensor_timestamp_ns,gx,gy,gz\n",
        "camera2_sensor_metadata.json":json.dumps(meta),
        "camera2_calibration.json":json.dumps({"camera_id":camera,"width":640,"height":480,
                                              "sensor_timestamp_source":source}),
        "camera2_depth_summary.json":json.dumps({"frame_count":12}),
        "record_identity.json":"{}",
    }
    with zipfile.ZipFile(path,"w") as z:
        for name,value in files.items():z.writestr(ROOT+name,value)

class WindowTests(unittest.TestCase):
    def test_startup_outlier_not_silently_called_camera_motion(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"a.zip";fixture(p)
            r=analyze(p);g=r["directional_streams"]["gravity"]
            self.assertGreater(g["startup_first_five_vs_capture_end_deg"],3)
            self.assertAlmostEqual(g["capture_first_half_second_vs_last_half_second_deg"],0,places=4)
            self.assertEqual(r["nonempty_depth_frames"],11)
            self.assertFalse(r["camera_physical_motion_proven"])
            self.assertFalse(r["absolute_slope_accuracy_proven"])

    def test_unknown_camera_clock_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"unknown.zip";fixture(p,source=0)
            r=analyze(p)
            self.assertFalse(r["camera_sensor_timebases_comparable"])
            self.assertIsNone(r["directional_streams"]["gravity"]["capture_end_median_xyz"])
            self.assertIsNone(r["gyro_during_capture"]["gyroscope"])

    def test_missing_gyro_evidence_cannot_approve_motion(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"missing.zip";fixture(p,gyro=False)
            r=analyze(p)
            self.assertFalse(r["raw_motion_diagnostics_available"])
            self.assertIsNone(r["gyro_during_capture"]["gyroscope"])
            self.assertFalse(r["camera_physical_motion_proven"])

    def test_gyro_integral_units_and_uncalibrated_bias_proxy(self):
        rows=[{"sensor_timestamp_ns":str(1_000_000_000+i*100_000_000),
               "x":"0.1","y":"0","z":"0"} for i in range(20)]
        x=gyro_integral(rows,1_000_000_000,2_000_000_000)
        self.assertAlmostEqual(x["raw_integral_norm_deg"],math.degrees(0.1),places=4)
        self.assertAlmostEqual(x["bias_proxy_adjusted_integral_norm_deg"],0,places=4)

    def test_corrupted_or_out_of_order_stream_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            for case,options in (("nan",{"broken":True}),("order",{"disorder":True})):
                with self.subTest(case=case):
                    p=Path(d)/(case+".zip");fixture(p,**options)
                    with self.assertRaises(ValueError):analyze(p)

    def test_pair_reports_difference_without_certifying_slope(self):
        with tempfile.TemporaryDirectory() as d:
            a,b=Path(d)/"a.zip",Path(d)/"b.zip"
            fixture(a);fixture(b,shift=0.04)
            r=compare(a,b)
            self.assertTrue(r["camera_geometry_compatible"])
            self.assertGreater(r["cross_session_capture_end_direction_difference_deg"]["gravity"],0.1)
            self.assertFalse(r["camera_mount_pose_independently_verified"])
            self.assertFalse(r["absolute_slope_accuracy_proven"])

    def test_incompatible_camera_geometry_blocks_pair_direction(self):
        with tempfile.TemporaryDirectory() as d:
            a,b=Path(d)/"a.zip",Path(d)/"b.zip"
            fixture(a);fixture(b,camera="5")
            r=compare(a,b)
            self.assertFalse(r["camera_geometry_compatible"])
            self.assertNotIn("cross_session_capture_end_direction_difference_deg",r)

if __name__=="__main__":unittest.main()
