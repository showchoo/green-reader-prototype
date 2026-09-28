"""Generate the final Precision v7.0 source from the known-good v0.8.19 base."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

PATCHES = [
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
print("\nGenerated Green Reader Precision v7.0 successfully")
