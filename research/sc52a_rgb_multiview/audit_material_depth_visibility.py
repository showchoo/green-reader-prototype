"""Read-only material-sensitive DEPTH16 step visibility audit.

Manually annotated surface ROI, independent unchanged background ROI. If a
physically present elevated surface is not separated in *recorded* DEPTH16,
flag the apparent range failure, NOT that the object is proven transparent.

An opaque-looking image-space depth step does not imply correct real board
height, a physical camera pose lock, ToF model, or slope accuracy.
No user raw measurement files in this repository.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from estimate_relative_board_height import load_depth_stack,stable_temporal_distance
from audit_depth16_imu_stability import analyze as analyze_imu,angle_deg

def rectangle(shape,box):
    height,width=shape
    if len(box)!=4:raise ValueError("Expected xyxy bounds")
    x0,y0,x1,y1=map(int,box)
    if not 0<=x0<x1<=width or not 0<=y0<y1<=height:
        raise ValueError("Invalid image rectangle")
    m=np.zeros(shape,dtype=bool)
    m[y0:y1,x0:x1]=True
    return m

def audit_images(empty_mm,board_mm,intrinsics,subject_box,background_box,operator_rise_mm=None):
    if empty_mm.shape!=board_mm.shape or empty_mm.ndim!=2:
        raise ValueError("Unaligned depth arrays")
    subject=rectangle(empty_mm.shape,subject_box)
    background=rectangle(empty_mm.shape,background_box)
    if np.any(subject&background):
        raise ValueError("Subject and background regions must not overlap")
    fx,fy,cx,cy=map(float,intrinsics[:4])
    if min(fx,fy)<=0:raise ValueError("Invalid intrinsics")
    yy,xx=np.indices(empty_mm.shape)
    ray=np.sqrt(1+((xx-cx)/fx)**2+((yy-cy)/fy)**2)
    diff=(board_mm-empty_mm)/ray
    good=np.isfinite(diff)
    s=diff[subject&good]
    b=diff[background&good]
    if len(s)<100 or len(b)<100:
        raise ValueError("Insufficient stable overlapping depth samples")
    if np.mean(good[subject])<.8 or np.mean(good[background])<.8:
        raise ValueError("Insufficient area coverage for a material visibility audit")
    bg_shift=float(np.median(b))
    corrected=s-bg_shift
    med=float(np.median(corrected))
    negative_25_frac=float(np.mean(corrected<=-25))
    near_zero_frac=float(np.mean(np.abs(corrected)<=12))
    if operator_rise_mm is not None and not 0<operator_rise_mm<=300:
        raise ValueError("Operator-reported physical separation out of research range")
    # This is VISIBILITY, not independent height estimation.
    # Without a known rise we can only report raw appearance.
    if operator_rise_mm is not None and operator_rise_mm>=25 and near_zero_frac>=.95 and negative_25_frac<=.01:
        status="operator_elevated_surface_not_resolved_in_depth"
    elif med<=-20 and negative_25_frac>=.65:
        status="negative_depth_step_observed_but_unverified"
    else:
        status="ambiguous_depth_response"
    return {
        "status":status,
        "subject_roi_xyxy":list(map(int,subject_box)),
        "background_roi_xyxy":list(map(int,background_box)),
        "subject_paired_coverage_fraction":round(float(np.mean(good[subject])),5),
        "background_paired_coverage_fraction":round(float(np.mean(good[background])),5),
        "stable_subject_pixel_count":int(len(s)),
        "stable_background_pixel_count":int(len(b)),
        "background_median_optical_z_delta_mm":round(bg_shift,3),
        "subject_median_background_corrected_optical_z_delta_mm":round(med,3),
        "subject_p5_p95_background_corrected_delta_mm":[round(float(v),3) for v in np.percentile(corrected,[5,95])],
        "subject_abs_delta_le_12mm_fraction":round(near_zero_frac,5),
        "subject_negative_at_least_25mm_fraction":round(negative_25_frac,5),
        "operator_reported_rise_mm":operator_rise_mm,
        "optical_material_is_translucent_verified":False,
        "infrared_passes_through_object_verified":False,
        "physical_board_edges_auto_detected":False,
        "physical_height_estimated_or_certified":False,
        "slope_accuracy_certified":False,
        "raw_depth_preserved":True,
        "warning":"No physical-depth conclusion. Transparent-looking, glossy, missing, or nonrigid geometry and camera micro-motion can mimic these observations."
    }

def audit_archives(empty_path,board_path,subject_box,background_box,operator_rise_mm=None):
    empty,cal_e,_=load_depth_stack(empty_path)
    board,cal_b,_=load_depth_stack(board_path)
    geometry=("camera_id","width","height","lens_intrinsic_calibration","lens_distortion",
              "lens_pose_translation","lens_pose_rotation","sensor_timestamp_source")
    if any(cal_e.get(k)!=cal_b.get(k) for k in geometry):
        raise ValueError("Camera metadata mismatch")
    result=audit_images(stable_temporal_distance(empty),stable_temporal_distance(board),
                        cal_e["lens_intrinsic_calibration"],subject_box,background_box,
                        operator_rise_mm)
    imu_e,imu_b=analyze_imu(empty_path),analyze_imu(board_path)
    def end_vec(r,kind):
        return r.get("directional_streams",{}).get(kind,{}).get("capture_end_median_xyz")
    gravity=angle_deg(end_vec(imu_e,"gravity"),end_vec(imu_b,"gravity"))
    accel=angle_deg(end_vec(imu_e,"accelerometer"),end_vec(imu_b,"accelerometer"))
    imu_valid=all(v.get("raw_motion_diagnostics_available") and
                  v.get("camera_sensor_timebases_comparable") for v in (imu_e,imu_b))
    pose_guard=bool(imu_valid and gravity is not None and accel is not None and
                    gravity<=.15 and accel<=.2)
    result.update({
        "empty_archive":Path(empty_path).name,
        "surface_archive":Path(board_path).name,
        "relative_imu_gravity_end_deg":None if gravity is None else round(gravity,5),
        "relative_imu_accel_end_deg":None if accel is None else round(accel,5),
        "conservative_imu_orientation_gate_passed":pose_guard,
        "camera_pose_independently_verified":False,
        "raw_user_material_not_in_repository":True,
    })
    return result

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--empty",type=Path,required=True)
    parser.add_argument("--surface",type=Path,required=True)
    parser.add_argument("--subject-xyxy",type=int,nargs=4,required=True)
    parser.add_argument("--background-xyxy",type=int,nargs=4,required=True)
    parser.add_argument("--operator-rise-mm",type=float)
    parser.add_argument("--output",type=Path)
    args=parser.parse_args()
    r=audit_archives(args.empty,args.surface,args.subject_xyxy,args.background_xyxy,args.operator_rise_mm)
    output=json.dumps(r,ensure_ascii=False,indent=2)+"\n"
    if args.output:args.output.write_text(output,encoding="utf-8")
    else:print(output,end="")
