# SC-52A direct DEPTH16 — last meaningful physical calibration before go/no-go

Use existing **v11.0 Camera2 DEPTH16 research APK**. Do **not** install another version or run ARCore ordinary scans.

## Physical materials

- The same Galaxy S20+ securely mounted on a stable tripod/fixture.
- A **rigid, flat, matte, preferably 40cm+ wide panel/board**, approximately 80–100cm long. Avoid shiny/transparent surfaces or bendable sheet material.
- Physical spirit level (already used to check the indoor floor), ruler/tape measure, and two shims or small stacks of measured height.
- Smooth lighting. Keep phone position and aim *absolutely unchanged* throughout both captures.

## Test 1: the real reference plane (level)

1. Place board with a broad face clearly in the rear camera's field of view at ~0.8–1.2m. It should occupy a substantial image area, including ideally the image's center-right. The camera-only depth research screen has no color preview, so a narrow stick is not enough.
2. Use the spirit level **on the board itself along its 80–100cm long axis**. Level it (0mm rise). Do not rely only on the room floor being level.
3. From MENU select **Camera2深度画像を実際に取得（研究） → 深度データ取得開始**. Keep everything still until saved. Auto-records at most 12 frames and backs up to the existing authorized Drive folder when sync is enabled.
4. Return to the app. **Do not touch the camera mount** between captures.

## Test 2: known +2% board tilt

1. Keep one end of the board at its original height and lift the other end **20mm** at a measured support spacing of **1000mm** (if only an 800mm board is available, use **16mm rise over 800mm run**, still 2%). Confirm the actual difference with a ruler or calipers; books may compress.
2. Keep the same surface and material visible, camera unchanged. Record one more Camera2 DEPTH16 research capture.
3. The target geometric normal rotation is `atan(20/1000)=1.14576°`; do not assume the measured results will match.
4. Wait until the two independent `Session_HW_DEPTH_....zip` files are in the user's own Google Drive and report **「水平と2%を取得しました」**. Also state the *actual measured* rise/run and which end was elevated. Do not manually attach ZIP if the Drive backup succeeded.

## Validation

Offline research tool `evaluate_measured_incline_pair.py` uses the same upper-right ROI of the depth image and two **independent** image sequences with preserved intrinsics and fixed camera framing. It estimates the angle between session median plane normals, and compares the *magnitude* of the implied grade change to the independent reference. It never silently assumes that visual plane goodness implies ground truth.

- If the board is not clearly the subject in the ROI, **invalidate the result**; do not mistake wall/floor for the test board.
- If the two sessions have insufficient nonzero depth or unstable normals, invalidate.
- If reconstructed grade change differs by more than **0.5 percentage points** from the known 2% tilt, consider this modality **NO-GO for precision putting on the current evidence**.
- If difference is within tolerance, call it only **preliminary differential-angle feasibility**, *not commercial precision*. More reference conditions and externally verified signed orientation and absolute grade are required before claims of accuracy.

This deliberate two-state experiment is more informative than any number of same-scene arbitrary scans. Keep private range files off the public GitHub repository.

## Constraints and caveats

The SC-52A direct Camera2 stream is depth-only (`DEPTH_DEPTH_IS_EXCLUSIVE=true`), and the camera pose metadata declares `LENS_POSE_REFERENCE_PRIMARY_CAMERA`. Android gravity is therefore **not** directly an independently certified depth-camera horizon. The two-image-session board-normal **change** reduces dependence on that absolute reference only if the physical camera stays immobile.

Existing direct Camera2 measurements reported **confidence code 2 across every nonzero fixed frame** (~14.3% reported confidence), which is not equivalent to known 85.7% physical error. Dense temporal and spatial averages can be more stable than individual pixels, but geometric fit error and repeatability do not establish absolute slope accuracy.
