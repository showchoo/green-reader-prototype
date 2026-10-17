# SC-52A v11.0 fixed-camera versus handheld DEPTH16 — 2026-10-17

## Data provenance / privacy

- User-authorized Google Drive (private): `Session_HW_DEPTH_20261017_222431_073.zip` (handheld, ~22:24 JST) and `Session_HW_DEPTH_20261017_224806_554.zip` (user-confirmed **fixed** ~22:48 JST).
- Same **Camera2 ID 4**, 640×480 packed DEPTH16, same calibrated Camera2 intrinsics, each captures 12 frames with first all-zero warm-up, leaving **11** nonempty frames spaced at 200ms. No reported capture errors.
- **Distances differ:** the handheld images have whole-frame median range ~1.03m, fixed images ~1.55m. Central ROI radial ranges ~1.18m vs ~1.82m. These are not the same fixed target position and can have distinct materials/scene geometry, so data improvements **cannot all be attributed causally to mounting**.
- Raw .bin maps/room geometry remain in user's authorized Google Drive; none committed publicly.

## Apples-to-apples logged statistics

| Metric | Handheld | Camera fixed |
| --- | ---: | ---: |
| Nonempty frame count | 11/12 | 11/12 |
| Valid-distance pixels, median per frame | **85.25%** | **87.12%** |
| Global distance median (across frames) | 1028–1033mm, span **5mm** | 1548–1552mm, span **4mm** |
| Center 100×100 ROI median radial range span | **13mm** | **1mm** |
| Same *image pixel* nonzero in all valid frames | 254,704 | 261,653 |
| Per-pixel range min–max span, median | **10mm** | **8mm** |
| Per-pixel range min–max span, 90th percentile | **46mm** | **24mm** |
| Adjacent frames: per-pixel absolute range difference median | **1mm** | **2mm** |
| Adjacent frames: per-pixel absolute range difference 90th percentile | 6mm | 6mm |
| First five vs last five: same-pixel signed average-distance shift median | **−5.8mm** | **−0.2mm** |
| First five vs last five: same-pixel absolute shift median | **6.2mm** | **2.6mm** |
| First five vs last five: same-pixel absolute shift p90 | **23.8mm** | **9.6mm** |
| Gravity vector max angular change (relative to first nonempty depth frame) | **0.664°** | **0.031°** |
| Gravity sensor row count | 157 | 159 |
| Confidence >=50% coded distance pixels | **0** | **0** |
| DEPTH16 packed confidence code distribution | 2: 1,506,676; 3: 1,365,097; 4: 4,341 | **2: 2,942,719; others: 0** |
| Camera2 reported confidence value | ~21.11% mean | **14.29% mean** |

All distance statistics are *radial distances*, **not independently surveyed floor elevations**. In particular, center-ROI median stability at 1mm does **not** mean each pixel or floor point is measured to 1mm: 261,653 common pixel coordinates have a median **8mm full temporal range**, and most of that is not independent height error. A steady camera can reproduce a biased 3D shape very well.

### Exploratory plane normal fitting, not a physical slope measurement

Using radial depths deprojected through saved approximate camera intrinsics **without reliable RGB segmentation or verified distortion removal**, robust per-frame planar regression across several rectangular pixel ROIs found:

- Center 180×180 image patch: same-region estimated normal fluctuated no more than ~**0.13°** from its frame-averaged normal. Its **median absolute plane residual was ~14mm**.
- Right-hand ROI normal deviated from the center 180×180 ROI's normal by approximately **5.7°**, whereas the upper ROI deviated by **8.1°**. This can mean distinct scene surfaces or depth distortions; without a synchronized RGB image, there is no justification to label all three patches as the *same* physical level floor.
- The full patch regression has substantial nonplanar residual and does not establish world-up or physical grade. The Camera2 lens pose reference is `PRIMARY_CAMERA`, not an externally verified camera-to-gravity transform. A stable image registration or floor plane normal cannot substitute for such calibration.

**Do not** convert any of these angles into a golf-green percent slope or claim the sensor measures the floor's absolute tilt. Distortion correction/semantic masking would change plane fits; quoted angles are *diagnostics only*.

## Engineering verdict

1. **CONFIRMED:** independent public Camera2 DEPTH16 acquisition works on the SC-52A, with reliable archival, up to ~87% nonzero radial-distance coverage, and fixed capture has far lower drift in central aggregate range and gravity direction.
2. **NOT CERTIFIED:** high-resolution sub-percent true floor grade. The fixed scene yields **zero >=50%-coded confidence pixels**, same-pixel range spans often exceed the **5mm rise/run height difference corresponding to 0.5 percentage points over 1m**, and the gravity-to-depth-camera frame is not independently verified.
3. **NOT A PROOF OF IMPOSSIBILITY:** low Camera2 confidence may be conservative, vendor-dependent or affected by physical target material/range. Fixed captures show potentially useful repeatability; systematic error remains untested.
4. **NO APK BUMP:** v11.0 remains a research recorder. Keep putting guidance blocked/not advertised as precise. Adding blind frame averaging to claim sub-percent grade would be scientifically unjustified.

### Only worthwhile next gate

Rather than another handheld/camera-only APK, the next meaningful experiment requires an **independent physically measured rise/run reference**, firm phone mount, unchanged physical A/B positions and confirmed camera-to-gravity extrinsics; ideally also mark which pixels are floor. With 1m marked distance, a 5mm independent vertical difference is already a 0.5pp grade. If independent average error >0.5pp, worst >1.0pp or repeated grade span >0.5pp after one defensible calibration, stop the SC-52A phone-only precision-line route. Do not buy more phones or blindly scan the same floor.

Reproducibility: `research/sc52a_rgb_multiview/compare_depth16_fixed.py` compares the two private ZIPs locally; `test_compare_depth16_fixed.py` tests only synthetic user-free ZIPs in CI.
