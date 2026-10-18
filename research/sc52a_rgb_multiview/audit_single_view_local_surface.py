"""Experimental single-view DEPTH16 surface-bias diagnostic. NOT a putt meter.

A manually defined exclusion ROI is treated only as a putative board, never as
an objectively detected object. Fit a local smooth empty-floor *hypothesis*
around it; extrapolate into the ROI, and project the residual to a fitted
surface tangent normal. A single depth image cannot independently prove
gravity, surface flatness, camera translation, hardware calibration or grade.

Crucially, evaluate IDENTICAL ROIs on controls known to contain no board.
Neither board height nor expected 35/70mm outcomes ever enter the estimator.
Uses only numpy and the already-existing private ZIP reader, if CLI invoked.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from estimate_relative_board_height import load_depth_stack, stable_temporal_distance

def box_mask(shape,box):
    height,width=shape
    x0,x1,y0,y1=map(int,box)
    if not (0<=x0<x1<=width and 0<=y0<y1<=height):
        raise ValueError("Invalid explicitly supplied region")
    m=np.zeros((height,width),dtype=bool)
    m[y0:y1,x0:x1]=True
    return m

def estimate_local_surface(depth_mm,intrinsics,outer,excluded,inner,degree=3,step=4):
    """Unverified local normal-distance contrast; unit is millimetres."""
    if depth_mm.ndim!=2:raise ValueError("Expected 2D DEPTH16 median image")
    h,w=depth_mm.shape
    if degree not in (2,3,4,5) or step not in (2,3,4,6):
        raise ValueError("Unsupported research configuration")
    o=box_mask(depth_mm.shape,outer)
    e=box_mask(depth_mm.shape,excluded)
    i=box_mask(depth_mm.shape,inner)
    if np.any(i&~e) or np.any(e&~o):raise ValueError("ROI geometry not nested")
    fx,fy,cx,cy=map(float,intrinsics[:4])
    if min(fx,fy)<=0:raise ValueError("Invalid camera intrinsics")
    yy,xx=np.indices((h,w))
    nx=(xx-cx)/fx
    ny=(yy-cy)/fy
    optical_z=depth_mm/np.sqrt(1+nx*nx+ny*ny)
    # Normalize pixel coordinates for stable polynomial regression.
    u=(xx-w/2)/(w/2)
    v=(yy-h/2)/(h/2)
    valid=np.isfinite(optical_z)&(optical_z>0)
    train=o&~e&valid&(xx%step==0)&(yy%step==0)
    test=i&valid
    if int(train.sum())<max(80,(degree+1)*(degree+2)*6):
        raise ValueError("Insufficient surrounding depth samples")
    if test.sum()<60:raise ValueError("Insufficient board-candidate core")
    powers=[(a,b) for a in range(degree+1) for b in range(degree+1-a)]
    A=np.column_stack([u[train]**a*v[train]**b for a,b in powers])
    observed=optical_z[train]
    weights=np.ones_like(observed)
    for _ in range(10):
        coeff=np.linalg.lstsq(A*weights[:,None],observed*weights,rcond=None)[0]
        residual=observed-A@coeff
        sigma=max(float(np.median(np.abs(residual))*1.4826),1.)
        weights=1/np.sqrt(1+(residual/(2*sigma))**2)
    # Evaluate predicted floor only where needed; don't emit user pixels.
    def value_and_deriv(uuu,vvv):
        z=sum(c*(uuu**a)*(vvv**b) for c,(a,b) in zip(coeff,powers))
        du=sum(c*a*(uuu**(a-1))*vvv**b for c,(a,b) in zip(coeff,powers) if a)
        dv=sum(c*b*uuu**a*(vvv**(b-1)) for c,(a,b) in zip(coeff,powers) if b)
        return z,du/(w/2),dv/(h/2)
    centerx=float(np.median(xx[i]))
    centery=float(np.median(yy[i]))
    ux=(centerx-w/2)/(w/2)
    vy=(centery-h/2)/(h/2)
    z,dx,dy=value_and_deriv(ux,vy)
    nxx=(centerx-cx)/fx
    nyy=(centery-cy)/fy
    qx=dx*fx
    qy=dy*fy
    tangent_x=np.array([z+nxx*qx,nyy*qx,qx],dtype=float)
    tangent_y=np.array([nxx*qy,z+nyy*qy,qy],dtype=float)
    normal=np.cross(tangent_x,tangent_y)
    norm=np.linalg.norm(normal)
    if norm<1e-8:raise ValueError("Degenerate fitted surface tangent")
    normal/=norm
    predicted,_,_=value_and_deriv(u[test],v[test])
    projected=normal[0]*nx[test]+normal[1]*ny[test]+normal[2]
    delta_mm=(predicted-optical_z[test])*projected
    mads=np.abs(residual)
    return {
        "status":"unverified_manually_selected_single_view_contrast",
        "local_normal_projected_contrast_mm":round(float(np.median(delta_mm)),3),
        "candidate_interior_iqr_mm":[round(float(v),3) for v in np.percentile(delta_mm,[25,75])],
        "surrounding_model_fit_median_abs_residual_mm":round(float(np.median(mads)),3),
        "train_pixels":int(train.sum()),"interior_pixels":int(test.sum()),
        "fit_degree":degree,
        "outer_xyxy":list(map(int,outer)),
        "excluded_xyxy":list(map(int,excluded)),
        "inner_xyxy":list(map(int,inner)),
        "operator_board_identity_verified":False,
        "real_surface_height_independently_verified":False,
        "camera_translation_independently_verified":False,
        "physical_grade_accuracy_certified":False,
        "warning":"Manual ROI, learned optical curvature and fitted normal can bias result. Run blank-scene negative controls and multiple ROIs."
    }

def sensitivity(depth_mm,intrinsics,models):
    trials=[]
    for model in models:
        for degree in (3,4,5):
            report=estimate_local_surface(depth_mm,intrinsics,
                model["outer"],model["excluded"],model["inner"],degree)
            trials.append({"roi_name":model["name"],
                           "fit_degree":degree,
                           "contrast_mm":report["local_normal_projected_contrast_mm"],
                           "background_mad_mm":report["surrounding_model_fit_median_abs_residual_mm"]})
    valid=[v["contrast_mm"] for v in trials]
    # Never interpret a stable median as independently calibrated accuracy.
    return {
        "status":"research_uncalibrated_roi_sensitivity_only",
        "median_apparent_contrast_mm":round(float(np.median(valid)),3),
        "min_max_apparent_contrast_mm":[round(float(min(valid)),3),round(float(max(valid)),3)],
        "trial_count":len(valid),"trials":trials,
        "physical_height_or_slope_accuracy_certified":False,
        "warning":"Do not discard unstable ROI choices post-hoc or tune against operator board height."
    }

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("archive",type=Path)
    p.add_argument("--outer",nargs=4,type=int,required=True)
    p.add_argument("--exclude",nargs=4,type=int,required=True)
    p.add_argument("--inner",nargs=4,type=int,required=True)
    p.add_argument("--degree",type=int,default=3,choices=(2,3,4,5))
    p.add_argument("--output",type=Path)
    a=p.parse_args()
    frames,cal,_=load_depth_stack(a.archive)
    med=stable_temporal_distance(frames)
    result=estimate_local_surface(med,cal["lens_intrinsic_calibration"],
        a.outer,a.exclude,a.inner,a.degree)
    result["archive_name"]=a.archive.name
    payload=json.dumps(result,ensure_ascii=False,indent=2)+"\n"
    if a.output:a.output.write_text(payload,encoding="utf-8")
    else:print(payload,end="")
