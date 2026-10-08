# Green Reader Precision v8.6 — camera-view geometry diagnostics

**Status:** Engineering instrumentation only. This is *not* a correction of
green slope, not a ground-truth calibration, and not evidence of better
slice/hook accuracy.

## Why this matters

v8.5 recorded the camera position, ARCore world quaternion, a camera-frame
timestamp and a depth-image timestamp. However, without a view orientation
expressed in the same gravity-aligned ball coordinate frame as the saved
point cloud, one cannot reliably tell how far from the image center each
accepted Depth point was observed. A world quaternion alone is not sufficient
without the reference-frame orientation.

v8.6 adds the following fields to the already saved
`collector_diagnostics.txt` `FRAME_POSE_V1` CSV blocks:

- `camera_forward_local_{x,y,z}`: camera negative-Z forward ray in the
  gravity-aligned, ball-relative reference frame.
- `camera_right_local_{x,y,z}`: camera positive-X ray in the same frame.
- `projection_basis`: `raw_texture_scaled` or `cpu_image_pixels`.
- `projection_width`, `projection_height` and effective
  `intrinsics_{fx,fy,cx,cy}` in that projection's native pixel units.

Raw and Full camera projection coordinates are **not interchangeable**.
Raw uses texture intrinsics scaled to the acquired Raw Depth dimensions;
Full uses camera CPU image intrinsics after ARCore coordinate transformation.
The logged values mirror the existing geometry pipeline.

Only accepted Depth frames produce these records. Each internal scan window
has a fixed bounded buffer (256 records maximum); blocks are captured before
that window's collector is cleared. The value of `dropped` is retained.
Capture still uses the current camera pose, which may have a later
timestamp than the depth image; the timestamps stay separate.

## New offline tool

From a terminal with Python 3.9+:

```sh
python3 scripts/analyze_precision_view_geometry.py \
  "/path/to/Session.zip" \
  --output "./view_geometry_summary.csv"
```

Multiple ZIP paths and uncompressed session directories can be passed.
The tool uses only Python's standard library and never opens `camera.jpg`.

The resulting CSV contains one row per recorded scan. Useful fields:

| Field | Meaning |
|---|---|
| `status` | readiness or missing-data reason |
| `matched_fraction` | sampled saved Depth points joined exactly to a timestamp/source pose |
| `camera_span_m` | bounding-box diagonal of observed camera positions; not traveled path |
| `camera_pitch_down_median_deg` | view tilt using the local forward-vector vertical component |
| `depth_age_median_ms` | camera frame timestamp minus depth image timestamp |
| `off_axis_angle_p95_deg` | angular off-axis extent of matched Depth points |
| `pixel_inside_fraction` | fraction projecting inside the documented pixel basis |
| `raw_rays`, `full_rays` | reconstructed ray samples by actual data source |

The projection is **a diagnostic consistency calculation**; it is not
an additional observation of a true physical slope.

A `legacy_no_pose` status is expected for scans saved before v8.5.
A `legacy_pose_no_view_axes` or `insufficient_geometry` status is
expected for v8.5 scans that do not include the v8.6 ray metadata.
`geometry_ready` means only that the geometry is suitable for
later analysis, *not* that Depth curvature or inaccuracy was detected.

## Future experimental comparison

When v8.6 data become available from M07:

1. Examine timestamp mismatch, camera movement and off-axis pixel coverage
   for failures and successes separately, and Raw versus Full separately.
2. Group scans of the *same stationary surface* by viewing position and
   image eccentricity to look for systematic changes in measured slope.
3. Confirm any suspected trend using a physically surveyed ground-truth
   right/left grade; real undulations and uneven left/right sampling can
   produce the same trends.
4. Only then evaluate a device-specific correction with holdout validation.
   Do not globally multiply distances or reverse the cross-slope sign.

## Invariants

- v8.2 paired positions at 1.5cm or less remain unchanged.
- v8.3 32/50/80cm spatial-scale check remains unchanged.
- v8.4 cell-level matched flank check remains unchanged.
- v8.5 camera pose logs and automatic file saving remain enabled.
- One putt folder per putt, camera image, Raw/Full sidecar, quality log,
  user result input, and prior-install APK signing remain unchanged.
- No camera image or scanned course data is committed to the public repo.

**Limitation:** source/build unit tests do not confirm camera/runtime
accuracy on the arrows We2 M07. Older 83 scans have no frame-pose history.
