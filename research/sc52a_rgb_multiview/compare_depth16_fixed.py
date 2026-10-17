#!/usr/bin/env python3
"""Compare two privately held Camera2 DEPTH16 research session ZIP files.

Never treats same pixel as independently tracked physical floor; angular change
from gravity sensors is device *motion*, not a calibrated slope error. This
research output cannot certify putting precision, and never uploads user data.
Requires numpy. Excludes the initial all-zero warm-up frame.
"""
from pathlib import Path
import argparse
import csv
import io
import json
import zipfile
import numpy as np

def read_session(path):
    with zipfile.ZipFile(path) as z:
        prefix=next((s.rsplit("/",1)[0] for s in z.namelist()
                     if s.endswith("/camera2_depth_summary.json")),None)
        if prefix is None:
            raise ValueError("Missing Camera2 DEPTH16 summary")
        base=prefix+"/"
        calibration=json.loads(z.read(base+"camera2_calibration.json"))
        status=json.loads(z.read(base+"camera2_depth_summary.json"))
        rows=list(csv.DictReader(io.StringIO(
            z.read(base+"camera2_depth_frames.csv").decode("utf-8"))))
        gravity=list(csv.DictReader(io.StringIO(
            z.read(base+"camera2_gravity.csv").decode("utf-8"))))
        w,h=int(status["width"]),int(status["height"])
        if (w,h)!=(int(calibration["width"]),int(calibration["height"])):
            raise ValueError("Calibration does not match captured format")
        if len(rows)!=int(status["frame_count"]):
            raise ValueError("Frame manifest and capture count disagree")
        packed=[];time=[];indices=[]
        for row in rows:
            idx=int(row["index"])
            if int(row["width"])!=w or int(row["height"])!=h:
                raise ValueError("Wrong frame dimensions")
            raw=z.read(base+f"depth_{idx:04d}.bin")
            if len(raw)!=2*w*h:
                raise ValueError("Bad DEPTH16 byte count")
            packed.append(np.frombuffer(raw,dtype="<u2").reshape(h,w))
            time.append(int(row["image_timestamp_ns"]))
            indices.append(idx)
        if len(set(indices))!=len(indices) or not all(a<b for a,b in zip(time,time[1:])):
            raise ValueError("Duplicate depth frame or timestamps not increasing")
        data=np.stack(packed)
        mm=(data&8191).astype(np.int32)
        conf=(data>>13).astype(np.uint8)
        present=(mm>0).any(axis=(1,2))
        valid=mm[present]>0
        if int(present.sum())<3:
            raise ValueError("Not enough nonzero DEPTH16 frames")
        depth=mm[present]
        codes=conf[present]
        common=valid.all(axis=0)
        if common.sum()<100:
            raise ValueError("Too few same-image-coordinate common samples")
        diff=np.diff(depth,axis=0)
        adjacent=abs(diff[(valid[:-1]&valid[1:])])
        spans=np.ptp(depth[:,common],axis=0)
        first=depth[:5,common].astype(float).mean(axis=0)
        last=depth[-5:,common].astype(float).mean(axis=0)
        cross=last-first
        center=depth[:,h//2-50:h//2+50,w//2-50:w//2+50]
        center_median=[
            float(np.median(frame[frame>0])) for frame in center
        ]
        all_median=[
            float(np.median(frame[frame>0])) for frame in depth
        ]
        hist=np.bincount(codes[valid],minlength=8)

        gravity_times=np.asarray(
            [int(g["sensor_timestamp_ns"]) for g in gravity],dtype=np.int64)
        grav_vectors=np.asarray([
            [float(g[k]) for k in ("gx","gy","gz")] for g in gravity
        ],dtype=np.float64)
        grav_vectors/=np.linalg.norm(grav_vectors,axis=1)[:,None]
        times=np.asarray(time,dtype=np.int64)[present]
        ids=abs(gravity_times[:,None]-times[None,:]).argmin(axis=0)
        grav=grav_vectors[ids]
        angles=np.rad2deg(np.arccos(np.clip(grav@grav[0],-1,1)))
        return {
            "source":Path(path).name,
            "camera_id":calibration["camera_id"],
            "range_unit":"radial millimetres",
            "frames_total":len(data),
            "frames_nonempty":int(present.sum()),
            "first_frame_empty":bool(not present[0]),
            "valid_pixel_fraction_median":round(float(np.median(valid.mean(axis=(1,2)))),6),
            "all_frame_median_range_span_mm":round(float(np.ptp(all_median)),2),
            "center_100x100_median_range_span_mm":round(float(np.ptp(center_median)),2),
            "same_image_pixel_all_frames_count":int(common.sum()),
            "same_image_pixel_span_p50_mm":round(float(np.median(spans)),2),
            "same_image_pixel_span_p90_mm":round(float(np.percentile(spans,90)),2),
            "adjacent_image_pixel_abs_difference_p50_mm":round(float(np.median(adjacent)),2),
            "adjacent_image_pixel_abs_difference_p90_mm":round(float(np.percentile(adjacent,90)),2),
            "early_late_same_image_pixel_shift_median_mm":round(float(np.median(cross)),2),
            "early_late_same_image_pixel_abs_shift_p50_mm":round(float(np.median(abs(cross))),2),
            "early_late_same_image_pixel_abs_shift_p90_mm":round(float(np.percentile(abs(cross),90)),2),
            "depth_nonzero_confidence_counts":hist.tolist(),
            "high_confidence_pixel_count":int(hist[0]+hist[5:].sum()),
            "gravity_sample_count":len(gravity),
            "recorded_gravity_direction_max_change_degrees":round(float(angles.max()),5),
            "metric_slope_certified":False,
            "limitations":"Handheld and fixed samples have different approximate ranges; same pixel is not a uniquely identified ground point; intrinsic depth bias and lens/IMU extrinsics unverified."
        }

def compare(handheld,fixed):
    a=read_session(handheld);b=read_session(fixed)
    if a["camera_id"]!=b["camera_id"]:
        raise ValueError("Different DEPTH16 cameras cannot be directly compared")
    return dict(
        status="DIRECT_DEPTH16_CAPTURE_WORKS_BUT_PHYSICAL_SLOPE_NOT_VERIFIED",
        handheld=a,fixed=b,
        fixed_gravity_motion_reduction_factor=round(
            a["recorded_gravity_direction_max_change_degrees"]/
            b["recorded_gravity_direction_max_change_degrees"],1)
            if b["recorded_gravity_direction_max_change_degrees"] else None,
        comparison_is_not_calibrated_absolute_accuracy=True,
        commercial_putting_accuracy_certified=False)

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("handheld_zip",type=Path)
    parser.add_argument("fixed_zip",type=Path)
    parser.add_argument("--output",type=Path)
    args=parser.parse_args()
    txt=json.dumps(compare(args.handheld_zip,args.fixed_zip),indent=2,
                   ensure_ascii=False)
    if args.output:args.output.write_text(txt,encoding="utf-8")
    else:print(txt)
