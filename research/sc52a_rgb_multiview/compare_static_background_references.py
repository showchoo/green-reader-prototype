"""Compare static-background references without picking the closest answer.

Input: two private user-authorized DEPTH16 ZIPs. Only aggregated numerical
diagnostics printed. No physical grade/phone accuracy certification.
The identical camera depth model is used for both before/after frames.
Requires numpy and opencv-python-headless.
"""
import argparse
import json
import math
import warnings
from pathlib import Path

import cv2
import numpy as np

from compare_depth_geometry_models import read_session, rays_from_calibration

# Predetermined across the same right-side unmoved background; overlapping
# windows are correlated, not independent validation.
BACKGROUNDS={
    "right_upper_inner": (80,240,530,580),
    "right_upper_outer": (80,240,580,638),
    "right_lower_inner": (240,410,530,580),
    "right_lower_outer": (240,410,580,638),
    "right_middle": (135,365,550,625),
    "right_wide": (100,410,535,630),
    "control_different_surface": (370,470,10,105),
}


def unit(vector):
    v=np.asarray(vector,dtype=float)
    norm=np.linalg.norm(v)
    if norm<1e-10 or not np.isfinite(norm):
        raise ValueError("Non-finite or zero normal")
    return v/norm


def angle_deg(a,b):
    return float(np.degrees(np.arccos(np.clip(unit(a)@unit(b),-1,1))))


def minimal_normal_alignment(before,after):
    """Smallest rotation mapping one background normal onto its prior value.

    Rotation about that background normal is UNKNOWN, not recovered.
    """
    a,b=unit(before),unit(after)
    cross=np.cross(b,a)
    sine=np.linalg.norm(cross)
    cosine=np.clip(b@a,-1,1)
    if sine<1e-10:
        if cosine<0:raise ValueError("Opposite normals have nonunique alignment")
        return np.eye(3)
    axis=cross/sine
    theta=np.arctan2(sine,cosine)
    x,y,z=axis
    k=np.array([[0,-z,y],[z,0,-x],[-y,x,0]])
    return np.eye(3)+np.sin(theta)*k+(1-np.cos(theta))*(k@k)


def compare_normals(board0,board1,background0,background1):
    raw=angle_deg(board0,board1)
    back_angle=angle_deg(background0,background1)
    corrected=angle_deg(board0,minimal_normal_alignment(
        background0,background1)@unit(board1))
    return {"uncorrected_grade_change_pct":100*math.tan(math.radians(raw)),
            "background_normal_change_deg":back_angle,
            "background_referenced_grade_change_pct":
                100*math.tan(math.radians(corrected)),
            "unknown_camera_rotation_around_background_normal":True}


def robust_plane(points):
    if len(points)<175:return None
    pts=np.asarray(points,float)
    center=pts.mean(0)
    for _ in range(6):
        centered=pts-center
        _,v=np.linalg.eigh(centered.T@centered)
        normal=v[:,0]
        resid=centered@normal
        scale=max(.001,1.4826*np.median(abs(resid-np.median(resid))))
        weights=1/np.maximum(1,abs(resid)/(2*scale))
        center=np.average(pts,axis=0,weights=weights)
        weighted=(pts-center)*np.sqrt(weights[:,None])
        _,v=np.linalg.eigh(weighted.T@weighted)
        normal=v[:,0]
    if normal[2]<0:normal=-normal
    residual=np.abs((pts-center)@normal)*1000
    return normal,float(np.percentile(residual,90))


def fit_frames(frames,rays,mask):
    normals=[];p90=[]
    for frame in frames:
        mm=frame[::3,::3].astype(float)
        ok=mask[::3,::3]&(mm>200)&(mm<5000)
        if ok.sum()<175:continue
        pts=rays[::3,::3][ok]*(mm[ok,None]/1000)
        fit=robust_plane(pts)
        if fit is not None:
            normals.append(fit[0])
            p90.append(fit[1])
    if len(normals)<6:return None
    n=unit(np.median(normals,axis=0))
    return {"n":n,"max_drift_deg":max(angle_deg(v,n) for v in normals),
            "p90_mm":float(np.median(p90))}


def median_map(frames):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore",RuntimeWarning)
        return np.nanmedian(np.where(frames>0,frames,np.nan),axis=0)


