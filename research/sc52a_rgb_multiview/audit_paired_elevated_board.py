#!/usr/bin/env python3
"""OFFLINE v11.3 no-board versus elevated-board DEPTH16 difference audit.

Labels --empty and --board are USER SUPPLIED, not visually verified.
The tool deliberately refuses to certify board identity or millimetre/grade
accuracy. Gravity-angle agreement does NOT prove camera translation/yaw absent.
Private depth, IMU and pixels remain local and are never committed to GitHub.
"""
import argparse
from collections import deque
import json
import math
from pathlib import Path
import statistics
import zipfile

from audit_depth16_confidence_stability import read_session
from audit_depth16_imu_stability import analyze as analyze_imu,angle_deg

STEP=8
MIN_RETAINED_FRACTION=.75
MAX_TEMPORAL_MAD_MM=5
MAX_GRAVITY_DIFFERENCE_DEG=.15
MAX_ACCELEROMETER_DIFFERENCE_DEG=.20
MIN_VALID_PAIR_FRACTION=.50
MIN_BACKGROUND_FRACTION=.20
MIN_CANDIDATE_FRACTION=.05
MAX_CANDIDATE_FRACTION=.70
MIN_COMPONENT_DOMINANCE=.75
MIN_COMPONENT_PIXELS=60
BOARD_Z_DELTA_RANGE=(-105,-25) # millimetres, candidate only, NOT vertical rise

def round0(x,n=4):
    return None if x is None else round(x,n)

def percentile(data,p):
    if not data:return None
    values=sorted(data)
    n=(len(values)-1)*p/100
    i=int(n);j=min(i+1,len(values)-1)
    return values[i]*(j-n)+values[j]*(n-i)

def source_calibration(path):
    with zipfile.ZipFile(path) as z:
        names=[n for n in z.namelist() if n.endswith("/camera2_calibration.json")]
        if len(names)!=1:raise ValueError("Missing or ambiguous camera calibration")
        return json.loads(z.read(names[0]))

def frame_median_at(frames,index,needed):
    vals=[int(f[index])&8191 for f in frames]
    good=[v for v in vals if v>0]
    if len(good)<needed:return None
    med=statistics.median(good)
    mad=statistics.median(abs(t-med) for t in good)
    return med if mad<=MAX_TEMPORAL_MAD_MM else None

def persistent_count(frames,index):
    """Valid repeated depth samples, without claiming distance confidence."""
    return sum(bool(int(frame[index])&8191) for frame in frames)

def dropout_geometry(lost,baseline_good,grid_w,grid_h):
    """Diagnostic missing-depth shape; NEVER an inferred board silhouette."""
    report={"baseline_valid_board_missing_grid_cells":len(lost),
            "lost_depth_component_bbox_grid":None,
            "lost_depth_component_cells":0,
            "lost_depth_component_share":0.0,
            "lost_depth_touches_baseline_blind_zone":False,
            "lost_depth_touches_frame_edge":False,
            "dropout_is_board_silhouette_verified":False}
    groups=components(lost)
    if not groups:return report
    main=groups[0]
    report["lost_depth_component_cells"]=len(main)
    report["lost_depth_component_share"]=round0(len(main)/len(lost),4)
    xs=[k[0] for k in main];ys=[k[1] for k in main]
    report["lost_depth_component_bbox_grid"]=[min(xs),min(ys),max(xs),max(ys)]
    report["lost_depth_touches_frame_edge"]=min(xs)==0 or min(ys)==0 or max(xs)==grid_w-1 or max(ys)==grid_h-1
    report["lost_depth_touches_baseline_blind_zone"]=any(
        (gx+dx,gy+dy) not in baseline_good
        for gx,gy in main for dx,dy in ((1,0),(-1,0),(0,1),(0,-1))
        if 0<=gx+dx<grid_w and 0<=gy+dy<grid_h)
    return report

def candidate_contour_observability(component,paired_good):
    """Count visible/missing adjacent pixels around candidate boundary (grid)."""
    neighbors=((1,0),(-1,0),(0,1),(0,-1))
    sides={side:{"total":0,"unobserved":0} for side in ("left","right","top","bottom")}
    for x,y in component:
        for dx,dy in neighbors:
            outside=(x+dx,y+dy)
            if outside in component:continue
            side="left" if dx<0 else "right" if dx>0 else "top" if dy<0 else "bottom"
            sides[side]["total"]+=1
            if outside not in paired_good:
                sides[side]["unobserved"]+=1
    total=sum(v["total"] for v in sides.values())
    unseen=sum(v["unobserved"] for v in sides.values())
    return {
        "candidate_boundary_edges_total":total,
        "candidate_boundary_edges_unobserved":unseen,
        "candidate_boundary_unobserved_fraction":round0(unseen/total) if total else 1.0,
        "candidate_boundary_by_side":sides,
        "candidate_four_sides_observable":bool(total and all(v["total"]>0 and
            v["unobserved"]/v["total"]<=.15 for v in sides.values()))
    }

