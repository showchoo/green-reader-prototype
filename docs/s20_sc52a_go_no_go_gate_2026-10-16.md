# Galaxy S20+ (SC-52A) — Precision go/no-go gate

Date: 2026-10-16. Status: **HOLD / PHYSICAL ACCURACY NOT VERIFIED**.

This is a **stop/go calibration plan**, not a new application version. Do not increase the version or claim accuracy from Raw/Full agreement, smooth regressions, or AR plane agreement.

## Retrospective S20+ observations

The field archive contains **67 scans across v10.1–v10.6** in nine sessions (2026-10-15 to 2026-10-16 JST).

- 55/67 returned a numerical longitudinal slope, but a numerical result is not a physically accurate result.
- 55 successful scans also reported both AR marker delta and Depth ground delta.
- Median absolute disagreement: **3.09 cm** (43/55 > 2 cm; 11/55 > 5 cm; observed maximum 16.39 cm).
- v10.6: 6/6 numerical results; 0/6 STANDARD; all six explicitly warn about marker/Depth height conflict.
- v10.6 putt 001 (0.735 m): Depth delta ≈ +4.5 cm versus AR marker delta ≈ −0.9 cm; disagreement ≈5.4 cm, with Raw and Full reporting similar slopes (~5.9%).
- v10.6 putt 002 (0.603 m): Depth ≈+2.6–3.5 cm versus AR delta ≈0.0 cm.
- The v10.6 travel evidence was only ~1.4–12.6 cm, less than the requested 20–30 cm. This is a real test limitation.
- No independent physical grade of the scanned floor is recorded. **These deltas are internal contradictions, NOT quantified physical measurement errors.**

Sources: original `Session_20261015_*.zip` and `Session_20261016_*.zip` data in the Google Drive Green Reader field backup folder.

## Technical interpretation and warning

- Google officially lists Galaxy S20+ 5G as supporting ARCore Depth API and a ToF sensor, **not** as providing verified putting-grade precision.
- Google's Raw Depth and Full Depth are related outputs of the same ARCore depth inference; Full uses smoothing/interpolation. Agreement is useful for consistency but **cannot establish external accuracy**.
- ARCore `Plane.Type.HORIZONTAL_UPWARD_FACING` hit tests used for markers also cannot certify true floor grade. The marker-vs-depth conflict alone cannot identify which is correct.
- Do not buy a different smartphone on the assumption that faster SoC or ToF will eliminate a bias shared by ARCore algorithms.

Official references:
- https://developers.google.com/ar/devices/
- https://developers.google.com/ar/develop/depth
- https://developers.google.com/ar/develop/java/depth/raw-depth

## Single controlled benchmark before further releases

1. Use a rigid straightedge and a physical bubble level to **independently check** a floor area of at least 1 m in the exact ball-to-cup direction. If the straightedge needs shimming to be level, record the measured shim height and baseline; do not assume a room floor is exactly 0%.
2. Mark physical floor positions A and B approximately 0.8–1.0 m apart. Measure their separation with a tape. Use good diffuse lighting and a textured, non-reflective surface (not carpet piles, glass, furniture).
3. With S20+ running unmodified v10.6, mark A (ball) and B (cup), perform **3 scans** with the phone held steady and another **3 scans** while genuinely translating 20–30 cm sideways. Preserve full session ZIP.
4. Repeat at reversed direction B (ball) → A (cup), **3 scans**. This checks the sign convention and directional bias without relying solely on the absolute level reading. Keep the camera height and angle similar.
5. Record independent floor grade in percent, measurement method and original marker direction. An ARCore horizontal-plane hit is **not** this reference.

### Provisional engineering thresholds (not external standards)

- At least **3 valid scans** for each direction/condition.
- Median absolute longitudinal-grade error versus **measured physical reference** <= **0.5 percentage point**.
- Worst longitudinal-grade error <= **1.0 percentage point**.
- Repeat-scan max-minus-min longitudinal grade <= **0.5 percentage point** in each repeated condition.
- Reversing A→B to B→A must reverse slope sign on a verified nonzero physical incline; on level floor both must be near 0%.
- Separate full software release readiness additionally requires outdoor tests on verified real green slopes and lateral aim verification. This first controlled indoor benchmark cannot establish commercial readiness.

### Stop rule

- A verified flat-floor benchmark that consistently outputs 3–6% grade is **FAIL** for the present S20+/ARCore pipeline.
- If it fails: allow at most **one targeted algorithmic correction with a falsifiable cause**, then repeat the same independent benchmark. Do not continue adding diagnostic APK versions for weeks.
- If the corrected measurement still fails these thresholds, **stop S20+ ARCore-only precision putting development as presently architected**. Consider different sensors or an explicitly lower-precision product; do not tell the user to buy another phone without separate evidence.
- If it passes, proceed to independently verified 1–3% sloped tests, and only then golf-green validation.

Release decision now: **NO RELEASE CERTIFICATION**. Device-specific impossibility: **NOT PROVEN**.


## October 16: Locked execution protocol (v10.6; no new APK)

