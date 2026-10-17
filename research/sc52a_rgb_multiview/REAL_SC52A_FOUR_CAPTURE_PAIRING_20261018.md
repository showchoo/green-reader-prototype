# SC-52A direct Camera2 four-session ambiguity audit — 2026-10-18 00:20–00:24 JST

Four new private user-owned v11.0 DEPTH16 ZIPs arrived in the existing authorized Google Drive folder:

| Index | Session suffix | Depth frames / nonempty | Median range coverage | Capture error count |
| --- | --- | --- | --- | --- |
| A | 002038_623 | 12 / 11 | 88.36% | 0 |
| B | 002108_029 | 12 / 11 | 88.93% | 0 |
| C | 002328_291 | 12 / 11 | 88.71% | 0 |
| D | 002354_752 | 12 / 11 | 88.69% | 0 |

All frames have the same Camera2 ID 4, intrinsics/distortion, 640×480, and only low reported depth confidence codes 2/3.

## Important label ambiguity

The user said only 「映しました」 after advice to record a horizontally level rigid board and then raise one side for a 2% reference. No scan ordering was supplied despite **four** captures:

- Could be **A=level B=level C=raised D=raised** (two repeats per state).
- Could be **A=level B=raised C=level D=raised** (two level/raised pairs).
- Other actual sequences cannot be excluded from metadata alone.

The pipeline MUST NOT interpret time proximity as a condition label.

## Motion and geometrical sensitivity

- Gravity direction difference (device pitch/roll proxy): A→B **0.024°**; C→D **0.029°**; A→C **1.226°**. This does not measure yaw/translation.
- Shared image pixel depth difference medians: A→B **−1mm**, C→D **−2mm**, A→C **+3mm**; range pixel coordinates need not correspond to identical physical surface points.
- Using the *optical-axis depth hypothesis*, unchanged predeclared ROIs produce widely different **unsigned angle-derived grade-change equivalents**:

| ROI | A→B | C→D | A→C |
| --- | ---: | ---: | ---: |
| Full image interior | 0.625% | 0.838% | 1.322% |
| Left interior | 0.807% | 1.174% | 1.779% |
| Central | 1.330% | 0.839% | 0.979% |
| Right interior | 0.020% | 0.060% | 1.906% |
| Upper right | 0.616% | 0.124% | 2.371% |
| Far right | 0.202% | 0.004% | 1.702% |

The apparent ~1.9% match **only within the right interior** for A→C is not independently verified board surface and may be confounded by the **1.226° camera gravity direction difference**. It must NOT be elevated to a claim of 2% slope detection accuracy.

## New reproducible research controls

- `audit_four_depth16_capture_pairings.py` parses exactly four user-owned ZIPs, preserves unknown labels unless user supplies two explicit `level` and two explicit `raised` labels, compares **all six capture combinations**, records multiple predeclared region normals and measured gravity difference, and always disables absolute slope / commercial precision certification.
- `test_audit_four_depth16_capture_pairings.py` confirms both alternative orders can only be explicitly assigned; never infer level or tilted from time proximity, rejects missing/duplicate archives, rejects invalid norms, and guards gravity-movement interpretation.
- GitHub Actions verifies the synthetic guards; **private room depth binaries are never uploaded or committed**.

**Current status:** 4/4 archives contain actual depth data; **physical 2% grade accuracy INCONCLUSIVE** until the user identifies which scans correspond to which state, gives independently measured support span and rise, and a coherent panel is identified inside a stable ROI. Do not request another scan before using existing data or claim accuracy based on cherry-picked regions. v11.0 APK remains unchanged.
