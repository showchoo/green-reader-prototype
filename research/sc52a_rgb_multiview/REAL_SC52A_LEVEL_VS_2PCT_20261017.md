# Real SC-52A reference experiment — level vs 2% (2026-10-17)

## Data and provenance

The user reported completing a level-board followed by a 2%-inclined board acquisition with v11.0 Camera2. Private, user-owned Drive archives (do NOT commit): `Session_HW_DEPTH_20261017_232314_973.zip` (23:23 JST, treated as level), and `Session_HW_DEPTH_20261017_232350_431.zip` (treated as 2%). Both are 640×480 direct Camera2 DEPTH16, 12/12 captured, zero errors; first frame empty, 11 valid in each. Camera intrinsics, calibration metadata, and image dimensions are identical. Source Drive IDs: `10slgsZ6shhzcf3OYxoLD6UmPLY4KIbVk` and `1Ccc4f2YDIMbJj6givNduIgqhZskIqkkH`.

The nominal external reference is **2% = 20mm/1000mm**, based on the user following the preceding protocol; the individual physical shim and support positions were not independently instrumented or photographed.

## Two-stage optical-axis depth reconstruction

Depth16 packed millimetre samples are interpreted with the *optical-axis Z* hypothesis supported by prior spatial hold-out geometric tests; camera intrinsics and lens distortion are applied. Each frame has an independently fitted weighted orthogonal point-cloud plane. Median camera-frame normals are calculated over 11 valid frames per condition.

The **old preselected x350–620, y80–400 ROI** yielded **4.225° normal rotation = 7.388% unsigned grade change**, or **5.388 percentage points away** from the 2% nominal reference. That ROI blends moving and stationary surfaces, so it is **not an adequate board-only estimate**.

A less contaminated, intervention-based comparison identifies the **largest connected component** with at least 20mm decrease in median camera range (not selected by closeness to 2%): bounding rectangle about **x328–504, y22–415**, area ~55,800 pixels. The distance difference within this component has median **−50mm**, while an unmoved far-right background area has median **+1mm**. The region was eroded by 17px and constrained to pixels with nonzero readings in at least 10/11 valid frames in both sessions, leaving about **46,800 shared pixels**. This is **an observed changed-surface candidate**, not a confirmed semantic board label.

| Check | Observation |
| --- | ---: |
| External reference | **2.00%** (normal delta atan(.02)=1.146°) |
| Matched changed-area plane-normal delta | **3.09°** |
| Matched changed-area candidate grade change | **5.40%** |
| Difference from nominal reference | **+3.40 percentage points** |
| Baseline acceptance threshold | **±0.50 percentage points** |
| Varying change threshold 15–45mm and erosion 9–27px | **4.76–5.57%**, none near 2% |
| Fixed-mount reported gravity median between sessions | **~0.099°** |
| Per-frame normal drift, first/second capture (selected region, step2) | max **0.049° / 0.084°** |
| Within-plane residual median first/second capture | **4.30mm / 4.06mm** |
| Prior DEPTH16 known limitation | Confidence overwhelmingly code 2 (~14.3%) |

Additional interior subregions of the changed component produced around **4–6%** candidate grade change. Choosing one thin boundary strip by how closely it approximates 2% would be outcome-based cherry-picking; it is not allowed.

## Decision

**Current two-capture 2% physical-reference experiment: preliminary FAIL / NOT CERTIFIED.** A stable plane fit *inside a session* does not establish *between-condition* ground-truth slope accuracy. The same visible physical board surface and exact physical tilt are not independently identifiable in the stored depth-only images. Raising a board can change distance, position, perspective and which physical patch maps to each pixel. The 50mm foreground depth shift is a line-of-sight displacement, **not necessarily a 50mm vertical lift**.

Do not declare the hardware fundamentally incapable or mistake the initial 7.39% mixed ROI for a board-only value. Do not issue another blind APK or merge raw DEPTH16 into the existing putting aim engine. Keep the signed v11.0 research recorder unchanged and treat further work as calibration research. A next meaningful go/no-go would require an independently verified board-support baseline and unchanged surface identity via aligned color or physically controlled fiducials; simply repeating the same unknown-reference captures will not certify 0.5pp accuracy.

Privacy: raw depth maps and user room layout remain private; this report contains only aggregates.