**User-side physical preparation (one time only):**
- Mark two small spots A and B on the same floor (approximately 0.8–1.0 m apart). Do not place the AR markers on the straightedge itself.
- Check the actual physical rise from A to B with a rigid straightedge, spirit level and measured shim thickness, or a suitably calibrated independent measuring instrument.
- Keep the actual baseline length in millimetres, signed rise in millimetres (B higher than A = positive), and measurement method. The AR marker delta is NOT an acceptable substitute.
- Remove the straightedge before capturing the scene; leave the A/B floor marks.

**Exact scan sequence for a single ZIP:**
1. `Putt_001`: Ball=A, cup=B, 3 scans with minimal phone translation.
2. `Putt_002`: Ball=A, cup=B **at exactly the same floor marks**, 3 scans with the phone genuinely translated laterally 20–30 cm **during each scan**, not merely rotated.
3. `Putt_003`: Ball=B, cup=A, 3 scans. This is a deliberate reversed direction, **not a different target line**.

User can report the measured baseline/rise/method along with “スキャンしました”. The assistant retrieves the Session ZIP from the existing connected Google Drive and performs the evaluation. No need for the user to copy scan logs manually.

**Fail-closed controls for the evaluator:**
- Missing physical reference, unconfirmed identical marks, absent reverse direction, fewer than 3 valid scans in any condition, or missing <18 cm travel in the moving condition → **HOLD: invalid/incomplete protocol**, never PASS.
- Compare the registered AR marker distance to the tape measurement (tolerance max(5cm, 5%)).
- Three conditions are checked against signed independent grade; reverse direction is compared against NEGATIVE of the measured grade.
- Per-condition repeat spread <= 0.5 percentage point, median absolute error <= 0.5 percentage point across the benchmark, worst error <= 1.0 percentage point.
- Passing is `CONTROLLED_BENCHMARK_PASS_NOT_PRODUCT_READY`: a real-green and aim-line test is still mandatory.

**Recheck of latest v10.6 ZIP (Putt_001 and Putt_002 only):**
- Putt_001 3/3 numerical slopes ~5.86%, 6.06%, 5.81%, travel ~1.4–2.5 cm.
- Putt_002 3/3 numerical slopes ~5.42%, 3.84%, 5.38%, travel ~4.2–12.6 cm.
- All 6 were LOW_CONFIDENCE. No reversed `Putt_003`, no measured physical grade.
- Therefore the current data must remain `HOLD_PROTOCOL_OR_REFERENCE_INCOMPLETE`, not a claim that hardware is impossible or a claim that accuracy is proven.

**Development constraint:** The v10.6 binary remains the test instrument. No follow-on numerical threshold tuning or new diagnostic APK until the independent baseline/reverse-direction benchmark establishes a concrete failure mode.


## 2026-10-16: user-confirmed physical level, latest benchmark result

**Reference update:** User explicitly reports the indoor wood floor was checked with a physical spirit level and appears level. The instrument's resolution and exact checked direction are not recorded; this establishes a near-horizontal reference, not surveyed exact 0.000%.

**Latest data**: `Session_20261016_024205_8c44c70d.zip` (S20+ SC-52A, v10.6, 02:42–02:44 JST).

- Nine saved scans, five numerical successes and four analysis failures.
- Same Putt_002 / 0.956958 m baseline: signed longitudinal slopes **−2.110%, +1.989%, +1.479%, +2.084%, +4.015%**, **6.125 percentage-point spread**. All were LOW_CONFIDENCE.
- At placement, ball and cup plane hit-test world Y were −0.6865895 m and −0.6865927 m (essentially identical). In later scan metadata the current anchor-derived cup-minus-ball elevation is +0.027231 m (2.72 cm). Anchors' **relative elevation changed** despite same initial horizontal plane; this is a concrete marker-frame consistency problem, but it does not explain Raw cloud slope variations by itself.
- Offline per-depth-frame reconstruction near the same putt corridor (independently segmented by Raw image timestamps) showed a **24.8 cm range in camera local Y coinciding with a 22.6 cm range in reconstructed floor median Y** during the first scan (14 qualifying Raw frames; Pearson correlation approximately 1.00, regression ratio 0.90). If the same real floor is stationary, its inferred world height should not track camera elevation this way. Strong observational sign of camera-pose/depth-world alignment failure; NOT a proven isolated root cause in ARCore versus app unprojection.
- Other scans with much smaller camera vertical motion still showed nontrivial forward and cross grades. Therefore a uniform vertical-offset subtraction is **not a demonstrated fix**.

**Decision:** `CURRENT_PIPELINE_FAILS_LEVEL_FLOOR_BENCHMARK` for v10.6; the phone supports acquisition but **the app is not safe to present as a precise putting-line reader**. The absence of a quantized shim/level reference prevents a published external accuracy number, but reproducibility failure is conclusive for this app. **Hardware impossibility is not proven.**

**Stop/go next:** No further blind scans or algorithm tuning. Only a single falsifiable correction that addresses (1) independent AR anchors' relative drift and (2) camera pose vs Raw depth-image temporal/alignment mismatch, verified against original floor data, may precede the final go/no-go retest. Do not force a flat-floor slope to zero by post-hoc calibration: actual greens can have arbitrary legitimate slopes.
