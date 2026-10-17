#!/usr/bin/env python3
"""Compare two direct DEPTH16 sessions of one independently measured planar target.

Research only: level target then known shim, same stationary camera, same
physical ROI x350..620 y80..400. The angle between camera-frame normals can
test grade CHANGE while avoiding an unverified camera-to-gravity transform.
No automatic floor identification, sign, confidence certification or accuracy
release from a single pair. Does not transmit the private captured depth.
"""
import argparse
import json
import math
from pathlib import Path
import numpy as np
from compare_depth_geometry_models import (
    read_session,rays_from_calibration,region_points,robust_plane
)

ROI=(80,400,350,620)


def summarize_session(path):
    cal,raw=read_session(path)
    frames=raw[np.any(raw>0,axis=(1,2))]
    if len(frames)<6:raise ValueError("Need six valid depth frames")
    rays=rays_from_calibration(cal)
    normals=[];p90=[]
    for f in frames:
        pts=region_points(f,rays,ROI,"optical_axis")
        fit=robust_plane(pts)
        if fit is None:continue
        n,d=fit
        normals.append(n)
        p90.append(float(np.percentile(abs(pts@n+d)*1000,90)))
    if len(normals)<6:raise ValueError("Cannot locate stable candidate plane")
    ns=np.asarray(normals,float)
    reference=np.median(ns,axis=0)
    reference/=np.linalg.norm(reference)
    deviation=np.degrees(np.arccos(np.clip(ns@reference,-1,1)))
    return {"normal":reference,"frames":len(ns),
            "max_frame_angle_deg":float(max(deviation)),
            "median_planar_p90_mm":float(np.median(p90))}


def compare_normal_delta(n0,n1,known_rise_mm,known_run_mm):
    if not (math.isfinite(known_rise_mm) and math.isfinite(known_run_mm)):
        raise ValueError("Finite physical reference required")
    if not (0<=known_rise_mm<=100 and 500<=known_run_mm<=3000):
        raise ValueError("Reference outside checked laboratory range")
    a=np.asarray(n0,float);b=np.asarray(n1,float)
    if np.linalg.norm(a)==0 or np.linalg.norm(b)==0:
        raise ValueError("Invalid plane normals")
    a/=np.linalg.norm(a);b/=np.linalg.norm(b)
    diff=math.degrees(math.acos(float(np.clip(a@b,-1,1))))
    observed=100*math.tan(math.radians(diff))
    expected=100*known_rise_mm/known_run_mm
    return {"candidate_normal_change_degrees":round(diff,5),
            "candidate_unsigned_grade_change_percent":round(observed,4),
            "independent_grade_change_percent":round(expected,4),
            "unsigned_error_pp":round(abs(observed-expected),4),
            "signed_grade_available":False,"certified_accuracy":False}


def evaluate(level_zip,inclined_zip,rise_mm,run_mm):
    if Path(level_zip).resolve()==Path(inclined_zip).resolve():
        raise ValueError("Two independent captures are needed")
    a=summarize_session(level_zip)
    b=summarize_session(inclined_zip)
    output=compare_normal_delta(a["normal"],b["normal"],rise_mm,run_mm)
    for prefix,scan in (("level",a),("inclined",b)):
        output[prefix+"_frames"]=scan["frames"]
        output[prefix+"_max_frame_normal_drift_degrees"]=round(scan["max_frame_angle_deg"],4)
        output[prefix+"_median_plane_p90_mm"]=round(scan["median_planar_p90_mm"],2)
    stable=(max(a["max_frame_angle_deg"],b["max_frame_angle_deg"])<.15 and
            max(a["median_planar_p90_mm"],b["median_planar_p90_mm"])<12)
    output["within_capture_geometry_consistent"]=stable
    output["decision"]="RESEARCH_EVIDENCE_ONLY" if stable else "REJECT_UNSTABLE_GEOMETRY"
    output["certified_putting_accuracy"]=False
    output["limitations"]=[
        "Same scene feature and fixed camera mount required, neither machine-verified",
        "Camera-relative angle magnitude does not establish signed slope",
        "Only one incline pair cannot prove 0.5pp repeatability/worst-case accuracy",
        "DEPTH16 confidence reported low and physical ground truth may be uncertain"
    ]
    return output


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("level_zip",type=Path)
    p.add_argument("inclined_zip",type=Path)
    p.add_argument("--rise-mm",required=True,type=float)
    p.add_argument("--run-mm",required=True,type=float)
    args=p.parse_args()
    print(json.dumps(evaluate(args.level_zip,args.inclined_zip,
                              args.rise_mm,args.run_mm),ensure_ascii=False,indent=2))
