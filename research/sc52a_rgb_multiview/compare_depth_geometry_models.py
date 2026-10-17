#!/usr/bin/env python3
"""Compare optical-axis Z and Euclidean radial interpretations of Camera2 DEPTH16.

Research ONLY: smaller 3D planar held-out residual is not ground-truth grade.
Uses bounded user-owned ZIPs offline; no images/sensor maps committed to git.
Dependencies: numpy, opencv-python-headless.
"""
import argparse
import csv
import io
import json
import zipfile
from pathlib import Path

import cv2
import numpy as np

SPLITS = {
    "upper_to_lower": ((80,240,350,620),(240,400,350,620)),
    "inner_to_outer": ((80,400,350,480),(80,400,480,620)),
}


def read_session(path):
    with zipfile.ZipFile(path) as z:
        roots={n.rsplit("/",1)[0] for n in z.namelist()
               if n.endswith("/camera2_depth_summary.json")}
        if len(roots)!=1:raise ValueError("Expected one DEPTH16 scan")
        root=roots.pop()
        cal=json.loads(z.read(root+"/camera2_calibration.json"))
        meta=json.loads(z.read(root+"/camera2_depth_summary.json"))
        rows=list(csv.DictReader(io.StringIO(
            z.read(root+"/camera2_depth_frames.csv").decode("utf8"))))
        w,h=int(cal["width"]),int(cal["height"])
        if len(rows)!=int(meta["frame_count"]) or min(w,h)<10:
            raise ValueError("Missing frames or invalid calibration")
        stack=[];times=[]
        for row in rows:
            i=int(row["index"])
            data=z.read(root+"/depth_%04d.bin"%i)
            if len(data)!=w*h*2:raise ValueError("Invalid frame byte count")
            stack.append(np.frombuffer(data,dtype="<u2").reshape(h,w)&8191)
            times.append(int(row["image_timestamp_ns"]))
        if any(a>=b for a,b in zip(times,times[1:])):
            raise ValueError("Depth timestamps not increasing")
    return cal,np.stack(stack)


def rays_from_calibration(cal):
    """Camera2 k1,k2,k3,p1,p2 -> OpenCV k1,k2,p1,p2,k3."""
    w,h=int(cal["width"]),int(cal["height"])
    intr=np.asarray(cal["lens_intrinsic_calibration"],float)
    dist=np.asarray(cal["lens_distortion"],float)
    if (len(intr)!=5 or len(dist)!=5 or
        not np.isfinite(intr).all() or not np.isfinite(dist).all() or
        min(intr[:2])<=0):
        raise ValueError("Invalid camera calibration")
    fx,fy,cx,cy,skew=intr
    K=np.array([[fx,skew,cx],[0,fy,cy],[0,0,1.]],float)
    cv_dist=dist[[0,1,3,4,2]]
    y,x=np.mgrid[:h,:w]
    pixels=np.stack([x,y],axis=-1).astype(float)
    uv=cv2.undistortPoints(
        pixels.reshape(-1,1,2),K,cv_dist).reshape(h,w,2)
    return np.dstack((uv,np.ones((h,w),float)))


def robust_plane(points):
    if len(points)<100:return None
    xyz=np.asarray(points,float)
    center=np.mean(xyz,axis=0)
    for _ in range(7):
        _,_,v=np.linalg.svd(xyz-center,full_matrices=False)
        normal=v[-1]
        residual=(xyz-center)@normal
        scale=max(.001,1.4826*np.median(
            abs(residual-np.median(residual))))
        weights=1/np.maximum(1,abs(residual)/(2*scale))
        center=np.average(xyz,axis=0,weights=weights)
        _,_,v=np.linalg.svd(
            (xyz-center)*np.sqrt(weights[:,None]),full_matrices=False)
        normal=v[-1]
    if normal[2]<0:normal=-normal
    return normal,-float(normal@center)


def region_points(depth,rays,roi,model,step=4):
    y0,y1,x0,x1=roi
    measured=depth[y0:y1:step,x0:x1:step].astype(float)
    direction=rays[y0:y1:step,x0:x1:step]
    valid=(measured>200)&(measured<5000)
    if valid.sum()<100:return np.empty((0,3))
    vectors=direction[valid]
    if model=="euclidean_range":
        vectors=vectors/np.linalg.norm(vectors,axis=1,keepdims=True)
    elif model!="optical_axis":
        raise ValueError("Unknown distance interpretation")
    return vectors*(measured[valid,None]/1000.)


def evaluate_frame(depth,rays,model):
    result={}
    for name,(train,test) in SPLITS.items():
        fitted=robust_plane(region_points(depth,rays,train,model))
        held=region_points(depth,rays,test,model)
        if fitted is None or len(held)<100:
            result[name]=None
            continue
        normal,offset=fitted
        error=np.abs(held@normal+offset)*1000
        result[name]=(float(np.median(error)),
                      float(np.percentile(error,90)),normal)
    return result


def analyze(path):
    cal,raw=read_session(path)
    frames=raw[np.any(raw>0,axis=(1,2))]
    if len(frames)<3:
        return dict(status="INSUFFICIENT_FRAMES",accuracy_certified=False)
    rays=rays_from_calibration(cal)
    modes={}
    for mode in ("optical_axis","euclidean_range"):
        each=[evaluate_frame(f,rays,mode) for f in frames]
        mode_stats={}
        for name in SPLITS:
            v=[entry[name] for entry in each if entry[name] is not None]
            if len(v)<3:
                mode_stats[name]={"status":"INSUFFICIENT_SPATIAL_DATA"}
                continue
            ns=np.stack([entry[2] for entry in v])
            ns=ns/np.linalg.norm(ns,axis=1)[:,None]
            central=np.median(ns,axis=0);central/=np.linalg.norm(central)
            angle=np.degrees(np.arccos(np.clip(ns@central,-1,1)))
            mode_stats[name]={
                "frame_count":len(v),
                "heldout_median_mm":round(float(np.median([r[0] for r in v])),3),
                "heldout_p90_mm":round(float(np.median([r[1] for r in v])),3),
                "max_frame_normal_drift_deg":round(float(angle.max()),3)}
        modes[mode]=mode_stats
    ratios={}
    for name in SPLITS:
        a=modes["optical_axis"][name]
        b=modes["euclidean_range"][name]
        if "heldout_median_mm" in a and "heldout_median_mm" in b:
            ratios[name]=round(b["heldout_median_mm"]/
                               max(a["heldout_median_mm"],.001),2)
    return {
        "source_file":Path(path).name,
        "nonempty_frames":len(frames),
        "candidate_region":"x350..620, y80..400; not independently identified as floor",
        "models":modes,
        "radial_to_axial_holdout_error_ratio":ratios,
        "accuracy_certified":False,
        "model_fits_do_not_prove_slope":True,
        "limitation":"Unknown surface identity, depth convention and physical gravity transform; not calibrated ground truth"}


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("zip_paths",nargs="+",type=Path)
    p.add_argument("--output",type=Path)
    args=p.parse_args()
    result=json.dumps({"experiments":[analyze(f) for f in args.zip_paths],
                       "commercial_putting_guide_allowed":False},
                      indent=2,ensure_ascii=False)
    if args.output:args.output.write_text(result,encoding="utf8")
    else:print(result)
