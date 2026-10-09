# Green Reader Precision v8.7 — capture-time motion diagnostics

**Scope:** diagnostics only. Green slope estimation, slope-sign vetoes,
aiming arrows, surface points, Raw/Full arbitration, UI, scan save paths,
per-putt folders, and signing are inherited unchanged from v8.6.

## Motivation

The camera pose used to transform an ARCore Depth image is the pose of
the *currently processed camera Frame*, whereas the image has its own
capture timestamp. While the handset moves, the two moments can differ,
potentially causing camera-motion-dependent artifacts.

The previous v8.6 log recorded the two timestamps but not the movement
between the currently processed pose and a more contemporaneous tracked
frame pose. v8.7 retains tracked camera frame samples to **diagnose** the
size of that discrepancy. It does **not** silently change the pose used
for point-cloud reconstruction.

## Instrumentation

- During tracked `PrecisionDepthCollector.integrate()`, save an optional
  `CameraFramePose` before Raw/Full image acquisition.
- Each frame sample includes its ARCore frame timestamp, local XYZ and
  camera-forward unit vector in the same gravity-aligned reference frame
  as the exported point cloud.
- The in-memory history is bounded to **256 camera frames per internal scan
  window**, and is cleared with the existing collector.
- On serializing `collector_diagnostics.txt`, each accepted Depth pose
  is matched against the **closest frame timestamp** retained in the same
  window. Require an absolute time gap of **at most 80ms**.
- Persist four extra optional CSV columns in existing
  `FRAME_POSE_V1` sections:

| Column | Units | Meaning |
|---|---|---|
| `nearest_camera_frame_timestamp_ns` | ns | Timestamp of closest retained tracked frame |
| `nearest_camera_gap_ms` | ms | Absolute image timestamp to matched frame gap |
| `camera_translation_delta_m` | meters | Euclidean distance between image-processing camera and matched-frame camera |
| `camera_forward_delta_deg` | degrees | Absolute difference in camera-facing direction |

A missing acceptable historical pose is represented by four **blank
fields**, **never by zero**, since zero incorrectly suggests perfect
temporal alignment. The 80ms limit is a data-join safeguard, not a
camera-safety criterion or an estimate of actual sensor accuracy.
Nearest matching is not an interpolated/exact pose at acquisition time.

## Updated offline analyzer

The existing standard-library analyzer

```sh
python3 scripts/analyze_precision_view_geometry.py \
  /path/to/Session.zip --output /tmp/view_geometry.csv
```

now includes:

- `matched_depth_pose_records`
- `pose_history_gap_p95_ms`
- `camera_translation_delta_median_m`
- `camera_translation_delta_p95_m`
- `camera_forward_delta_p95_deg`
- `pose_motion_status` (`history_matched`,
  `few_historical_frames`, `not_recorded`)

All previous v8.6 view-geometry metrics remain available. Historical
pre-v8.7 scans legitimately return `not_recorded`, **not**
zero-motion evidence.

## Validation / limits

Android unit tests cover best-timestamp matching, an older image while
the camera moves, a 90° orientation change, no suitable frame,
buffer eviction and scan reset, and invalid/duplicate samples.
Offline tests cover legacy absence and out-of-window/invalid data.
GitHub workflow `verify-v87.yml` executes these along with earlier
Android regression tests, builds and signs the upgrade-compatible APK.

The currently saved 83 M07 scans cannot retrospectively supply frame
pose history. The new diagnostics become useful only after v8.7 is
installed and new scans are performed. Accurate calibration of
hook/slice signs still needs known true terrain slopes and on-device
observation. No algorithmic correction is justified yet.

**Privacy:** no camera photos, session archives or user scan data are
committed to the public repository; only source, synthetic tests and
format documentation are stored there.
