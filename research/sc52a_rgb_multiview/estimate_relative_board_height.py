"""Research only: plane-normal and background-adjusted board/floor depth delta.

Do not interpret a fitted plane as independently surveyed gravity, and do not
use estimated height to certify putting-slope accuracy. The subject mask is
defined by scene difference, never authenticated as a physical board.
Dependencies: numpy, scipy. No Android code or private data committed.
"""
from pathlib import Path
import argparse
import json
import math
import warnings
import zipfile

import numpy as np
from scipy import ndimage as ndi

def load_depth_stack(path):
    with zipfile.ZipFile(path) as z:
        roots={n.rsplit("/",1)[0]+"/" for n in z.namelist()
               if n.endswith("/camera2_calibration.json")}
        if len(roots)!=1:raise ValueError("Expected one archive with DEPTH16 camera calibration")
        root=roots.pop()
        cal=json.loads(z.read(root+"camera2_calibration.json"))
        summ=json.loads(z.read(root+"camera2_depth_summary.json"))
        rows=int(summ["frame_count"])
        w,h=int(cal["width"]),int(cal["height"])
        if rows<3 or rows>48 or w<=0 or h<=0:raise ValueError("Invalid frame geometry")
        arr=[]
        for i in range(1,rows+1):
            packed=np.frombuffer(z.read(root+f"depth_{i:04d}.bin"),dtype="<u2")
            if packed.size!=w*h:raise ValueError("Bad packed DEPTH16 frame size")
            arr.append((packed.reshape(h,w)&8191).astype("float64"))
        return np.stack(arr),cal,summ

def stable_temporal_distance(frames,minimum_fraction=.75,max_mad_mm=5):
    if frames.ndim!=3 or not 0<minimum_fraction<=1:
        raise ValueError("Bad frame count or valid fraction")
    a=np.where(frames>0,frames,np.nan)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore",RuntimeWarning)
        med=np.nanmedian(a,axis=0)
        mad=np.nanmedian(abs(a-med),axis=0)
    valid=np.sum(np.isfinite(a),axis=0)>=math.ceil(minimum_fraction*len(a))
    med[~valid | (mad>max_mad_mm)]=np.nan
    return med

def fit_normal_from_empty(empty_mm,mask,xn,yn,ray):
    sampled=np.zeros_like(mask,dtype=bool)
    sampled[::4,::4]=True
    m=mask & sampled & np.isfinite(empty_mm)
    if m.sum()<100:raise ValueError("Too few floor samples for normal fit")
    z=empty_mm[m]/ray[m]
    xyz=np.column_stack((xn[m]*z,yn[m]*z,z))
    matrix=np.column_stack((xyz[:,0],xyz[:,1],np.ones(len(xyz))))
    weights=np.ones(len(xyz))
    for _ in range(6):
        c=np.linalg.lstsq(matrix*weights[:,None],xyz[:,2]*weights,rcond=None)[0]
        residual=xyz[:,2]-matrix@c
        sigma=max(1.48*np.median(abs(residual)),2.0)
        weights=1/np.sqrt(1+(residual/(2*sigma))**2)
    n=np.array([-c[0],-c[1],1.0],dtype="float64")
    n/=np.linalg.norm(n)
    plane_residual=(xyz[:,2]-matrix@c)*n[2]
    return n,float(np.median(abs(plane_residual)))

