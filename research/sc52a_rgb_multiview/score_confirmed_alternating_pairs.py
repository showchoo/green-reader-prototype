#!/usr/bin/env python3
"""Score known A=level, B=raised, C=level, D=raised pairings.

Use user-confirmed order; no implicit ground-truth 2% claim. All available
predeclared ROIs are reported, not cherry-picked. Sign-consistency checks
are *additional diagnostics* only because camera posture between A and C
shifted ~1.2deg and semantic board region is unavailable.

No raw maps/photos/ZIP are sent to a service or committed to GitHub.
"""
import argparse
import json
import math
from pathlib import Path

import numpy as np

from audit_four_depth16_capture_pairings import (
    evaluate_four, summarize_one, PREDECLARED_REGIONS,
    normal_angle_deg, normalized,
)


def directional_cosine(n0, n1, n2, n3, minimum_rotation_deg=0.10):
    """Return None when direction is numerically meaningless.

    Consecutive condition-change vectors are differences between
    normalized Camera2-coordinate plane normals. This is NOT a true
    world-frame tilt vector without independent extrinsic calibration.
    """
    a=normalized(n1)-normalized(n0)
    b=normalized(n3)-normalized(n2)
    a_len=float(np.linalg.norm(a))
    b_len=float(np.linalg.norm(b))
    minimum=2*math.sin(math.radians(minimum_rotation_deg)/2.)
    if a_len<minimum or b_len<minimum:
        return None
    return float(np.clip(a@b/a_len/b_len,-1.,1.))


def summarize_confirmed_order(paths):
    labels=["level","raised","level","raised"]
    audit=evaluate_four(paths,labels)
    report={
        "user_confirmed_order":labels,
        "sessions":audit["capture_order"],
        "pair_labels":["A→B: level→raised","C→D: level→raised"],
        "same_condition_pairs":["A↔C: level↔level","B↔D: raised↔raised"],
        "predeclared_regions":{},
        "target_region_independently_identified":False,
        "external_shim_rise_and_support_run_independently_measured":False,
        "absolute_slope_accuracy_certified":False,
        "commercial_putting_accuracy_certified":False,
    }
    captures=[summarize_one(p) for p in paths]
    pair_map={
        tuple(x["capture_indices"]):x
        for x in audit["comparisons"]
    }
    for key,indices in {
        "pair_1":(0,1),"pair_2":(2,3),
        "repeat_level":(0,2),"repeat_raised":(1,3),
    }.items():
        r=pair_map[indices]
        report[key+"_gravity_direction_difference_deg"]=r[
            "device_gravity_direction_difference_deg"]
    for region in PREDECLARED_REGIONS:
        a=pair_map[(0,1)]["regions"][region]
        b=pair_map[(2,3)]["regions"][region]
        c=pair_map[(0,2)]["regions"][region]
        d=pair_map[(1,3)]["regions"][region]
        normals=[x["normals"][region] for x in captures]
        if any(x is None for x in normals):
            report["predeclared_regions"][region]={
                "status":"NO_COMMON_STABLE_REGION"}
            continue
        response_1=a["unsigned_grade_equivalent_pct"]
        response_2=b["unsigned_grade_equivalent_pct"]
        agreement=directional_cosine(
            *(x[0] for x in normals))
        report["predeclared_regions"][region]={
            "grade_change_pair_1_pct":response_1,
            "grade_change_pair_2_pct":response_2,
            "grade_change_pair_disagreement_pp":
                round(abs(response_1-response_2),3),
            "change_direction_cosine_camera_frame":
                round(agreement,4) if agreement is not None else None,
            "level_repeat_normal_change_pct":
                c["unsigned_grade_equivalent_pct"],
            "raised_repeat_normal_change_pct":
                d["unsigned_grade_equivalent_pct"],
            "plane_fit_p90_not_ground_truth_mm":None,
            "physical_board_roi_verified":False,
            "physically_calibrated_grade_error_pp":None,
        }
    report["audit_assessment"]="REPEATED_CHANGE_SIGNAL_BUT_PHYSICAL_GRADE_INCONCLUSIVE"
    report["limitations"]=[
        "Actual 16mm rise/800mm support distance not independently confirmed",
        "Image regions contain possible board/background mixtures",
        "Cross-group camera gravity direction shifted; yaw/translation unknown",
        "All nonzero depth pixels have low Camera2-reported confidence",
        "Small pair normal changes are not themselves survey-calibrated ground grade",
    ]
    return report


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("zip_A_level",type=Path)
    p.add_argument("zip_B_raised",type=Path)
    p.add_argument("zip_C_level",type=Path)
    p.add_argument("zip_D_raised",type=Path)
    p.add_argument("--output",type=Path)
    args=p.parse_args()
    result=json.dumps(summarize_confirmed_order([
        args.zip_A_level,args.zip_B_raised,
        args.zip_C_level,args.zip_D_raised
    ]),ensure_ascii=False,indent=2)
    if args.output:args.output.write_text(result,encoding="utf8")
    else:print(result)
