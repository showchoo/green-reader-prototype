#!/usr/bin/env python3
"""Four-scan Camera2 DEPTH16 audit with UNKNOWN condition labels.

There may be two repeated captures of each condition or two independent
(level,tilt) pairs. Neither order is inferred from clock proximity.
Compares every capture pairing on fixed predeclared ROIs. Does not select
the region that best approximates 2% and never certifies putting accuracy.

Run offline on user-owned Session_HW_DEPTH_*.zip (raw pixels stay private).
Requires numpy/opencv-python-headless.
"""
import argparse
import csv
import io
import itertools
import json
from pathlib import Path
import zipfile

import numpy as np

from compare_depth_geometry_models import (
    read_session, rays_from_calibration, region_points, robust_plane,
)

PREDECLARED_REGIONS = {
    "full_interior": (40,450,130,635),
    "left_interior": (40,450,130,350),
    "center_interior": (40,450,285,515),
    "right_interior": (40,450,400,635),
    "top_center": (65,225,270,470),
    "bottom_center": (255,415,270,470),
    "far_right": (70,420,510,635),
}


def normalized(v):
    v=np.asarray(v,dtype=float)
    l=np.linalg.norm(v)
    if not np.isfinite(l) or l<1.e-8:
        raise ValueError("Invalid vector norm")
    return v/l


def normal_angle_deg(a,b):
    return float(np.degrees(np.arccos(np.clip(
        normalized(a)@normalized(b),-1,1))))


def condition_labels(label_list):
    """Require deliberate, user-provided conditions; never guess by time."""
    if label_list is None:
        return None
    if len(label_list)!=4 or set(label_list)!={"level","raised"}:
        raise ValueError("Specify exactly four level/raised labels containing both")
    if label_list.count("level")!=2 or label_list.count("raised")!=2:
        raise ValueError("Each of two conditions needs exactly two captures")
    return list(label_list)


def acquire_orientation(path,nonempty_frame_mask):
    """Gravity measures device roll/pitch direction; yaw is unobservable."""
    with zipfile.ZipFile(path) as z:
        matches=[
            n for n in z.namelist()
            if n.endswith("/camera2_gravity.csv")
        ]
        rows=[
            n for n in z.namelist()
            if n.endswith("/camera2_depth_frames.csv")
        ]
        if len(matches)!=1 or len(rows)!=1:
            raise ValueError("Missing gravity or camera timestamp metadata")
        g=list(csv.DictReader(
            io.StringIO(z.read(matches[0]).decode("utf-8"))))
        f=list(csv.DictReader(
            io.StringIO(z.read(rows[0]).decode("utf-8"))))
    if not g or len(f)!=len(nonempty_frame_mask):
        raise ValueError("Invalid gravity and capture timestamp count")
    gt=np.array([int(v["sensor_timestamp_ns"]) for v in g],
                dtype=np.int64)
    gv=np.array([[float(v[k]) for k in ("gx","gy","gz")]
                for v in g])
    norm=np.linalg.norm(gv,axis=1)
    valid=np.isfinite(gv).all(axis=1)&(norm>1.e-7)
    if valid.sum()<3:
        raise ValueError("Insufficient valid gravity")
    gt=gt[valid]
    gv=gv[valid]/norm[valid,None]
    times=np.array([int(v["image_timestamp_ns"]) for v in f],
                   dtype=np.int64)
    times=times[nonempty_frame_mask]
    nearest=np.abs(gt[:,None]-times[None,:]).argmin(axis=0)
    selected=gv[nearest]
    med=normalized(np.median(selected,axis=0))
    drift=max(normal_angle_deg(med,v) for v in selected)
    return med,drift


def region_normal(sequence,rays,roi):
    frames=[];deviations=[]
    for d in sequence:
        xyz=region_points(d,rays,roi,"optical_axis",step=4)
        fit=robust_plane(xyz)
        if fit is None:continue
        n,offset=fit
        n=normalized(n)
        if n[2]<0:n=-n
        frames.append(n)
    if len(frames)<6:
        return None
    median=normalized(np.median(frames,axis=0))
    drift=max(normal_angle_deg(median,n) for n in frames)
    return median,drift