def analyze_depth_pair(empty_mm,board_mm,intrinsics,real_measured_height_mm=None):
    if empty_mm.shape!=board_mm.shape or empty_mm.ndim!=2:
        raise ValueError("Camera images not aligned in pixel dimensions")
    h,w=board_mm.shape
    fx,fy,cx,cy=map(float,intrinsics[:4])
    if min(fx,fy)<=0:raise ValueError("Invalid intrinsics")
    y,x=np.mgrid[:h,:w]
    xn=(x-cx)/fx
    yn=(y-cy)/fy
    ray=np.sqrt(1+xn*xn+yn*yn)
    valid=np.isfinite(empty_mm)&np.isfinite(board_mm)
    delta_z=(board_mm-empty_mm)/ray
    candidate=valid&(delta_z<=-25)&(delta_z>=-130)
    labels,n=ndi.label(candidate,structure=np.array([[0,1,0],[1,1,1],[0,1,0]]))
    if n<1:raise ValueError("No connected depth-change candidate")
    areas=np.bincount(labels.ravel())
    largest=(labels==1+np.argmax(areas[1:]))
    inner=ndi.binary_erosion(largest,iterations=14)&valid
    if inner.sum()<100:raise ValueError("No adequately sized stable candidate core")
    ring=ndi.binary_dilation(largest,iterations=85)&(~ndi.binary_dilation(largest,iterations=15))&valid
    far=valid&(~ndi.binary_dilation(largest,iterations=60))
    if ring.sum()<1000:raise ValueError("No stable surrounding background")
    normal,plane_mad=fit_normal_from_empty(empty_mm,inner,xn,yn,ray)
    projection=normal[0]*xn+normal[1]*yn+normal[2]
    # Convert per-pixel optical-axis disparity into a distance along the
    # independently *fitted* EMPTY floor normal. No height calibration here.
    point_difference=delta_z*projection
    board_distance=float(np.nanmedian(point_difference[inner]))
    background_shift=float(np.nanmedian(point_difference[ring]))
    preliminary=-(board_distance-background_shift)
    boundary=ndi.binary_dilation(largest)&~largest
    unseen=int((boundary&~valid).sum())
    boundary_len=int(boundary.sum())
    yy,xx=np.where(largest)
    box=[int(xx.min()),int(yy.min()),int(xx.max()),int(yy.max())]
    clipped=bool(box[0]==0 or box[1]==0 or box[2]==w-1 or box[3]==h-1)
    unknown_frac=unseen/boundary_len if boundary_len else 1.
    report={
        "status":"preliminary_unverified_depth_difference",
        "candidate_identified_as_physical_board":False,
        "camera_translation_independently_verified":False,
        "camera_yaw_independently_verified":False,
        "depth_error_bound_calibrated":False,
        "slope_accuracy_certified":False,
        "estimated_perpendicular_change_mm_preliminary":round(preliminary,3),
        "operator_measured_vertical_height_mm":real_measured_height_mm,
        "comparison_is_not_accuracy_proof":True,
        "empty_floor_fitted_normal_camera_xyz":[round(float(v),6) for v in normal],
        "empty_floor_plane_fit_median_absolute_residual_mm":round(plane_mad,3),
        "candidate_core_px":int(inner.sum()),
        "candidate_outer_bbox_xyxy":box,
        "candidate_touches_image_edge":clipped,
        "candidate_unknown_neighbor_fraction":round(unknown_frac,5),
        "board_core_raw_projected_normal_delta_mm":round(board_distance,3),
        "surrounding_background_raw_projected_normal_shift_mm":round(background_shift,3),
        "ring_pixels":int(ring.sum()),
        "far_background_pixels":int(far.sum()),
        "paired_pixels":int(valid.sum()),
        "warning":"The mask may include nonboard surfaces; the physical camera pose, actual board region and distortion model have not been independently verified."
    }
    if clipped or unknown_frac>.15:
        report["status"]="unresolved_boundary_preliminary_height_only"
    if real_measured_height_mm is not None:
        report["preliminary_minus_operator_height_mm"]=round(preliminary-real_measured_height_mm,3)
        report["operator_height_did_not_tune_estimator"]=True
    # Sensitivity: vary how much of the candidate core is used and choose
    # ring or far-background shift. No automated precision claim from range.
    trials=[]
    for erosion in (8,12,14,20):
        m=ndi.binary_erosion(largest,iterations=erosion)&valid
        if m.sum()<100:continue
        for bg in (ring,far):
            if bg.sum()<1000:continue
            trials.append(float(-np.nanmedian(point_difference[m])+np.nanmedian(point_difference[bg])))
    report["roi_sensitivity_min_max_mm"]=[round(min(trials),3),round(max(trials),3)] if trials else None
    return report

def analyze_archives(empty_path,board_path,height=None):
    e,ec,_=load_depth_stack(empty_path)
    b,bc,_=load_depth_stack(board_path)
    names=("camera_id","width","height","lens_intrinsic_calibration","lens_distortion",
           "lens_pose_translation","lens_pose_rotation","sensor_timestamp_source")
    if any(ec.get(v)!=bc.get(v) for v in names):
        raise ValueError("Camera geometry mismatch")
    e=stable_temporal_distance(e)
    b=stable_temporal_distance(b)
    report=analyze_depth_pair(e,b,ec["lens_intrinsic_calibration"],height)
    report["empty_archive"]=Path(empty_path).name
    report["board_archive"]=Path(board_path).name
    report["independent_imu_pose_gate_not_performed_by_this_function"]=True
    return report

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--empty",type=Path,required=True)
    p.add_argument("--board",type=Path,required=True)
    p.add_argument("--operator-height-mm",type=float)
    p.add_argument("--output",type=Path)
    a=p.parse_args()
    r=analyze_archives(a.empty,a.board,a.operator_height_mm)
    payload=json.dumps(r,indent=2,ensure_ascii=False)+"\n"
    if a.output:a.output.write_text(payload,encoding="utf-8")
    else:print(payload,end="")
