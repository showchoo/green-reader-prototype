"""Synthetic paired-camera DEPTH16 experiments only; no private recordings."""
import csv
import io
import json
import math
from pathlib import Path
import tempfile
import unittest
import zipfile

from audit_paired_elevated_board import analyze_pair

ROOT="Session_SYNTH/Putt_000/Scan_01_DEPTH16/"
WIDTH,HEIGHT=160,120
INTR=[135.0,135.0,WIDTH/2,HEIGHT/2,0.0]
TYPES=("gravity","accelerometer","gyroscope","gyroscope_uncalibrated")

def csv_text(fields,rows):
    s=io.StringIO();w=csv.DictWriter(s,fieldnames=fields)
    w.writeheader();w.writerows(rows)
    return s.getvalue()

def make_zip(path,board=False,global_shift=0,motion=0,empty_holes=False,
             camera="4",source=1):
    files={};rows=[]
    for frame in range(1,6):
        data=[];valid=0
        for y in range(HEIGHT):
            for x in range(WIDTH):
                raised=(40<=x<120 and 28<=y<92)
                z=1200+global_shift-(50 if board and raised else 0)
                if empty_holes and x<WIDTH*.85:z=0
                if z>0:
                    radial=z*math.sqrt(1+((x-INTR[2])/INTR[0])**2+((y-INTR[3])/INTR[1])**2)
                    packed=(3<<13)|round(radial)
                    valid+=1
                else:packed=0
                data.append(packed)
        files[f"depth_{frame:04d}.bin"]=b"".join(
            x.to_bytes(2,"little") for x in data)
        rows.append({"index":frame,"image_timestamp_ns":2_000_000_000+(frame-1)*200_000_000,
                     "width":WIDTH,"height":HEIGHT,"valid_pixels":valid,
                     "confident_pixels":0,"coverage":f"{valid/(WIDTH*HEIGHT):.6f}"})
    calibration={"width":WIDTH,"height":HEIGHT,"camera_id":camera,
                 "lens_intrinsic_calibration":INTR,"lens_distortion":[0,0,0,0,0],
                 "sensor_orientation_degrees":90,"lens_pose_translation":[0,0,0],
                 "lens_pose_rotation":[0,0,0,1],
                 "sensor_timestamp_source":source}
    readings=[]
    for kind in TYPES:
        for i in range(160):
            t=1_500_000_000+i*20_000_000
            x=(motion if kind in ("gravity","accelerometer") else 0.0002)
            readings.append({"sensor_type":kind,"sensor_timestamp_ns":t,
                             "callback_elapsed_ns":t+100_000,
                             "x":x,"y":0,"z":9.8 if kind in ("gravity","accelerometer") else 0,
                             "bias_x":"","bias_y":"","bias_z":"","accuracy":3})
    counts={kind:160 for kind in TYPES}
    files["camera2_calibration.json"]=json.dumps(calibration)
    files["camera2_depth_summary.json"]=json.dumps({
        "width":WIDTH,"height":HEIGHT,"frame_count":5})
    files["camera2_depth_frames.csv"]=csv_text(
        ("index","image_timestamp_ns","width","height","valid_pixels",
         "confident_pixels","coverage"),rows)
    files["camera2_sensor_events.csv"]=csv_text(
        ("sensor_type","sensor_timestamp_ns","callback_elapsed_ns",
         "x","y","z","bias_x","bias_y","bias_z","accuracy"),readings)
    files["camera2_sensor_metadata.json"]=json.dumps({
        "camera_timestamp_source":source,
        "camera_vs_sensor_timestamp_comparable":source==1,
        "per_sensor_sample_count":counts,
        "sensor_listener_registered":{k:True for k in TYPES},
        "per_sensor_cap_dropped":{k:0 for k in TYPES},
        "per_sensor_out_of_order_dropped":{k:0 for k in TYPES}})
    files["camera2_gravity.csv"]="sensor_timestamp_ns,gx,gy,gz,accuracy\n"
    files["record_identity.json"]="{}"
    with zipfile.ZipFile(path,"w",zipfile.ZIP_DEFLATED) as z:
        for name,data in files.items():z.writestr(ROOT+name,data)

class PairedBoardTests(unittest.TestCase):
    def test_50mm_board_produces_uncertified_contiguous_candidate(self):
        with tempfile.TemporaryDirectory() as d:
            e,b=Path(d)/"empty.zip",Path(d)/"board.zip"
            make_zip(e);make_zip(b,board=True)
            r=analyze_pair(e,b)
            self.assertEqual(r["status"],"unverified_board_like_depth_change_candidate",r)
            self.assertGreater(r["largest_component_share"],.9)
            self.assertAlmostEqual(r["depth_change_median_optical_z_mm"],-50,delta=2)
            self.assertFalse(r["board_identity_verified"])
            self.assertIsNone(r["measured_board_height_mm"])
            self.assertFalse(r["physical_grade_accuracy_certified"])
            self.assertFalse(r["camera_translation_independently_verified"])

    def test_identical_scene_fails_without_false_board(self):
        with tempfile.TemporaryDirectory() as d:
            e,b=Path(d)/"e.zip",Path(d)/"b.zip"
            make_zip(e);make_zip(b)
            r=analyze_pair(e,b)
            self.assertEqual(r["status"],"unresolved")
            self.assertEqual(r["reason"],"candidate_fraction_not_plausible")

    def test_camera_translation_like_global_shift_fails(self):
        with tempfile.TemporaryDirectory() as d:
            e,b=Path(d)/"e.zip",Path(d)/"b.zip"
            make_zip(e);make_zip(b,global_shift=-50)
            r=analyze_pair(e,b)
            self.assertEqual(r["reason"],"unmodified_background_not_observed")

    def test_imu_orientation_change_blocks_comparison(self):
        with tempfile.TemporaryDirectory() as d:
            e,b=Path(d)/"e.zip",Path(d)/"b.zip"
            make_zip(e);make_zip(b,board=True,motion=0.6)
            r=analyze_pair(e,b)
            self.assertEqual(r["reason"],"camera_orientation_drift_cannot_be_excluded")
            self.assertGreater(r["gravity_end_direction_delta_deg"],.15)

    def test_unknown_camera_clock_cannot_certify_alignment(self):
        with tempfile.TemporaryDirectory() as d:
            e,b=Path(d)/"e.zip",Path(d)/"b.zip"
            make_zip(e,source=0);make_zip(b,board=True,source=0)
            self.assertEqual(analyze_pair(e,b)["reason"],"imu_evidence_insufficient")

    def test_distinct_camera_identity_blocks_pair(self):
        with tempfile.TemporaryDirectory() as d:
            e,b=Path(d)/"e.zip",Path(d)/"b.zip"
            make_zip(e,camera="4");make_zip(b,board=True,camera="5")
            self.assertEqual(analyze_pair(e,b)["reason"],"camera_intrinsic_or_extrinsic_mismatch")

    def test_missing_depth_blocks_board_candidate(self):
        with tempfile.TemporaryDirectory() as d:
            e,b=Path(d)/"e.zip",Path(d)/"b.zip"
            make_zip(e);make_zip(b,board=True,empty_holes=True)
            r=analyze_pair(e,b)
            self.assertEqual(r["reason"],"insufficient_valid_common_depth")

    def test_same_file_cannot_be_empty_and_board(self):
        with tempfile.TemporaryDirectory() as d:
            e=Path(d)/"e.zip";make_zip(e)
            self.assertEqual(analyze_pair(e,e)["reason"],"same_archive_for_both_roles")

if __name__=="__main__":unittest.main()