def components(nodes):
    remaining=set(nodes)
    result=[]
    while remaining:
        root=remaining.pop()
        selected={root};queue=deque([root])
        while queue:
            gx,gy=queue.popleft()
            for p in ((gx-1,gy),(gx+1,gy),(gx,gy-1),(gx,gy+1)):
                if p in remaining:
                    remaining.remove(p);selected.add(p);queue.append(p)
        result.append(selected)
    return sorted(result,key=len,reverse=True)

def analyze_pair(empty_zip,board_zip):
    empty_zip,board_zip=Path(empty_zip),Path(board_zip)
    result={
        "empty_capture":empty_zip.name,"board_capture":board_zip.name,
        "status":"unresolved","reason":"not_checked",
        "board_identity_verified":False,
        "board_corner_coordinates_verified":False,
        "camera_translation_independently_verified":False,
        "camera_yaw_independently_verified":False,
        "vendor_depth_confidence_calibrated":False,
        "measured_board_height_mm":None,
        "physical_grade_accuracy_certified":False,
        "production_putting_usable":False,
        "labels_supplied_by_operator_not_independently_verified":True
    }
    if empty_zip.resolve()==board_zip.resolve():
        result["reason"]="same_archive_for_both_roles";return result
    e,b=read_session(empty_zip),read_session(board_zip)
    cal_e,cal_b=source_calibration(empty_zip),source_calibration(board_zip)
    fields=("camera_id","width","height","sensor_orientation_degrees",
            "lens_intrinsic_calibration","lens_distortion",
            "lens_pose_translation","lens_pose_rotation","sensor_timestamp_source")
    if any(cal_e.get(k)!=cal_b.get(k) for k in fields):
        result["reason"]="camera_intrinsic_or_extrinsic_mismatch";return result
    intr=cal_e.get("lens_intrinsic_calibration")
    if not isinstance(intr,list) or len(intr)<4 or not all(
            type(x) in (int,float) and math.isfinite(x) for x in intr[:4]
    ) or intr[0]<=0 or intr[1]<=0:
        result["reason"]="camera_ray_calibration_missing";return result
    result["same_camera_geometry_metadata"]=True
    ie,ib=analyze_imu(empty_zip),analyze_imu(board_zip)
    for x in (ie,ib):
        if not x["camera_sensor_timebases_comparable"] or not x["raw_motion_diagnostics_available"]:
            result["reason"]="imu_evidence_insufficient";return result
        for kind in ("gravity","accelerometer"):
            if x["directional_streams"][kind]["capture_end_median_xyz"] is None:
                result["reason"]="imu_capture_end_missing";return result
    ga=angle_deg(ie["directional_streams"]["gravity"]["capture_end_median_xyz"],
                 ib["directional_streams"]["gravity"]["capture_end_median_xyz"])
    aa=angle_deg(ie["directional_streams"]["accelerometer"]["capture_end_median_xyz"],
                 ib["directional_streams"]["accelerometer"]["capture_end_median_xyz"])
    result["gravity_end_direction_delta_deg"]=round0(ga,5)
    result["accelerometer_end_direction_delta_deg"]=round0(aa,5)
    # Even when the pose guard fails, compute READ-ONLY image difference
    # evidence for debugging. Never promote it to a verified board candidate.
    orientation_guard_passed=(ga is not None and aa is not None and
        ga<=MAX_GRAVITY_DIFFERENCE_DEG and aa<=MAX_ACCELEROMETER_DIFFERENCE_DEG)
    result["camera_orientation_guard_passed"]=orientation_guard_passed
    width,height=e["width"],e["height"]
    fx,fy,cx,cy=map(float,intr[:4])
    required_e=max(3,math.ceil(len(e["raw_frames"])*MIN_RETAINED_FRACTION))
    required_b=max(3,math.ceil(len(b["raw_frames"])*MIN_RETAINED_FRACTION))
    candidates=set();background=[];deltas=[]
    baseline_good=set();paired_good=set();lost_depth=set();gained_depth=set()
    grid_w=(width+STEP-1)//STEP
    grid_h=(height+STEP-1)//STEP
    valid_pairs=0
    total=((height+STEP-1)//STEP)*((width+STEP-1)//STEP)
    for gy,y in enumerate(range(0,height,STEP)):
        for gx,x in enumerate(range(0,width,STEP)):
            idx=y*width+x
            de=frame_median_at(e["raw_frames"],idx,required_e)
            db=frame_median_at(b["raw_frames"],idx,required_b)
            key=(gx,gy)
            if de is not None:baseline_good.add(key)
            if de is not None and db is None and persistent_count(b["raw_frames"],idx)<=len(b["raw_frames"])//4:
                lost_depth.add(key)
            if de is None and db is not None and persistent_count(e["raw_frames"],idx)<=len(e["raw_frames"])//4:
                gained_depth.add(key)
            if de is None or db is None:continue
            paired_good.add(key)
            valid_pairs+=1
            nx=(x-cx)/fx;ny=(y-cy)/fy
            factor=math.sqrt(1+nx*nx+ny*ny)
            dz=(db-de)/factor # relative optical-axis depth, NOT measured rise
            deltas.append(dz)
            if abs(dz)<=12:background.append(dz)
            elif BOARD_Z_DELTA_RANGE[0]<=dz<=BOARD_Z_DELTA_RANGE[1]:
                candidates.add((gx,gy))
    result.update(dropout_geometry(lost_depth,baseline_good,grid_w,grid_h))
    result["newly_valid_grid_cells"]=len(gained_depth)
    result["baseline_persistently_valid_grid_cells"]=len(baseline_good)
    result["lost_fraction_of_baseline_valid"]=round0(len(lost_depth)/len(baseline_good)) if baseline_good else None
    result["sampled_overlap_pixels"]=valid_pairs
    result["sampled_grid_pixels"]=total
    result["paired_valid_fraction"]=round0(valid_pairs/total)
    result["candidate_range_change_pixels"]=len(candidates)
    result["unverified_candidate_optical_z_delta_median_mm"]=round0(percentile(
        [d for d in deltas if BOARD_Z_DELTA_RANGE[0]<=d<=BOARD_Z_DELTA_RANGE[1]],50),3)
    result["near_zero_background_pixels"]=len(background)
    result["image_space_evidence_only"]=True
    if valid_pairs<total*MIN_VALID_PAIR_FRACTION:
        result["reason"]="insufficient_valid_common_depth";return result
    if len(background)<valid_pairs*MIN_BACKGROUND_FRACTION:
        result["reason"]="unmodified_background_not_observed";return result
    result["background_median_absolute_delta_mm"]=round0(statistics.median(
        abs(v) for v in background),3)
    if result["background_median_absolute_delta_mm"]>6:
        result["reason"]="background_inconsistent";return result
    fraction=len(candidates)/valid_pairs
    result["candidate_fraction_of_matched"]=round0(fraction,5)
    if not MIN_CANDIDATE_FRACTION<=fraction<=MAX_CANDIDATE_FRACTION:
        if fraction<MIN_CANDIDATE_FRACTION and result["lost_depth_component_cells"]>=25:
            result["reason"]="depth_disappearance_observed_without_confirmed_range_step"
        else:
            result["reason"]="candidate_fraction_not_plausible"
        return result
    groups=components(candidates)
    if not groups or len(groups[0])<MIN_COMPONENT_PIXELS:
        result["reason"]="no_large_contiguous_depth_change";return result
    primary=groups[0]
    result["largest_component_pixel_count"]=len(primary)
    result["largest_component_share"]=round0(len(primary)/len(candidates),4)
    if len(primary)/len(candidates)<MIN_COMPONENT_DOMINANCE:
        result["reason"]="multiple_unrelated_depth_changes";return result
    xx=[x for x,y in primary];yy=[y for x,y in primary]
    gxmax=(width-1)//STEP;gymax=(height-1)//STEP
    bbox=[min(xx),min(yy),max(xx),max(yy)]
    result["candidate_bbox_grid"]=bbox
    result.update(candidate_contour_observability(primary,paired_good))
    if bbox[0]<=2 or bbox[1]<=2 or bbox[2]>=gxmax-2 or bbox[3]>=gymax-2:
        result["reason"]="depth_change_touches_image_edge";return result
    result["depth_change_median_optical_z_mm"]=round0(
        percentile([d for d in deltas if BOARD_Z_DELTA_RANGE[0]<=d<=BOARD_Z_DELTA_RANGE[1]],50),3)
    if not result["candidate_four_sides_observable"]:
        result["reason"]="candidate_boundary_depth_unobserved";return result
    if not orientation_guard_passed:
        result["reason"]="camera_orientation_drift_cannot_be_excluded";return result
    result["status"]="unverified_board_like_depth_change_candidate"
    result["reason"]="image_change_observed_but_physical_board_and_pose_unproven"
    return result

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--empty",type=Path,required=True,help="Empty-floor v11.3 Session ZIP")
    p.add_argument("--board",type=Path,required=True,help="Same-mount board-added Session ZIP")
    p.add_argument("--output",type=Path,help="Private JSON report; no raw images")
    a=p.parse_args()
    try:report=json.dumps(analyze_pair(a.empty,a.board),ensure_ascii=False,indent=2)+"\n"
    except (ValueError,KeyError,zipfile.BadZipFile) as err:p.error(str(err))
    if a.output:a.output.write_text(report,encoding="utf-8")
    else:print(report,end="")
