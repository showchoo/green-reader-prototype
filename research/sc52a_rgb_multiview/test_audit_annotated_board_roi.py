"""Synthetic/manual polygon audit tests. No user camera pixels in repository."""
import csv
import io
import json
import math
from pathlib import Path
import tempfile
import unittest
import zipfile

from audit_annotated_board_roi import (
    run,sha256,validate_corners,angle_deg
)

ROOT="Session_SYNTHETIC/Putt_000/Scan_01_DEPTH16/"
WIDTH,HEIGHT=320,240
CORNERS=[[54,44],[266,44],[266,196],[54,196]]

def csv_text(fields,rows):
    t=io.StringIO();w=csv.DictWriter(t,fieldnames=fields)
    w.writeheader();w.writerows(rows);return t.getvalue()

def fixture(path,tilt=0.0,noise=False,invalid=False,camera="4",
            intrinsics=True,frame_count=5):
    fx,fy,cx,cy=260.,260.,WIDTH/2,HEIGHT/2
    rows=[];files={}
    for frame_index in range(1,frame_count+1):
        p=[];valid=0
        for y in range(HEIGHT):
            for x in range(WIDTH):
                nx=(x-cx)/fx;ny=(y-cy)/fy
                # A planar board inside the externally annotated inner box;
                # background lies 200 mm behind it.
                board=50<=x<=270 and 40<=y<=200
                inv_z=(1.0+tilt*nx)/1000.0
                z=1/inv_z if board else 1200.0
                if noise and board:z+=(frame_index%2)*(x%5)*10
                radial=z*math.sqrt(1+nx*nx+ny*ny)
                distance=round(radial)
                if invalid and board and y>100 and x>110:distance=0
                code=3
                packed=(code<<13)|int(distance) if distance else 0
                p.append(packed);valid+=distance!=0
        blob=b"".join(int(v).to_bytes(2,"little") for v in p)
        files[f"depth_{frame_index:04d}.bin"]=blob
        rows.append({"index":frame_index,"image_timestamp_ns":frame_index*200000000,
                     "width":WIDTH,"height":HEIGHT,"valid_pixels":valid,
                     "confident_pixels":0,
                     "coverage":f"{valid/(WIDTH*HEIGHT):.6f}"})
    calibration={"width":WIDTH,"height":HEIGHT,"camera_id":camera,
                 "sensor_orientation_degrees":90}
    if intrinsics:calibration["lens_intrinsic_calibration"]=[fx,fy,cx,cy,0]
    files["camera2_calibration.json"]=json.dumps(calibration)
    files["camera2_depth_summary.json"]=json.dumps({
        "width":WIDTH,"height":HEIGHT,"frame_count":frame_count})
    files["camera2_depth_frames.csv"]=csv_text(
        ("index","image_timestamp_ns","width","height","valid_pixels","confident_pixels","coverage"),rows)
    files["record_identity.json"]="{}"
    with zipfile.ZipFile(path,"w",zipfile.ZIP_DEFLATED) as z:
        for name,data in files.items():z.writestr(ROOT+name,data)

def manifest(path,entries):
    path.write_text(json.dumps({"schema_version":1,"sessions":entries}),encoding="utf-8")
    return path

def item(path,corners=None):
    return {"sha256":sha256(path),"source":"manual_depth_view",
            "corners_px":corners or CORNERS}

