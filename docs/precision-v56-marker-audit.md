# Precision v5.6: validate candidates before selecting a source

## Evidence

Device v5.5 logs selected exactSurface for both Ball and Cup. Both camera
distances were about 1.1 m, tracking and Anchor creation succeeded, but the pair
had horizontal separation 0.098 m and vertical separation 0.290 m (limit 0.080 m).
All alternate acquisition paths were marked not-needed. The actual hit type was
not recorded, so a vertical Plane is a hypothesis, not an established diagnosis.
The old predicate admitted every in-polygon Plane, including vertical/downward.

Ball world: (-0.088341296, -0.46506894, -0.9961827)
Cup world: (-0.044462323, -0.17497732, -1.0839884)

## Change

- Accept tracked upward Planes or tracked DepthPoints. Log type, plane
  classification, tracking, XYZ and rejection reason for each visited hit.
- Iterate past rejected hits rather than stopping at the first in-range hit.
- Apply the existing camera distance and Ball/Cup height limits to candidates
  before returning them. This allows resolution to continue through the existing
  exactSurface -> nearbySurface -> exactDepth -> neighborDepth order.
- Refuse Cup resolution when the Ball Anchor is not tracking, and record its
  current pose together with the camera pose. Retain the post-Anchor height
  validation as a check against pose updates during acquisition.
- Preserve automatic Ball -> Cup progression and copyable marker traces.

No new acceptable-grade threshold, ground projection, forced Cup height, fitter
change or global slope clamp is introduced. A valid pair is not proof of physical
ground accuracy, especially if Ball itself is wrong. DepthPoints have no Plane
classification; pair validation alone cannot establish that they lie on turf.

ARCore Plane.Type reference:
https://developers.google.com/ar/reference/java/com/google/ar/core/Plane.Type

## Validation

Pure Kotlin unit tests reproduce the reported candidate rejection, retain later
plausible ground candidates, check nonfinite inputs, symmetric height bounds,
world translation invariance and Euclidean vs axial distance. The final-source
guard checks both surface paths call the filtered hit loop and that candidate
validation precedes selection, in addition to the v32 transition regression.
Replay the exact workflow patch sequence before Android unit tests and assembly.

## Still intentionally unresolved

The v23 patch overwrites the checked-in slope analyzer, so the generated analyzer
has a 0.45 m local radius and no global regularization. This predates v5.5 and is
not silently changed while marker/Depth correctness remains unverified. Future
analysis should use source-separated Depth and ground support evidence, not
clamping bad geometry to plausible slope values. latestFrame access across the
UI/render threads and nearby-ray displacement remain candidates for investigation.
