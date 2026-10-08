# v8.5 diagnostic telemetry specification

Purpose: investigate whether ARCore Depth reconstruction of green cross-slope
changes with camera position, angle, or depth/frame latency, without
altering the v8.4 putt prediction algorithm.

## Recorded fields

The existing `collector_diagnostics.txt` now includes bounded blocks:

```text
FRAME_POSE_V1_BEGIN records=... dropped=...
depth_timestamp_ns,camera_frame_timestamp_ns,source,camera_local_x_m,camera_local_y_m,camera_local_z_m,camera_world_qx,camera_world_qy,camera_world_qz,camera_world_qw
... (one record per distinct accepted depth image timestamp + source)
FRAME_POSE_V1_END
```

- `source` identifies `raw` or `full`.
- Camera-local X/Y/Z uses the gravity-aligned putt reference frame, matching
  the local coordinate convention used for stored depth points.
- Quaternion is the camera orientation in ARCore world coordinates, not the
  gravity-aligned local frame. Interpret it alongside the reference transform;
  it is not itself a physical ground-slope measurement.
- `camera_frame_timestamp_ns` and `depth_timestamp_ns` are intentionally
  **separate**, as depth samples can be older than the currently reported
  ARCore camera frame. The camera pose must not be presumed to correspond
  exactly to the depth image timestamp.
- Separate blocks are kept for the short internal scan windows. Previous
  blocks are captured before collector reset; the active window is added
  when the scan is persisted.
- Each internal window retains at most 256 distinct timestamp/source records.
  Oldest entries are evicted on overflow; `dropped` records the count.

This is observational logging only; it does not correct or invert any slope,
change scan success criteria, or require a new handset.

## Readiness

The source generation, APK unit tests, and signing compatibility are
verified by `.github/workflows/verify-v85.yml`. They do NOT establish
that camera pose precisely timestamps the Depth pixels.

Future calibration requires a known-slope reference and measured viewing
geometry; previously saved 83 scans do not have these pose histories.

Do not commit captured user photos or full scan ZIPs into the public repo.