class BoardRoiTests(unittest.TestCase):
    def test_no_board_coordinates_gives_no_grade_even_with_depth(self):
        with tempfile.TemporaryDirectory() as d:
            a=Path(d)/"a.zip";fixture(a)
            r=run([a])
            self.assertEqual(r["sessions"][0]["reason"],"manual_four_corners_not_supplied")
            self.assertFalse(r["physical_grade_accuracy_certified"])

    def test_synthetic_planar_board_outputs_provisional_normal_only(self):
        with tempfile.TemporaryDirectory() as d:
            a=Path(d)/"a.zip";fixture(a,tilt=0.02)
            m=manifest(Path(d)/"roi.json",[item(a)])
            r=run([a],m)
            s=r["sessions"][0]
            self.assertEqual(s["status"],"provisional_annotated_roi_plane",s)
            self.assertGreaterEqual(s["frames_accepted"],3)
            self.assertLess(s["central_plane_rmse_mm"],2)
            self.assertTrue(s["low_vendor_confidence_warning"])
            self.assertFalse(s["board_identity_independently_verified"])
            self.assertFalse(s["absolute_slope_accuracy_certified"])
            self.assertFalse(r["physical_grade_accuracy_certified"])

    def test_two_images_show_apparent_normal_change_not_grade(self):
        with tempfile.TemporaryDirectory() as d:
            a,b=Path(d)/"a.zip",Path(d)/"b.zip"
            fixture(a);fixture(b,tilt=.02)
            m=manifest(Path(d)/"roi.json",[item(a),item(b)])
            r=run([a,b],m)
            self.assertTrue(r["camera_geometry_compatible"])
            self.assertGreater(r["apparent_normal_change_deg"],.8)
            self.assertLess(r["apparent_normal_change_deg"],1.5)
            self.assertIsNone(r["measured_board_slope_percent_points"])
            self.assertFalse(r["difference_is_physical_tilt_certified"])

    def test_annotation_not_bound_to_other_archive(self):
        with tempfile.TemporaryDirectory() as d:
            a=Path(d)/"a.zip";fixture(a)
            m=manifest(Path(d)/"wrong.json",[{"sha256":"0"*64,
                      "corners_px":CORNERS,"source":"manual_depth_view"}])
            # Unmatched manifest deliberately fails closed: no ROI attempted.
            r=run([a],m)
            self.assertEqual(r["sessions"][0]["status"],"unresolved")
            self.assertIsNone(r["sessions"][0].get("central_plane_rmse_mm"))

    def test_invalid_polygons_fail_validation(self):
        for p in (
            [[54,44],[266,196],[266,44],[54,196]],  # self-crossed
            [[54,44],[54,196],[266,196],[266,44]],  # inverse order
            [[0,0],[266,44],[266,196],[54,196]],    # edge
            [[54,44],[55,44],[55,45],[54,45]],      # tiny
            [[54,44],[266,44],[260,44],[54,196]],   # degenerate
        ):
            with self.subTest(p=p):
                with self.assertRaises(ValueError):
                    validate_corners(p,WIDTH,HEIGHT)

    def test_manual_polygon_does_not_guess_missing_calibration(self):
        with tempfile.TemporaryDirectory() as d:
            a=Path(d)/"a.zip";fixture(a,intrinsics=False)
            m=manifest(Path(d)/"roi.json",[item(a)])
            r=run([a],m)
            self.assertEqual(r["sessions"][0]["reason"],"lens_intrinsics_missing_or_invalid")

    def test_geometry_mismatch_blocks_paired_normal_claim(self):
        with tempfile.TemporaryDirectory() as d:
            a,b=Path(d)/"a.zip",Path(d)/"b.zip"
            fixture(a,camera="4");fixture(b,camera="5")
            m=manifest(Path(d)/"roi.json",[item(a),item(b)])
            r=run([a,b],m)
            self.assertFalse(r["camera_geometry_compatible"])
            self.assertIsNone(r["apparent_normal_change_deg"])

    def test_invalid_mask_prevents_provisional_plane(self):
        with tempfile.TemporaryDirectory() as d:
            a=Path(d)/"a.zip";fixture(a,invalid=True)
            m=manifest(Path(d)/"roi.json",[item(a)])
            r=run([a],m)
            self.assertEqual(r["sessions"][0]["status"],"unresolved",r)
            self.assertFalse(r["physical_grade_accuracy_certified"])

    def test_missing_or_wrong_manifest_provenance(self):
        with tempfile.TemporaryDirectory() as d:
            a=Path(d)/"a.zip";fixture(a)
            m=manifest(Path(d)/"roi.json",[item(a),item(a)])
            with self.assertRaises(ValueError):run([a],m)
            m=manifest(Path(d)/"roi.json",[
                {"sha256":sha256(a),"source":"web_inferred","corners_px":CORNERS}])
            with self.assertRaises(ValueError):run([a],m)

if __name__=="__main__":unittest.main()
