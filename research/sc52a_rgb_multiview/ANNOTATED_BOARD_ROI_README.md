# v11.1 externally annotated board ROI research (offline only)

This tool does not automatically identify a physical board from DEPTH16.
A smooth depth surface cannot tell us where the board ends. Low vendor
confidence further means repeatability cannot establish physical accuracy.

## Requirements
1. Keep user-owned Session_HW_DEPTH_*.zip strictly on a private local disk.
2. Independently locate the board in native DEPTH16 640x480 pixel space.
   An RGB image from another camera is NOT registered automatically;
   unknown RGB-to-depth calibration cannot supply verified corners.
   The existing flat sessions do not identify the board boundary.
3. Create a private manifest with schema_version=1, sessions=[ ... ].
   Each entry requires sha256 (actual ZIP SHA-256), source
   (manual_depth_view or externally_registered_rgb), and corners_px.
   Corners order: top-left, top-right, bottom-right, bottom-left,
   in native DEPTH16 pixel coordinates. Never invent coordinates.

Manifest example (PLACEHOLDER ONLY, NOT A VERIFIED BOARD):
{"schema_version":1,"sessions":[{"sha256":"REPLACE_WITH_REAL_SHA256",
"source":"manual_depth_view",
"corners_px":[[100,80],[450,80],[450,380],[100,380]]}]}

## Usage
python3 research/sc52a_rgb_multiview/audit_annotated_board_roi.py session.zip
python3 research/sc52a_rgb_multiview/audit_annotated_board_roi.py session.zip --annotations /private/roi.json --output /private/report.json
python3 research/sc52a_rgb_multiview/audit_annotated_board_roi.py level.zip tilted.zip --annotations /private/roi.json

Without matching annotations: status=unresolved, reason=manual_four_corners_not_supplied.
With annotations: image-space diagnostic planar fit only. The archive hash
proves association, not physical board identity. Lens-distortion correction
has not been independently validated. Camera pose, world gravity,
2% rise/run and ±0.5 percentage-point grade accuracy are all uncertified.
No provisional ROI should feed the production putting-line path.

Only synthetic data are committed to GitHub. Never upload user camera images,
raw depth, or IMU data.
