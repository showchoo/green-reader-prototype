# Precision v5.5 marker audit

Build source: `precision-v21-no-gmail-build`, PR #38 against
`precision-build-base`. No merge to main.

## Confirmed cause of unresponsive Cup taps

`apply_v082_auto_mark_sequence.py` removes manual mark buttons and changes a
successful Ball mark to `markMode = 2`. The later
`apply_precision_v32_immediate_mark_validation.py` replaces `applyMark()` in full
and restores the old unconditional `markMode = 0` before the Ball/Cup branches.
The touch listener consequently ignores every following Cup tap. Neither v33's
Cup Depth fallback nor its unresolved-point dialog can run. This is a reachable
state-machine bug in the final generated v5.4 activity, not a Depth threshold
failure. v35 restores the successful Ball -> Cup transition and retains the
immediate height rejection.

## Coordinate consistency

v28 converted only the neighbor Depth fallback to IMAGE_PIXELS/imageIntrinsics.
`depthPointAtTap()` still used scaled textureIntrinsics. v34 makes this path
consistent with the neighbor fallback and Full Depth collector. ARCore documents
Depth-to-CPU conversion via TEXTURE_NORMALIZED -> IMAGE_PIXELS:
https://developers.google.com/ar/develop/java/depth/developer-guide

This is NOT proof that textureIntrinsics caused the measured height error: a
correctly scaled GPU-intrinsics path can be geometrically equivalent. Device logs
must establish which candidate source is selected and whether geometry improves.
Surface-first selection, slope thresholds and fitter remain unchanged. The
neighbor fallback now also receives the same existing Euclidean camera-distance
gate as the other candidates; axial Depth <=4m alone is not equivalent.

## Diagnostics

Each tap records target, screen coordinates, viewport, frame availability,
tracking, timestamp, attempted candidate results, selected source, world XYZ,
camera distance, Anchor creation/error and next mode. Unneeded candidate paths
are explicitly marked not-needed. Depth API exception classes are retained.
Every Cup attempt displays copyable diagnostics including the prior Ball trace.
Ball failures also display a dialog; Ball success advances immediately to Cup.
The latest marker trace is persisted under `precision_diagnostics/last_marker`.

## Patch ordering and remaining audit findings

The actual workflow is on precision-build-base, not the source branch.
v0810/v0811/v0813-v0817/v088/v089 are not applied. The pending-mark resolver
remains unreachable legacy code (no constructor call and no render-loop retry).
Gmail v19/v20 are applied then removed by v21. These legacy scripts are retained
because other build workflows and their string replacement dependencies have not
been migrated. Removing them without an equivalence check would change the build.

Remaining hypotheses: touch-time latestFrame access races Session.update on the
render thread; nearby hits use a displaced ray; exact Depth searches nearby
pixels despite its name; surface hit type does not by itself establish ground.
The diagnostics allow device evidence before altering these behaviors.

## Verification

Run the workflow's full patch list from a clean source checkout, then
`python3 scripts/verify_precision_marker_pipeline.py`. The regression guard
examines the final generated source and includes a negative check recreating
v32's disabled Cup state. CI also runs Android unit tests, compiles/signs the APK,
uploads the final generated MainActivity as an audit artifact, and publishes APK.
Device geometry and AR tracking are not validated by these build-time checks.
