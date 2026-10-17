"""Synthetic depth-only board-identifiability regression suite.

No user images or measurements are fixtures. Even a perfect-looking isolated
rectangle has no independently verified board identity or metric-grade claim.
"""
import csv
import io
import json
import math
from pathlib import Path
import tempfile
import unittest
import zipfile

from audit_depth16_surface_identifiability import analyze_session,audit

W,H=128,96
ROOT="Session_SYNTHETIC/Putt_000/Scan_01_DEPTH16/"

def csv_text(cols,rows):
    out=io.StringIO();w=csv.DictWriter(out,fieldnames=cols);w.writeheader();w.writerows(rows)
    return out.getvalue()

def synthetic_zip(path,kind="rectangle",shift=0,metadata=True,missing_band=False):
    fx=100;fy=100;cx=W/2;cy=H/2
    files={}
    frame_rows=[]
    for j in range(1,6):
        pixels=[]
        valid=0
        for y in range(H):
            for x in range(W):
                board=(32<=x<96 and 24<=y<72)
                if kind=="rectangle":
                    z=1000+shift if board else 1250+shift
                elif kind=="flat":z=1000+shift
                elif kind=="smooth":
                    z=1000+.05*(x-cx)**2+.05*(y-cy)**2+shift
                elif kind=="masked":
                    z=1000 if board else 1250
                else:raise ValueError(kind)
                distance=round(z*math.sqrt(1+((x-cx)/fx)**2+((y-cy)/fy)**2))
                if kind=="masked" and 96<=x<104 and 24<=y<72 and missing_band:
                    distance=0
                packed=(3<<13)|distance if distance else 0
                pixels.append(packed);valid+=distance>0
        files[f"depth_{j:04d}.bin"]=b"".join(p.to_bytes(2,"little") for p in pixels)
        frame_rows.append(dict(index=j,image_timestamp_ns=j*200_000_000,
                               width=W,height=H,valid_pixels=valid,
                               confident_pixels=0,coverage=f"{valid/(W*H):.6f}"))
    cal={"width":W,"height":H,"camera_id":"4","sensor_orientation_degrees":90}
    if metadata:cal["lens_intrinsic_calibration"]=[fx,fy,cx,cy,0]
    files["camera2_calibration.json"]=json.dumps(cal)
    files["camera2_depth_summary.json"]=json.dumps({"width":W,"height":H,"frame_count":5})
    files["camera2_depth_frames.csv"]=csv_text(("index","image_timestamp_ns","width",
                                  "height","valid_pixels","confident_pixels","coverage"),frame_rows)
    files["record_identity.json"]="{}"
    with zipfile.ZipFile(path,"w",compression=zipfile.ZIP_DEFLATED) as z:
        for n,data in files.items():z.writestr(ROOT+n,data)

class IdentifiabilityTests(unittest.TestCase):
    def test_isolated_rectangle_is_only_patch_not_board(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"rectangle.zip";synthetic_zip(p)
            r=audit(p)["sessions"][0]
            self.assertEqual(r["status"],"isolated_depth_patch_candidate",r)
            self.assertFalse(r["semantic_board_identified"])
            self.assertFalse(r["slope_accuracy_certified"])
            self.assertFalse(r["surface_mask_released"])
            self.assertGreaterEqual(r["boundary_evidence"]["left"]["depth_step_at_least_35mm_fraction"],.65)

    def test_unbroken_flat_surface_refused(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"flat.zip";synthetic_zip(p,kind="flat")
            r=audit(p)["sessions"][0]
            self.assertEqual(r["status"],"unresolved")
            self.assertIn(r["reason"],("scene_wide_surface_cannot_identify_board",
                                       "patch_touches_image_edge"))

    def test_smooth_background_must_not_be_mislabeled_board(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"smooth.zip";synthetic_zip(p,kind="smooth")
            r=audit(p)["sessions"][0]
            self.assertEqual(r["status"],"unresolved",r)
            self.assertFalse(r["semantic_board_identified"])

    def test_unobserved_boundary_is_not_positive_step(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"masked.zip";synthetic_zip(p,kind="masked",missing_band=True)
            r=audit(p)["sessions"][0]
            self.assertEqual(r["status"],"unresolved",r)
            self.assertFalse(r["semantic_board_identified"])

    def test_missing_intrinsics_does_not_guess_camera_geometry(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"unknown.zip";synthetic_zip(p,metadata=False)
            r=audit(p)["sessions"][0]
            self.assertEqual(r["reason"],"intrinsics_missing")

    def test_two_identical_patches_do_not_prove_board_or_pose(self):
        with tempfile.TemporaryDirectory() as d:
            a,b=Path(d)/"first.zip",Path(d)/"second.zip"
            synthetic_zip(a);synthetic_zip(b)
            r=audit(a,b)
            self.assertTrue(r["capture_geometry_compatible"])
            self.assertFalse(r["same_physical_patch_verified"])
            self.assertFalse(r["paired_board_segmentation_approved"])
            self.assertFalse(r["physical_slope_accuracy_certified"])

    def test_missing_frame_archive_must_fail(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"bad.zip"
            with zipfile.ZipFile(p,"w") as z:z.writestr(ROOT+"record_identity.json","{}")
            with self.assertRaises(ValueError):audit(p)

if __name__=="__main__":unittest.main()
