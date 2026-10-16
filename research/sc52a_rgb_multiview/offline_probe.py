#!/usr/bin/env python3
"""Offline feasibility probe: independent per-frame Raw slopes and RGB 2D tracking.

Requires numpy + opencv-python-headless. NEVER claims metric 3D accuracy.
Only reads user-authorized local Session ZIPs. Does not upload photos or logs.
"""
import argparse
import csv
import io
import json
import zipfile
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np


def robust_plane(along, cross, height):
    design = np.column_stack((along, cross, np.ones_like(height)))
    beta = np.linalg.lstsq(design, height, rcond=None)[0]
    for _ in range(4):
        residual = height - design @ beta
        spread = max(.001, 1.4826 * np.median(abs(residual - np.median(residual))))
        w = np.clip(1.5 * spread / (abs(residual) + 1.e-12), .06, 1.)
        sq = np.sqrt(w)
        beta = np.linalg.lstsq(design * sq[:, None], height * sq, rcond=None)[0]
    return beta


def slope_from_frame(xyz, fx, fz, length, min_points=120):
    pts = np.asarray(xyz, dtype=float)
    if len(pts) < min_points:
        return None
    along = pts[:, 0] * fx + pts[:, 1] * fz
    cross = -pts[:, 0] * fz + pts[:, 1] * fx
    height = pts[:, 2]
    good = ((along >= -.15) & (along <= length + .15) &
            (abs(cross) < .30) & (abs(height) < .60))
    along, cross, height = along[good], cross[good], height[good]
    if len(height) < min_points:
        return None
    good = abs(height - np.median(height)) < .09
    along, cross, height = along[good], cross[good], height[good]
    if len(height) < min_points:
        return None
    hist = np.histogram(along, bins=np.linspace(0, length, 6))[0]
    if ((hist >= 10).sum() < 4 or np.ptp(along) < .6 * length or
            np.ptp(cross) < .18):
        return None
    b = robust_plane(along, cross, height)
    # A change of ground tilt across the same frame's two halves is not
    # strong planar evidence. This criterion is only an indoor test.
    left = along < np.median(along)
    split = float("inf")
    if left.sum() >= 60 and (~left).sum() >= 60:
        p0 = robust_plane(along[left], cross[left], height[left])
        p1 = robust_plane(along[~left], cross[~left], height[~left])
        split = float(100 * max(abs(p0[0]-p1[0]), abs(p0[1]-p1[1])))
    return dict(long_pct=float(100*b[0]), cross_pct=float(100*b[1]),
                offset_cm=float(100*b[2]), split_delta_pp=split)


def consensus_gate(frames):
    if len(frames) < 5:
        return dict(status="INSUFFICIENT_FRAMES", count=len(frames),
                    certified_accuracy=False)
    long = np.asarray([f["long_pct"] for f in frames])
    cross = np.asarray([f["cross_pct"] for f in frames])
    split = np.asarray([f["split_delta_pp"] for f in frames])
    half = len(frames)//2
    early_late = max(abs(np.median(long[:half])-np.median(long[half:])),
                     abs(np.median(cross[:half])-np.median(cross[half:])))
    spans = (float(np.ptp(long)),float(np.ptp(cross)))
    dispersion = max(np.median(abs(long-np.median(long))),
                     np.median(abs(cross-np.median(cross))))
    stable = (max(spans) <= 1. and early_late <= .5 and
              dispersion <= .25 and np.median(split) <= 1.)
    return dict(status="INTERNAL_CONSENSUS_ONLY" if stable else "REJECT_INCONSISTENT",
                count=len(frames), long_pct=round(float(np.median(long)),3),
                cross_pct=round(float(np.median(cross)),3),
                long_span_pp=round(spans[0],3),cross_span_pp=round(spans[1],3),
                early_late_max_pp=round(float(early_late),3),
                median_split_pp=round(float(np.median(split)),3),
                height_offset_span_cm=round(float(np.ptp([f["offset_cm"] for f in frames])),2),
                certified_accuracy=False)


