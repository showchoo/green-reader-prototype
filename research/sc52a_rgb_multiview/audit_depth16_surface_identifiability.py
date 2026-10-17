#!/usr/bin/env python3
"""Conservative, read-only Camera2 DEPTH16 surface-identifiability gate.

Find image-space *isolated depth patches*, NEVER a semantic board, floor or
calibrated slope. A flat/curved depth image cannot identify a board without
observed discontinuities / external annotation. Private ZIP input stays local.
"""
import argparse
import json
import math
from collections import deque
from pathlib import Path
import statistics
import zipfile
from audit_depth16_confidence_stability import read_session

STEP=8
MIN_FRAMES=3
MAX_FRAMES=48

def median(v):
    return statistics.median(v) if v else None

def fit_plane(points):
    """Least-squares 1/Z = a*X/Z + b*Y/Z + c in camera normalized rays."""
    if len(points)<20:return None
    matrix=[[0.0]*4 for _ in range(3)]
    for nx,ny,z in points:
        v=(nx,ny,1.0)
        for i in range(3):
            for j in range(3):matrix[i][j]+=v[i]*v[j]
            matrix[i][3]+=v[i]/z
    # Gaussian elimination with pivoting.
    for i in range(3):
        k=max(range(i,3),key=lambda r:abs(matrix[r][i]))
        if abs(matrix[k][i])<1e-12:return None
        matrix[i],matrix[k]=matrix[k],matrix[i]
        t=matrix[i][i]
        for j in range(i,4):matrix[i][j]/=t
        for k in range(3):
            if k==i:continue
            m=matrix[k][i]
            for j in range(i,4):matrix[k][j]-=m*matrix[i][j]
    return [matrix[i][3] for i in range(3)]

def predicted_z(beta,nx,ny):
    denom=beta[0]*nx+beta[1]*ny+beta[2]
    return 1.0/denom if denom>0 else None