def summarize_one(path):
    calibration,raw=read_session(path)
    keep=np.any(raw>0,axis=(1,2))
    sequence=raw[keep]
    if len(sequence)<6:
        raise ValueError("Less than six usable DEPTH16 frames")
    rays=rays_from_calibration(calibration)
    gravity,gravity_drift=acquire_orientation(path,keep)
    normals={}
    for name,roi in PREDECLARED_REGIONS.items():
        n=region_normal(sequence,rays,roi)
        normals[name]=n
    return {
        "filename":Path(path).name,
        "camera_id":calibration.get("camera_id"),
        "frame_count":len(raw),
        "valid_frames":len(sequence),
        "range_coverage_median":float(
            np.median((sequence>0).mean(axis=(1,2)))),
        "gravity":gravity,
        "gravity_drift_max_deg":gravity_drift,
        "normals":normals,
        "calibration":calibration,
    }


def evaluate_four(paths,labels=None):
    if len(paths)!=4 or len(set(str(Path(p).resolve()) for p in paths))!=4:
        raise ValueError("Exactly four distinct session ZIPs needed")
    labels=condition_labels(labels)
    captures=[summarize_one(path) for path in paths]
    for current in captures[1:]:
        for key in ("width","height","lens_intrinsic_calibration",
                    "lens_distortion","camera_id"):
            if captures[0]["calibration"].get(key)!=current["calibration"].get(key):
                raise ValueError("Camera characteristics differ: "+key)
    comparisons=[]
    for i,j in itertools.combinations(range(4),2):
        ci,cj=captures[i],captures[j]
        gravity_angle=normal_angle_deg(ci["gravity"],cj["gravity"])
        region_output={}
        for name in PREDECLARED_REGIONS:
            vi,vj=ci["normals"][name],cj["normals"][name]
            if vi is None or vj is None:
                region_output[name]=None
                continue
            ang=normal_angle_deg(vi[0],vj[0])
            region_output[name]={
                "unsigned_normal_delta_deg":round(ang,4),
                "unsigned_grade_equivalent_pct":round(
                    float(100*np.tan(np.radians(ang))),3),
                "capture0_internal_normal_drift_deg":round(vi[1],4),
                "capture1_internal_normal_drift_deg":round(vj[1],4),
            }
        comparisons.append({
            "capture_indices":[i,j],
            "labels_if_supplied":[labels[i],labels[j]] if labels else None,
            "device_gravity_direction_difference_deg":round(gravity_angle,4),
            "camera_posture_change_confound":gravity_angle>0.15,
            "unmeasured_yaw_or_translation":True,
            "board_surface_identity_verified":False,
            "regions":region_output,
        })
    return {
        "capture_order":[
            {"index":i,"filename":c["filename"],
             "valid_frames":c["valid_frames"],
             "depth_coverage_pct":round(c["range_coverage_median"]*100,2),
             "within_capture_gravity_drift_deg":
                round(c["gravity_drift_max_deg"],4)}
            for i,c in enumerate(captures)
        ],
        "condition_labels":labels,
        "time_proximity_is_not_ground_truth_condition":True,
        "comparisons":comparisons,
        "actual_rise_and_support_span_independently_measured":False,
        "signed_grade_certified":False,
        "absolute_grade_certified":False,
        "commercial_putting_accuracy_certified":False,
        "reason":"Unknown condition labels unless supplied; no independent board identity, camera yaw or translation, or measured physical grade reference.",
    }


def json_default(value):
    if isinstance(value,np.generic):return value.item()
    raise TypeError(type(value).__name__)


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("archives",nargs=4,type=Path)
    p.add_argument("--labels",nargs=4,
                   choices=["level","raised"],default=None,
                   help="In timestamp order. Omit unless confirmed by operator.")
    p.add_argument("--output",type=Path)
    args=p.parse_args()
    result=json.dumps(evaluate_four(args.archives,args.labels),
                      ensure_ascii=False,indent=2,default=json_default)
    if args.output:args.output.write_text(result,encoding="utf-8")
    else:print(result)
