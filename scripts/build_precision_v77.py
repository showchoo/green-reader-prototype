"""Generate the final Precision v7.7 source from the known-good v0.8.19 base."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

PATCHES = [
    # Rebuild the known-good v0.8.19 field base from the checked-in prototype.
    "scripts/apply_power_saving.py",
    "scripts/apply_v070_ui.py",
    "scripts/apply_v072_clean_result.py",
    "scripts/apply_v073_no_stimp.py",
    "scripts/apply_v074_auto_grain.py",
    "scripts/apply_v075_full_auto_log.py",
    "scripts/apply_v078_screen_cross.py",
    "scripts/apply_v079_bottom_inset.py",
    "scripts/apply_v080_depth_first_marks.py",
    "scripts/apply_v081_anchor_local_frame.py",
    "scripts/apply_v082_auto_mark_sequence.py",
    "scripts/apply_v083_open_saved_data.py",
    "scripts/apply_v084_data_manager.py",
    "scripts/apply_v087_anchor_cross_projection.py",
    "scripts/apply_v0812_consensus_scan.py",
    "scripts/apply_v0818_known_good_geometry.py",
    "scripts/apply_v0819_ball_center_depth_fallback.py",

    # Layer the Precision pipeline on top of that exact field base.
    "scripts/apply_precision_v12_integrated.py",
    "scripts/fix_precision_v12_3d_feed.py",
    "scripts/apply_precision_v14_gravity_frame.py",
    "scripts/apply_precision_v15_ground_extraction.py",
    "scripts/apply_precision_v16_fail_closed.py",
    "scripts/apply_precision_v17_relaxed_diagnostics.py",
    "scripts/apply_precision_v18_persistent_diagnostics.py",
    "scripts/apply_precision_v19_gmail_auto_report.py",
    "scripts/apply_precision_v20_oauth_signing.py",
    "scripts/apply_precision_v21_remove_gmail.py",
    "scripts/apply_precision_v22_failure_dialog.py",
    "scripts/apply_precision_v23_detailed_diagnostics.py",
    "scripts/apply_precision_v24_runtime_tuning.py",
    "scripts/apply_precision_v25_depth_aligned_marks.py",
    "scripts/apply_precision_v26_putt_corridor.py",
    "scripts/apply_precision_v27_aggregate_final.py",
    "scripts/apply_precision_v28_align_ball_depth.py",
    "scripts/apply_precision_v29_surface_first_marks.py",
    "scripts/apply_precision_v30_marker_sanity.py",
    "scripts/apply_precision_v31_copy_fix.py",
    "scripts/apply_precision_v32_immediate_mark_validation.py",
    "scripts/apply_precision_v33_cup_depth_fallback.py",
    "scripts/apply_precision_v34_full_depth_image_intrinsics.py",
    "scripts/apply_precision_v35_marker_pipeline.py",
    "scripts/apply_precision_v36_candidate_validation.py",
    "scripts/apply_precision_v37_fresh_frame_depth.py",
    "scripts/apply_precision_v38_long_range_cup_gate.py",
    "scripts/apply_precision_v39_dynamic_scan_depth.py",
    "scripts/apply_precision_v40_long_scan_full_supplement.py",
    "scripts/apply_precision_v41_restore_slope_analyzer.py",
    "scripts/apply_precision_v42_field_failure_ux.py",
    "scripts/apply_precision_v43_idle_power_saving.py",
    "scripts/apply_precision_v44_complete_field_logging.py",
    "scripts/apply_precision_v45_neon_hud_ui.py",
    "scripts/apply_precision_v46_ar_startup_stability.py",
    "scripts/apply_precision_v47_collapsible_controls.py",
    "scripts/apply_precision_v48_high_detail_roll.py",
    "scripts/apply_precision_v49_adaptive_scan.py",
]

def run(path: str) -> None:
    print(f"\n>>> {path}", flush=True)
    subprocess.run([sys.executable, path], cwd=ROOT, check=True)

for patch in PATCHES:
    run(patch)

run("scripts/verify_precision_marker_pipeline.py")
run("scripts/apply_precision_v50_session_quality.py")
run("scripts/verify_precision_v70_session_quality.py")
run("scripts/apply_precision_v71_field_recording.py")
run("scripts/apply_precision_v72_safe_quality_ui.py")
run("scripts/verify_precision_v72_safe_quality_ui.py")
run("scripts/apply_precision_v73_field_reliability.py")
run("scripts/verify_precision_v73_field_reliability.py")
run("scripts/apply_precision_v74_temporal_guard.py")
run("scripts/verify_precision_v74_temporal_guard.py")
run("scripts/apply_precision_v75_quality_validation.py")
run("scripts/verify_precision_v75_quality_validation.py")
run("scripts/apply_precision_v76_marker_trust.py")
run("scripts/verify_precision_v76_marker_trust.py")
run("scripts/apply_precision_v77_honest_quality.py")
run("scripts/verify_precision_v77_honest_quality.py")
print("\nGenerated Green Reader Precision v7.7 successfully")