def sample_grid(session):
    frames=session["raw_frames"]
    w,h=session["width"],session["height"]
    intrinsic=session.get("intrinsics")
    # The official app stores Camera2 intrinsics. No silently invented FOV.
    if not isinstance(intrinsic,list) or len(intrinsic)<4:
        return None,"intrinsics_missing"
    fx,fy,cx,cy=map(float,intrinsic[:4])
    if not all(math.isfinite(x) for x in (fx,fy,cx,cy)) or fx<=0 or fy<=0:
        return None,"intrinsics_invalid"
    if not (MIN_FRAMES<=len(frames)<=MAX_FRAMES):
        return None,"insufficient_nonempty_frames"
    nxgrid=(w+STEP-1)//STEP
    nygrid=(h+STEP-1)//STEP
    count=max(MIN_FRAMES,math.ceil(0.70*len(frames)))
    points={}
    for gy in range(nygrid):
        y=min(gy*STEP+STEP//2,h-1)
        for gx in range(nxgrid):
            x=min(gx*STEP+STEP//2,w-1)
            idx=y*w+x
            ranges=[int(f[idx])&8191 for f in frames if (int(f[idx])&8191)!=0]
            if len(ranges)<count:continue
            radial_mm=median(ranges)
            xn=(x-cx)/fx;yn=(y-cy)/fy
            # Android DEPTH16's reported distance is radial from camera.
            # Convert to optical-axis Z before testing plane continuity.
            z=radial_mm/math.sqrt(1+xn*xn+yn*yn)
            points[(gx,gy)]=(xn,yn,z)
    return (nxgrid,nygrid,points),None

def analyze_session(session):
    """Never certifies semantic class, sensor confidence, physical slope or pose."""
    output={
        "source":session["source"],
        "status":"unresolved","reason":"not_analyzed",
        "semantic_board_identified":False,
        "slope_accuracy_certified":False,
        "pose_certified":False,
        "confidence_calibrated":False,
        "surface_mask_released":False}
    grid,reason=sample_grid(session)
    if grid is None:
        output["reason"]=reason
        return output
    nx,ny,p=grid
    output["grid_size"]=[nx,ny]
    output["temporally_supported_grid_samples"]=len(p)
    if len(p)<nx*ny*.20:
        output["reason"]="insufficient_temporal_depth_coverage"
        return output
    cx,cy=nx//2,ny//2
    # Fit in a conservative central 20% box, not the entire image.
    r_x=max(2,nx//10);r_y=max(2,ny//10)
    core=[v for (x,y),v in p.items()
          if abs(x-cx)<=r_x and abs(y-cy)<=r_y]
    beta=fit_plane(core)
    if beta is None:
        output["reason"]="central_plane_not_identifiable"
        return output
    def resid(item):
        if item not in p:return None
        x,y,z=p[item];pred=predicted_z(beta,x,y)
        return None if pred is None else z-pred
    # Robust refit trims extreme central outliers, but does not invent board labels.
    residuals=[(abs(z-predicted_z(beta,x,y)),(x,y,z)) for x,y,z in core
               if predicted_z(beta,x,y) is not None]
    if len(residuals)<20:
        output["reason"]="unstable_plane_model"
        return output
    trimmed=[v for _,v in sorted(residuals,key=lambda t:t[0])[:max(20,int(len(residuals)*.8))]]
    beta=fit_plane(trimmed)
    if beta is None:
        output["reason"]="unstable_plane_model"
        return output
    seed_residual=[abs(z-predicted_z(beta,x,y)) for x,y,z in trimmed
                   if predicted_z(beta,x,y) is not None]
    output["central_plane_median_abs_residual_mm"]=round(median(seed_residual),3)
    if output["central_plane_median_abs_residual_mm"]>10:
        output["reason"]="central_patch_nonplanar_or_noisy"
        return output
    tolerance=max(8.0,min(18.0,3*median(seed_residual)+5.0))
    output["plane_membership_tolerance_mm"]=round(tolerance,2)
    def ismember(item):
        v=resid(item)
        return v is not None and abs(v)<=tolerance
    start=(cx,cy)
    if not ismember(start):
        near=[(x,y) for (x,y) in p if abs(x-cx)<=2 and abs(y-cy)<=2 and ismember((x,y))]
        if not near:
            output["reason"]="center_not_on_stable_patch"
            return output
        start=min(near,key=lambda k:(k[0]-cx)**2+(k[1]-cy)**2)
    selected={start};q=deque([start])
    directions=((1,0),(-1,0),(0,1),(0,-1))
    while q:
        x,y=q.popleft()
        for dx,dy in directions:
            node=(x+dx,y+dy)
            if node in p and node not in selected and ismember(node):
                selected.add(node);q.append(node)
    output["patch_grid_samples"]=len(selected)
    output["patch_percent_of_grid"]=round(100*len(selected)/(nx*ny),2)
    if len(selected)<max(30,int(nx*ny*.05)):
        output["reason"]="patch_too_small"
        return output
    if len(selected)>int(nx*ny*.75):
        output["reason"]="scene_wide_surface_cannot_identify_board"
        return output
    box=(min(x for x,y in selected),min(y for x,y in selected),
         max(x for x,y in selected),max(y for x,y in selected))
    output["patch_bbox_grid"]=box
    if box[0]<=1 or box[1]<=1 or box[2]>=nx-2 or box[3]>=ny-2:
        output["reason"]="patch_touches_image_edge"
        return output
    # Require an observable, strong discontinuity along EACH cardinal side.
    # A smooth model residual cutoff is NOT a physical board boundary.
    sides={side:{"boundary":0,"valid_outside":0,"strong_step":0} for side in ("left","right","top","bottom")}
    for x,y in selected:
        for dx,dy in directions:
            outside=(x+dx,y+dy)
            if outside in selected:continue
            side="left" if dx<0 else "right" if dx>0 else "top" if dy<0 else "bottom"
            sides[side]["boundary"]+=1
            if outside not in p:continue
            sides[side]["valid_outside"]+=1
            v=resid(outside)
            u=resid((x,y))
            # Signed plane-relative step across an actual neighboring pair.
            if v is not None and u is not None and abs(v-u)>=35.0:
                sides[side]["strong_step"]+=1
    output["boundary_evidence"]={}
    all_sides=True
    for side,counts in sides.items():
        denominator=counts["boundary"]
        observed=counts["valid_outside"]/denominator if denominator else 0
        supported=counts["strong_step"]/denominator if denominator else 0
        output["boundary_evidence"][side]={
            "boundary_edges":denominator,
            "valid_outside_fraction":round(observed,3),
            "depth_step_at_least_35mm_fraction":round(supported,3)}
        if denominator<3 or observed<.75 or supported<.65:all_sides=False
    if not all_sides:
        output["reason"]="no_four_sided_depth_discontinuity"
        return output
    # Even four discontinuities identify an isolated depth patch, not "board".
    output["status"]="isolated_depth_patch_candidate"
    output["reason"]="image_space_boundary_only_not_semantic_board"
    return output

def audit(*paths):
    if not (1<=len(paths)<=2):raise ValueError("Expected one or two ZIP paths")
    sessions=[read_session(Path(path)) for path in paths]
    answers=[analyze_session(s) for s in sessions]
    result={
        "sessions":answers,
        "independent_board_identity_verified":False,
        "physical_slope_accuracy_certified":False,
        "recommendation":"Do not feed research depth masks into production putting."}
    if len(sessions)==2:
        compatible=all(sessions[0][key]==sessions[1][key]
                       for key in ("camera_id","width","height","intrinsics","sensor_orientation_degrees"))
        result["capture_geometry_compatible"]=compatible
        result["same_physical_patch_verified"]=False
        # A shape match still cannot independently verify phone pose or board.
        result["paired_board_segmentation_approved"]=False
    return result

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("zip",type=Path,nargs="+")
    p.add_argument("--output",type=Path,help="Optional local JSON file; do not upload private ZIPs")
    a=p.parse_args()
    try:doc=json.dumps(audit(*a.zip),ensure_ascii=False,indent=2)+"\n"
    except (ValueError,KeyError,zipfile.BadZipFile) as exc:p.error(str(exc))
    if a.output:a.output.write_text(doc,encoding="utf-8")
    else:print(doc,end="")
