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
