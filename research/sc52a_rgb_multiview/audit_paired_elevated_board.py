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
    if ga is None or aa is None or ga>MAX_GRAVITY_DIFFERENCE_DEG or aa>MAX_ACCELEROMETER_DIFFERENCE_DEG:
        result["reason"]="camera_orientation_drift_cannot_be_excluded";return result
    width,height=e["width"],e["height"]
    fx,fy,cx,cy=map(float,intr[:4])
    required_e=max(3,math.ceil(len(e["raw_frames"])*MIN_RETAINED_FRACTION))
    required_b=max(3,math.ceil(len(b["raw_frames"])*MIN_RETAINED_FRACTION))
    candidates=set();background=[];deltas=[]
    valid_pairs=0
    total=((height+STEP-1)//STEP)*((width+STEP-1)//STEP)
    for gy,y in enumerate(range(0,height,STEP)):
        for gx,x in enumerate(range(0,width,STEP)):
            idx=y*width+x
            de=frame_median_at(e["raw_frames"],idx,required_e)
            db=frame_median_at(b["raw_frames"],idx,required_b)
            if de is None or db is None:continue
            valid_pairs+=1
            nx=(x-cx)/fx;ny=(y-cy)/fy
            factor=math.sqrt(1+nx*nx+ny*ny)
            dz=(db-de)/factor # relative optical-axis depth, NOT measured rise
            deltas.append(dz)
            if abs(dz)<=12:background.append(dz)
            elif BOARD_Z_DELTA_RANGE[0]<=dz<=BOARD_Z_DELTA_RANGE[1]:
                candidates.add((gx,gy))
    result["sampled_overlap_pixels"]=valid_pairs
    result["sampled_grid_pixels"]=total
    result["paired_valid_fraction"]=round0(valid_pairs/total)
    result["candidate_range_change_pixels"]=len(candidates)
    result["near_zero_background_pixels"]=len(background)
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
        result["reason"]="candidate_fraction_not_plausible";return result
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
    if bbox[0]<=2 or bbox[1]<=2 or bbox[2]>=gxmax-2 or bbox[3]>=gymax-2:
        result["reason"]="depth_change_touches_image_edge";return result
    result["depth_change_median_optical_z_mm"]=round0(
        percentile([d for d in deltas if BOARD_Z_DELTA_RANGE[0]<=d<=BOARD_Z_DELTA_RANGE[1]],50),3)
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
