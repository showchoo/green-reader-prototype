#!/usr/bin/env python3
"""Offline Camera2 DEPTH16 + TYPE_GRAVITY audit, user-reported fixed mount.

Read four private user-owned ZIPs only. Never infer device rotation from the
gravity sensor alone: Android TYPE_GRAVITY is a fused estimate and archives
contain no independent raw acceleration/gyro or fixed-target fiducials.
"""
import argparse
import csv
import io
import json
import warnings
import zipfile
from pathlib import Path

import numpy as np

# Predeclared background candidate; no verified object identity or camera pose.
STATIC_CANDIDATE_YX=(100,370,530,625)


def unit(vector):
    v=np.asarray(vector,float)
    length=float(np.linalg.norm(v))
    if not np.isfinite(length) or length<1e-10:
        raise ValueError("Invalid gravity reference")
    return v/length


def angle_deg(a,b):
    return float(np.degrees(np.arccos(np.clip(unit(a)@unit(b),-1,1))))


def posture_interpretation(gravity_angle_deg,operator_reports_fixed):
    if not isinstance(operator_reports_fixed,bool):
        raise ValueError("Require explicit operator mount condition")
    if not np.isfinite(gravity_angle_deg) or gravity_angle_deg<0:
        raise ValueError("Invalid gravity difference")
    if operator_reports_fixed and gravity_angle_deg>0.5:
        return "FUSED_GRAVITY_DIRECTION_DISAGREES_WITH_FIXED_MOUNT_REPORT"
    return "NO_LARGE_INTER_SESSION_GRAVITY_CONFLICT_DETECTED"


def load_session(path):
    path=Path(path)
    with zipfile.ZipFile(path) as z:
        roots={n.rsplit("/",1)[0] for n in z.namelist()
               if n.endswith("/camera2_gravity.csv")}
        if len(roots)!=1:raise ValueError("Require exactly one gravity record")
        root=roots.pop()
        samples=list(csv.DictReader(io.StringIO(z.read(
            root+"/camera2_gravity.csv").decode("utf8"))))
        capture_rows=list(csv.DictReader(io.StringIO(z.read(
            root+"/camera2_depth_frames.csv").decode("utf8"))))
        calibration=json.loads(z.read(root+"/camera2_calibration.json"))
        g=np.array([[float(row[key]) for key in ("gx","gy","gz")]
                    for row in samples],float)
        if g.ndim!=2 or len(g)<60 or not np.isfinite(g).all():
            raise ValueError("Insufficient valid gravity sensor samples")
        gn=np.linalg.norm(g,axis=1)
        if np.any(gn<=1.e-10):raise ValueError("Zero gravity vector")
        u=g/gn[:,None]
        tail=unit(np.median(u[-50:],axis=0))
        frames=[]
        height,width=int(calibration["height"]),int(calibration["width"])
        if (height,width)!=(480,640):raise ValueError("Unexpected DEPTH16 grid")
        for row in capture_rows:
            binary=z.read(root+"/depth_%04d.bin"%int(row["index"]))
            if len(binary)!=width*height*2:raise ValueError("Corrupt DEPTH16 frame")
            mm=np.frombuffer(binary,dtype="<u2").reshape(height,width)&8191
            if (mm>0).any():frames.append(mm)
        if len(frames)<6:raise ValueError("Insufficient nonzero frames")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore",RuntimeWarning)
        med=np.nanmedian(np.where(np.asarray(frames)>0,frames,np.nan),axis=0)
    return {
        "file":path.name,"reference_vector":tail,
        "gravity_start_vs_settled_deg":angle_deg(u[0],tail),
        "settled_max_sample_deviation_deg":
            max(angle_deg(v,tail) for v in u[-50:]),
        "gravity_norm_mean_mps2":float(gn.mean()),
        "gravity_norm_std_mps2":float(gn.std()),
        "nonzero_depth_frames":len(frames),
        "median_depth":med}


def compare(a,b):
    y0,y1,x0,x1=STATIC_CANDIDATE_YX
    d0=a["median_depth"][y0:y1,x0:x1]
    d1=b["median_depth"][y0:y1,x0:x1]
    common=np.isfinite(d0)&np.isfinite(d1)
    if common.mean()<0.80:
        raise ValueError("Candidate background has insufficient valid depth")
    d=d1[common]-d0[common]
    return {
        "gravity_reference_direction_difference_deg":
            round(angle_deg(a["reference_vector"],b["reference_vector"]),4),
        "candidate_background_depth_median_change_mm":
            float(np.median(d)),
        "candidate_background_depth_p10_p90_mm":
            [float(np.percentile(d,10)),float(np.percentile(d,90))],
        "candidate_background_identity_verified":False,
        "physical_camera_motion_measured":False}


def audit(paths,operator_reports_fixed):
    if len(paths)!=4 or len({str(Path(p).resolve()) for p in paths})!=4:
        raise ValueError("Exactly four distinct sessions required")
    measurements=[load_session(p) for p in paths]
    checks={key:compare(measurements[i],measurements[j]) for key,i,j in (
        ("A_to_B",0,1),("C_to_D",2,3),
        ("A_to_C",0,2),("B_to_D",1,3))}
    status=posture_interpretation(
        checks["A_to_C"]["gravity_reference_direction_difference_deg"],
        operator_reports_fixed)
    summaries=[
        {key:(round(float(value),7) if isinstance(value,float) else value)
         for key,value in item.items()
         if key not in ("reference_vector","median_depth")}
        for item in measurements]
    return {
        "condition_sequence":["level","raised","level","raised"],
        "operator_reports_unchanged_camera_mount":operator_reports_fixed,
        "gravity_source":"Android TYPE_GRAVITY fused estimate only",
        "raw_accelerometer_and_gyro_recorded":False,
        "capture_stats":summaries,
        "pair_diagnostics":checks,
        "gravity_reference_status":status,
        "physical_camera_rotation_established":False,
        "cause_of_reference_change_determined":False,
        "grade_accuracy_certified":False,
        "new_capture_required":False,
        "caution":"Fixed scene ROI is not independently surveyed, and fused gravity alone does not establish movement."
    }


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("session_zip",nargs=4,type=Path)
    p.add_argument("--fixed-camera-affirmed",action="store_true")
    p.add_argument("--output",type=Path)
    args=p.parse_args()
    result=json.dumps(audit(args.session_zip,args.fixed_camera_affirmed),
                      indent=2,ensure_ascii=False)
    if args.output:args.output.write_text(result,encoding="utf8")
    else:print(result)