def scan_raw(z, root):
    meta = json.loads(z.read(root+"/metadata.json"))
    if meta.get("distance_m",0) < .4:
        return dict(scan=root,status="BAD_BASELINE",certified_accuracy=False)
    cup=meta["cup_world"]
    fx,fz=cup["x"],cup["z"]
    length=float(np.hypot(fx,fz))
    if length < .4 or abs(length-meta["distance_m"]) > .08:
        return dict(scan=root,status="BAD_CUP_GEOMETRY",certified_accuracy=False)
    fx,fz=fx/length,fz/length
    rows=list(csv.DictReader(io.StringIO(z.read(root+"/precision_depth_points.csv").decode())))
    sources=list(csv.DictReader(io.StringIO(z.read(root+"/precision_depth_sources.csv").decode())))
    if len(rows)!=len(sources):
        return dict(scan=root,status="MISMATCHED_SOURCE_SIDECAR",certified_accuracy=False)
    by_frame=defaultdict(list)
    for p,source in zip(rows,sources):
        if source["depth_source"]!="raw":
            continue
        by_frame[int(p["frame_timestamp_ns"])].append(
            (float(p["x_m"]),float(p["z_m"]),float(p["y_m"])))
    fitted=[f for _,xyz in sorted(by_frame.items())
            if (f:=slope_from_frame(xyz,fx,fz,length)) is not None]
    return dict(scan=root, original_app_long_pct=meta.get("overall_longitudinal_percent"),
                **consensus_gate(fitted))


def track_rgb(z, folder):
    files=sorted(f for f in z.namelist() if f.startswith(folder+"/") and
                 f.endswith("/camera.jpg"))
    detector=cv2.SIFT_create(nfeatures=2500,contrastThreshold=.02)
    features=[]
    for file in files:
        image=cv2.imdecode(np.frombuffer(z.read(file),np.uint8),0)
        if image is None:
            continue
        image=cv2.resize(image,None,fx=.5,fy=.5,interpolation=cv2.INTER_AREA)
        mask=np.zeros(image.shape,np.uint8)
        mask[int(image.shape[0]*.5):,:]=255
        kp,des=detector.detectAndCompute(image,mask)
        features.append((file,kp,des,image.shape))
    matcher=cv2.BFMatcher(cv2.NORM_L2)
    pairs=[]
    for a,b in zip(features,features[1:]):
        file0,kp0,des0,shape=a
        file1,kp1,des1,_=b
        matches=matcher.knnMatch(des0,des1,k=2) if des0 is not None and des1 is not None else []
        strong=[m for m,n in matches if m.distance<.72*n.distance]
        n=0
        tiles=0
        if len(strong)>=8:
            src=np.float32([kp0[m.queryIdx].pt for m in strong])
            dst=np.float32([kp1[m.trainIdx].pt for m in strong])
            h,inmask=cv2.findHomography(src,dst,cv2.RANSAC,3.0,maxIters=2500)
            if h is not None and inmask is not None:
                matched=src[inmask.ravel().astype(bool)]
                n=len(matched)
                tiles=len(set(zip(np.clip((matched[:,0]/(shape[1]/4)).astype(int),0,3),
                                  np.clip((matched[:,1]/(shape[0]/8)).astype(int),0,7))))
        pairs.append(dict(first=Path(file0).parts[1],second=Path(file1).parts[1],
                          matched_2d_inliers=n,spatial_tiles=tiles,
                          trackable_floor_candidate=n>=40 and tiles>=8,
                          measured_3d_height=False))
    return pairs


def analyze_zip(path):
    with zipfile.ZipFile(path) as z:
        roots=sorted(x.rsplit("/",1)[0] for x in z.namelist()
                     if "/Scan_" in x and x.endswith("/metadata.json"))
        return dict(source=Path(path).name,frame_consensus=[
            scan_raw(z,root) for root in roots],
            rgb_2d_pairs=track_rgb(z,"Putt_002"),
            independent_physical_accuracy=False,
            caveat="2D homographies and internally stable Raw points are not metric 3D or physical slope truth.")


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("session_zip",type=Path)
    p.add_argument("--output",type=Path)
    a=p.parse_args()
    result=json.dumps(analyze_zip(a.session_zip),ensure_ascii=False,indent=2)
    if a.output:
        a.output.write_text(result,encoding="utf-8")
    else:
        print(result)
