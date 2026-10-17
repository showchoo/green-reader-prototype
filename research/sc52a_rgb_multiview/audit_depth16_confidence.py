#!/usr/bin/env python3
"""Confidence/temporal audit of user-authorized direct Camera2 DEPTH16 ZIP.

No plane or putting slope inferred: camera is hand-held, pixels can shift
relative to physical ground. No private images, maps, or ZIPs are uploaded.
Requires numpy. Fails closed on corrupt/incomplete session ZIP.
"""
import argparse
import csv
import io
import json
import zipfile
from pathlib import Path
import numpy as np


def decode(data, width, height):
    if len(data) != 2*width*height:
        raise ValueError("incorrect depth frame byte size")
    packed=np.frombuffer(data,dtype='<u2').reshape(height,width)
    return (packed&8191), (packed>>13)


def confidence_fraction(codes):
    codes=np.asarray(codes)
    return np.where(codes==0,1.,(codes.astype(float)-1.)/7.)


def report(path):
    path=Path(path)
    results=[]
    with zipfile.ZipFile(path) as z:
        roots=sorted(set(name.rsplit("/",1)[0] for name in z.namelist()
                         if name.endswith("/camera2_depth_summary.json")))
        for root in roots:
            status=json.loads(z.read(root+"/camera2_depth_summary.json"))
            calib=json.loads(z.read(root+"/camera2_calibration.json"))
            rows=list(csv.DictReader(io.StringIO(
                z.read(root+"/camera2_depth_frames.csv").decode("utf-8"))))
            gravity=list(csv.DictReader(io.StringIO(
                z.read(root+"/camera2_gravity.csv").decode("utf-8"))))
            w,h=int(calib["width"]),int(calib["height"])
            if w<=0 or h<=0 or len(rows)!=int(status["frame_count"]):
                raise ValueError("missing frames or calibration")
            depth=[];conf=[];timestamps=[];indexes=[]
            for row in rows:
                idx=int(row["index"])
                if (int(row["width"]),int(row["height"]))!=(w,h):
                    raise ValueError("frame/calibration mismatch")
                mm,code=decode(
                    z.read(root+"/depth_%04d.bin"%idx),w,h)
                depth.append(mm)
                conf.append(code)
                timestamps.append(int(row["image_timestamp_ns"]))
                indexes.append(idx)
            if len(set(indexes))!=len(indexes) or any(
                    b<=a for a,b in zip(timestamps,timestamps[1:])):
                raise ValueError("duplicate frame or nonmonotonic camera timestamp")
            mm=np.stack(depth)
            codes=np.stack(conf)
            valid=mm>0
            nonempty=valid.any(axis=(1,2))
            actual=valid[nonempty]
            count=int(valid.sum())
            histogram=np.bincount(codes[valid],minlength=8)
            high=int(histogram[0]+sum(histogram[5:]))
            conf_mean=float(np.sum(histogram*confidence_fraction(np.arange(8)))/count) if count else 0.
            out=dict(
                root=root,source="public Camera2 DEPTH16",
                depth_camera_id=calib["camera_id"],
                frame_count=len(mm),
                empty_frame_ids=[indexes[i] for i,v in enumerate(nonempty) if not v],
                nonempty_frames=int(nonempty.sum()),
                median_valid_coverage=float(np.median(actual.mean(axis=(1,2)))) if len(actual) else 0.,
                per_frame_median_range_mm=[
                    float(np.median(v[s])) if s.any() else None
                    for v,s in zip(mm,valid)],
                confidence_codes_nonzero={str(i):int(n) for i,n in enumerate(histogram)},
                mean_reported_confidence=float(conf_mean),
                camera_intrinsics_available=bool(calib.get("lens_intrinsic_calibration")),
                lens_pose_available=bool(calib.get("lens_pose_translation")),
                physical_tof_identity_verified=False,
                independently_measured_grade_error=False,
                putting_grade_certified=False)
            out["confidence_ge_50pct_count"]=high
            out["confidence_ge_50pct_fraction"]=high/count if count else 0.
            if len(actual)>=3:
                stable=np.all(actual,axis=0)
                out["same_pixel_all_frames_valid_count"]=int(stable.sum())
                if stable.any():
                    ranges=np.ptp(mm[nonempty][:,stable].astype(np.int32),axis=0)
                    out["same_pixel_temporal_span_median_mm"]=float(np.median(ranges))
                    out["same_pixel_temporal_span_p90_mm"]=float(np.percentile(ranges,90))
                hh,ww=mm.shape[1:]
                block=mm[nonempty,hh//2-50:hh//2+50,ww//2-50:ww//2+50]
                med=[float(np.median(x[x>0])) if (x>0).any() else None for x in block]
                out["center_100x100_per_frame_medians_mm"]=med
                med=[v for v in med if v is not None]
                out["center_median_drift_mm"]=max(med)-min(med) if med else None
            out["gravity_sample_count"]=len(gravity)
            if gravity and int(nonempty.sum())>=2:
                gt=np.array([int(g["sensor_timestamp_ns"]) for g in gravity],dtype=np.int64)
                gv=np.array([[float(g[c]) for c in ("gx","gy","gz")] for g in gravity])
                ft=np.asarray(timestamps,dtype=np.int64)[nonempty]
                closest=abs(gt[:,None]-ft[None,:]).argmin(axis=0)
                g=gv[closest];g=g/np.linalg.norm(g,axis=1,keepdims=True)
                angle=np.degrees(np.arccos(np.clip(g@g[0],-1,1)))
                out["gravity_direction_change_max_degrees"]=float(angle.max())
            out["status"]=(
                "UNUSABLE_DEPTH" if int(nonempty.sum())<3 else
                "VALID_RANGE_BUT_ZERO_HIGH_CONFIDENCE" if high==0 else
                "RANGE_CAPTURED_EXACT_SLOPE_UNVERIFIED")
            out["caveat"]="Same image pixel between moving hand-held frames is not fixed physical ground; no independent surveyed rise/run."
            results.append(out)
    return dict(filename=path.name,scans=results,
                commercial_grade_ready=False,physical_accuracy_certified=False)


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("session_zip",type=Path)
    parser.add_argument("--output",type=Path)
    args=parser.parse_args()
    text=json.dumps(report(args.session_zip),indent=2,ensure_ascii=False)
    if args.output:args.output.write_text(text,encoding="utf8")
    else:print(text)