def largest_changed_surface(before,after):
    d=median_map(after)-median_map(before)
    valid=np.isfinite(d)
    moved=np.uint8(valid&(d<-20))
    moved=cv2.morphologyEx(moved,cv2.MORPH_OPEN,np.ones((5,5),np.uint8))
    moved=cv2.morphologyEx(moved,cv2.MORPH_CLOSE,np.ones((9,9),np.uint8))
    n,labels,stats,_=cv2.connectedComponentsWithStats(moved,8)
    if n<2:raise ValueError("No coherent moved-surface candidate")
    idx=1+int(np.argmax(stats[1:,cv2.CC_STAT_AREA]))
    if stats[idx,cv2.CC_STAT_AREA]<10000:
        raise ValueError("Moved-surface candidate too small")
    mask=cv2.erode(np.uint8(labels==idx),
                   np.ones((17,17),np.uint8))>0
    shared=(before>0).sum(0)>=len(before)-1
    shared&=(after>0).sum(0)>=len(after)-1
    mask&=shared
    if mask.sum()<6000:raise ValueError("No sufficiently shared foreground region")
    return mask,shared,d


def evaluate(path0,path1):
    if Path(path0).resolve()==Path(path1).resolve():
        raise ValueError("Two independent sessions are needed")
    cal0,frames0=read_session(path0)
    cal1,frames1=read_session(path1)
    for key in ("width","height","lens_intrinsic_calibration","lens_distortion"):
        if cal0[key]!=cal1[key]:
            raise ValueError("Camera calibration mismatch: "+key)
    frames0=frames0[np.any(frames0>0,axis=(1,2))]
    frames1=frames1[np.any(frames1>0,axis=(1,2))]
    if min(len(frames0),len(frames1))<6:
        raise ValueError("Too few nonzero DEPTH16 images")
    ray=rays_from_calibration(cal0)
    foreground,shared,delta=largest_changed_surface(frames0,frames1)
    board0=fit_frames(frames0,ray,foreground)
    board1=fit_frames(frames1,ray,foreground)
    if board0 is None or board1 is None:
        raise ValueError("Cannot fit moved-surface planes")

    candidates=[]
    for name,(y0,y1,x0,x1) in BACKGROUNDS.items():
        window=np.zeros(foreground.shape,dtype=bool)
        window[y0:y1,x0:x1]=True
        window &= shared & (~foreground) & np.isfinite(delta) & (abs(delta)<=8)
        if window.sum()<500:continue
        back0=fit_frames(frames0,ray,window)
        back1=fit_frames(frames1,ray,window)
        if back0 is None or back1 is None:continue
        stats=compare_normals(board0["n"],board1["n"],
                              back0["n"],back1["n"])
        stats.update({
            "window":name,"pixels":int(window.sum()),
            "median_background_depth_shift_mm":float(np.median(delta[window])),
            "baseline_board_background_angle_deg":
                angle_deg(board0["n"],back0["n"]),
            "median_background_plane_p90_mm":
                max(back0["p90_mm"],back1["p90_mm"]),
        })
        # Filter DOES NOT inspect resulting incline number.
        stats["geometrically_related_background"]=(
            stats["baseline_board_background_angle_deg"]<18 and
            stats["median_background_plane_p90_mm"]<12)
        stats["independently_verified_static_surface"]=False
        candidates.append(stats)
    eligible=[v for v in candidates if v["geometrically_related_background"]]
    grades=[v["background_referenced_grade_change_pct"] for v in eligible]
    return {
        "source_names":[Path(path0).name,Path(path1).name],
        "moved_surface_shared_pixels":int(foreground.sum()),
        "unadjusted_candidate_grade_pct":
            100*math.tan(math.radians(angle_deg(board0["n"],board1["n"]))),
        "within_capture_normal_max_drift_deg":
            [board0["max_drift_deg"],board1["max_drift_deg"]],
        "background_windows":candidates,
        "qualified_background_grade_range_pct":
            [min(grades),max(grades)] if grades else None,
        "qualified_reference_variation_pp":
            max(grades)-min(grades) if grades else None,
        "user_stated_setup":{
            "cardboard_length_cm_approx":100,
            "stacked_cardboard_rise_cm_approx":4,
            "actual_rise_measured":False,
            "support_span_measured":False,
            "known_grade_reference_available":False},
        "grade_accuracy_certified":False,
        "interpretation":"Cannot choose the background reference whose grade happens to match approximately 4%. A single plane normal cannot identify rotation about itself, and cardboard grade is not measured."
    }


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("level_zip",type=Path)
    p.add_argument("raised_zip",type=Path)
    p.add_argument("--output",type=Path)
    args=p.parse_args()
    results=json.dumps(evaluate(args.level_zip,args.raised_zip),
                       ensure_ascii=False,indent=2)
    if args.output:args.output.write_text(results,encoding="utf8")
    else:print(results)
