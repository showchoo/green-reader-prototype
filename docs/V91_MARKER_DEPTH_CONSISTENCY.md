# Green Reader Precision v9.1 — Marker vs Depth height consistency

## Trigger

M07 field-test ZIP `Session_20261009_104824_4d7817af.zip` from
2026-10-09 contains three consecutive successful scans of the same Putt_002
with stable ~-3.14% lateral and +4.32% longitudinal displayed slope,
despite the user reporting that the tested room floor is *approximately
level*. Stability and a high internal quality score do **not** establish
accuracy.

- Marker positions used by these scans imply the cup is **3.865 cm below**
  the ball in the AR anchored gravity frame across **0.6787 m** horizontally
  (a -5.7% geometric height change).
- An independent, exploratory least-squares fit of the saved **raw points**
  in a narrow putt corridor gave ~+4.1% to +4.9% Y-vs-forward trends in
  these scans, whereas marker height decreases along the same direction.
  This is **not a confirmed floor-plane measurement**: raw points include
  possible furniture, wall fragments, multipath and tracking drift.
- The mismatch of height-change *direction* is valuable forensic evidence
  but does not prove which subsystem is wrong.
- The first successful Putt_002 scan had a materially different cross-slope
  sign and lower quality. It must not be conflated with the later repeat set.

## v9.1 change

New `PrecisionMarkerDepthHeightAudit` independently compares:
1. Vertical difference of AR ball/cup anchors.
2. Difference between robust median heights of existing accepted, connected
   ground-surface cells near the same two endpoints.

Every scan saves:
`MARKER_DEPTH_HEIGHT status=... markerDeltaM=... depthDeltaM=...
discrepancyM=... ballCells=... cupCells=... independentGroundTruth=false`
in the existing precision diagnostic.

If the two changes disagree by **4 cm or more**, the quality status is
**capped** (cannot claim high precision) and the UI displays an explicit
marker–Depth disagreement warning.

If ground-cell coverage is insufficient, the check is **inconclusive**,
not assumed to agree. This diagnostic does **not** claim cm-level accuracy.
A true slope of 5% would be retained if both signals agree; v9.1 **does
not assume terrain is level** and does not subtract any constant slope.

## Unchanged

- Raw/Full Depth reconstruction and point filtering
- Surface fitting, true numerical slope and line arrow algorithms
- App AR/Depth coordinate geometry and marker definitions
- Multi-window scanning, three-scan workflow and scan-failure records
- Download/Session/Putt/Scan saving and APK signing compatibility.

## Next validation

With v9.1 on M07, repeat three accepted scans with the SAME ball/cup marks.
Then repeat the experiment using a spirit level and measured reference
height difference, with a deliberately inclined plane as the control.
Upload the full saved session archive, including diagnostics.

The new diagnostics distinguish *disagreement within AR/Depth* from
*ground-truth error*. Agreement of these two ARCore-related estimates
is never absolute accuracy: both can share the same systematic bias.

Never publish the user's original camera images or ZIP in this repository.
