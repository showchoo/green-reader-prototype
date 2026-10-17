"""Quality gates for independent raised-board DEPTH16 validation (research only).

These gates decide whether a pair is suitable for further offline analysis;
passing them NEVER establishes camera translation/yaw, real board identity,
physical height accuracy, or putting-slope accuracy.

Local-only script. Never upload or commit private user ZIPs.
"""
import argparse
import json
import math
from pathlib import Path

from audit_depth16_imu_stability import analyze as audit_imu, angle_deg
from estimate_relative_board_height import analyze_archives

GRAVITY_DELTA_MAX_DEG=.15
ACCEL_DELTA_MAX_DEG=.20
INTRA_GRAVITY_MAX_DEG=.15
PLANE_MEDIAN_ABS_RESIDUAL_MAX_MM=5.
UNKNOWN_BOUNDARY_MAX_FRACTION=.15
PAIRED_VALID_MIN_FRACTION=.5
BACKGROUND_MEDIAN_SHIFT_MAX_MM=10.
MAX_FIT_COMPARE_MM=10000 # don't accept nonsensical reporting

def number(v):
    if isinstance(v,bool):return None
    if not isinstance(v,(int,float)) or not math.isfinite(v):return None
    return float(v)

def finite_bounded(v,max_abs):
    x=number(v)
    return x is not None and abs(x)<=max_abs

def imu_quality(empty,board):
    reasons=[]
    for side,record in (("empty",empty),("board",board)):
        if not record.get("camera_sensor_timebases_comparable"):
            reasons.append(f"{side}_camera_imu_clock_unverified")
        if not record.get("raw_motion_diagnostics_available"):
            reasons.append(f"{side}_raw_imu_missing_or_corrupted")
        if record.get("frames",0)<10 or record.get("nonempty_depth_frames",0)<10:
            reasons.append(f"{side}_insufficient_depth_frames")
        intra=record.get("directional_streams",{}).get("gravity",{}).get(
            "capture_first_half_second_vs_last_half_second_deg")
        if not finite_bounded(intra,INTRA_GRAVITY_MAX_DEG):
            reasons.append(f"{side}_within_capture_gravity_drift")
        for kind in ("gravity","accelerometer"):
            if record.get("directional_streams",{}).get(kind,{}).get(
                "capture_end_median_xyz") is None:
                reasons.append(f"{side}_{kind}_vector_missing")
    def vector(record,kind):
        return record.get("directional_streams",{}).get(kind,{}).get(
            "capture_end_median_xyz")
    g=angle_deg(vector(empty,"gravity"),vector(board,"gravity"))
    a=angle_deg(vector(empty,"accelerometer"),vector(board,"accelerometer"))
    if not finite_bounded(g,GRAVITY_DELTA_MAX_DEG):
        reasons.append("cross_session_gravity_direction_mismatch")
    if not finite_bounded(a,ACCEL_DELTA_MAX_DEG):
        reasons.append("cross_session_accelerometer_direction_mismatch")
    return {
        "capture_end_gravity_difference_deg":None if g is None else round(g,5),
        "capture_end_accelerometer_difference_deg":None if a is None else round(a,5),
        "camera_translation_independently_verified":False,
        "camera_yaw_independently_verified":False,
        "imu_observation_checks_passed":not reasons,
        "imu_rejection_reasons":reasons
    }

def qualify_pair(height_report, empty_imu, board_imu, width=None,height=None):
    """A pass permits only continued research, NOT a numerical accuracy claim."""
    reasons=[]
    imu=imu_quality(empty_imu,board_imu)
    reasons.extend(imu["imu_rejection_reasons"])
    if height_report.get("candidate_touches_image_edge") is not False:
        reasons.append("candidate_cropped_at_depth_image_edge")
    boundary=height_report.get("candidate_unknown_neighbor_fraction")
    if number(boundary) is None or not (0<=boundary<=UNKNOWN_BOUNDARY_MAX_FRACTION):
        reasons.append("candidate_contour_not_fully_observable")
    mad=height_report.get("empty_floor_plane_fit_median_absolute_residual_mm")
    if not finite_bounded(mad,PLANE_MEDIAN_ABS_RESIDUAL_MAX_MM):
        reasons.append("floor_is_not_well_approximated_by_one_local_plane")
    paired=height_report.get("paired_pixels")
    total=None if width is None or height is None else width*height
    paired_frac=None if number(paired) is None or total is None or total<=0 else paired/total
    if paired_frac is None or not PAIRED_VALID_MIN_FRACTION<=paired_frac<=1:
        reasons.append("insufficient_common_depth_pixels")
    bg=height_report.get("surrounding_background_raw_projected_normal_shift_mm")
    if not finite_bounded(bg,BACKGROUND_MEDIAN_SHIFT_MAX_MM):
        reasons.append("background_rigid_alignment_not_supported")
    candidate=height_report.get("estimated_perpendicular_change_mm_preliminary")
    if not finite_bounded(candidate,MAX_FIT_COMPARE_MM):
        reasons.append("invalid_candidate_delta")
    # The supplied ruler height is never part of any gate or model fitting:
    # the same observation must be reported under different operator heights.
    return {
        "research_quality_gates_passed":len(reasons)==0,
        "quality_rejection_reasons":reasons,
        "cross_session_imu":imu,
        "common_depth_fraction":None if paired_frac is None else round(paired_frac,6),
        "strict_plane_fit_median_abs_residual_limit_mm":PLANE_MEDIAN_ABS_RESIDUAL_MAX_MM,
        "strict_contour_missing_fraction_limit":UNKNOWN_BOUNDARY_MAX_FRACTION,
        "camera_pose_independently_verified":False,
        "real_world_board_identity_verified":False,
        "absolute_board_height_accuracy_verified":False,
        "putting_grade_precision_verified":False,
        "software_approved_for_real_green_slope_output":False,
        "only_research_observation_even_if_gates_pass":True
    }

def evaluate_archives(empty_path,board_path,operator_height_mm=None):
    base=analyze_archives(empty_path,board_path,operator_height_mm)
    empty_imu=audit_imu(empty_path)
    board_imu=audit_imu(board_path)
    # Load the dimensions from the frame-size evidence, not guesses.
    if empty_imu["frame_size"]!=board_imu["frame_size"]:
        raise ValueError("Depth dimensions mismatch")
    width,height=map(int,empty_imu["frame_size"])
    quality=qualify_pair(base,empty_imu,board_imu,width,height)
    return {"observational_height_diagnostics":base,
            "independent_quality_gates":quality,
            "research_phase":"separate known-height holdout experiment pending",
            "operator_height_never_used_to_calibrate_depth":True,
            "first_height_measurement_is_not_an_accuracy_certificate":True}

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--empty",type=Path,required=True)
    parser.add_argument("--board",type=Path,required=True)
    parser.add_argument("--operator-height-mm",type=float)
    parser.add_argument("--output",type=Path,help="Local JSON file; never commit private measurements")
    args=parser.parse_args()
    result=evaluate_archives(args.empty,args.board,args.operator_height_mm)
    payload=json.dumps(result,ensure_ascii=False,indent=2)+"\n"
    if args.output:args.output.write_text(payload,encoding="utf-8")
    else:print(payload,end="")
