"""Regression guard on the FINAL generated marker pipeline."""
from pathlib import Path
import re

s = Path("app/src/main/java/jp/example/greenreader/MainActivity.kt").read_text(encoding="utf-8")


def function(name):
    matches = list(re.finditer(r"    private fun " + re.escape(name) + r"\(", s))
    assert len(matches) == 1, f"Expected one {name}, got {len(matches)}"
    start = matches[0].start()
    end = s.find("\n    private fun ", start + 20)
    return s[start:end if end >= 0 else len(s)]


def verify():
    apply = function("applyMark")
    success = apply[apply.index("        collector.clear()") :]
    ball, cup = success.split("        } else {", 1)
    assert "markMode = 2" in ball, "Successful Ball must enable Cup taps"
    assert "markMode = 0" not in ball, "Ball must not disable touch input"
    assert "markMode = 0" in cup, "Successful Cup must end marking"
    assert "finishPrecisionTap(mode, true)" in apply
    assert "vertical > limit" in apply, "Keep immediate Cup height rejection"

    assert 'if (ev.action == MotionEvent.ACTION_UP && markMode != 0)' in s
    assert 'markAt(ev.x, ev.y)' in s

    # v5.7: UI touch only queues screen coordinates. ARCore access happens on
    # the next renderer Frame immediately after Session.update().
    mark = function("markAt")
    assert "pendingMark = PendingMark(mode, x, y" in mark
    assert "resolveMarkPoint(" not in mark
    assert "acquireDepthImage" not in mark
    assert "frame.hitTest" not in mark
    assert "gl.requestRender()" in mark
    assert "markMode = 0" not in mark

    fresh = function("resolvePrecisionPendingTap")
    assert "resolveMarkPoint(frame, pending.x, pending.y)" in fresh
    assert "ballPointFromNeighborDepth(frame, pending.x, pending.y)" in fresh
    assert "rawDepthPointNearTap(frame, pending.x, pending.y)" in fresh
    assert "runOnUiThread" in fresh
    assert "applyMark(mode, point)" in fresh

    draw_update = s.index("            val f = s.update()")
    fresh_call = s.index("            resolvePrecisionPendingTap(f)", draw_update)
    assert fresh_call > draw_update
    assert "tryResolvePendingMark(f)" not in s

    resolver = function("resolveMarkPoint")
    assert resolver.index('"exactSurface"') < resolver.index('"nearbySurface"') < resolver.index('"exactDepth"')

    # Full Depth paths must use IMAGE_PIXELS + imageIntrinsics.
    for name in ("depthPointAtTap", "ballPointFromNeighborDepth"):
        body = function(name)
        assert "Coordinates2d.IMAGE_PIXELS" in body
        assert "val intr = frame.camera.imageIntrinsics" in body
        assert "val intr = frame.camera.textureIntrinsics" not in body

    # Raw Depth fallback follows Google's native raw-depth reconstruction path.
    assert "PrecisionDepthRangePolicy.maxDepthM(" in s
    collector = Path("app/src/main/java/jp/example/greenreader/precision/PrecisionDepthCollector.kt").read_text(encoding="utf-8")
    assert "PrecisionFullDepthSupplementPolicy.plan(" in collector
    assert "fullSupplementFrames" in collector
    assert "pixelStrideStep = if (rawAccepted) max(6, pixelStrideStep) else pixelStrideStep" in collector
    assert "maxDepthM = precisionScanMaxDepthM" in s

    raw = function("rawDepthPointNearTap")
    assert "acquireRawDepthImage16Bits" in raw
    assert "acquireRawDepthConfidenceImage" in raw
    assert "val intr = frame.camera.textureIntrinsics" in raw
    assert "conf < 128" in raw

    for name in ("exactSurfaceHitPoint", "tinyNearbyHitPoint", "currentAnalysisMarks"):
        function(name)

    surface = function("admissibleSurfaceHit")
    assert 'Plane.Type.HORIZONTAL_UPWARD_FACING' in surface
    assert 'for ((index, hit) in hits.withIndex())' in surface
    assert surface.index('tracedMarkCandidate(') < surface.index('return point')
    assert 'admissibleSurfaceHit(' in function("exactSurfaceHitPoint")
    assert 'admissibleSurfaceHit(' in function("tinyNearbyHitPoint")
    assert 'PrecisionMarkerCandidateGate.evaluate(' in function("tracedMarkCandidate")

    analyzer = Path("app/src/main/java/jp/example/greenreader/precision/PrecisionSlopeAnalyzer.kt").read_text(encoding="utf-8")
    assert '" global="' in analyzer
    assert '" rawF="' in analyzer
    assert '" rawR="' in analyzer
    assert "globalFitRadius" in analyzer
    assert "maxLocalDeltaPercent = 5.0f" in analyzer
    assert "LOCAL_FIT_RADIUS_METERS = 0.32f" in analyzer

    assert 'button("診断コピー") { copyLastPrecisionDiagnostic() }' in s
    assert 'recordPrecisionScanFailure("測定結果が安定しませんでした。もう一度スキャンしてください")' in s
    assert '.setTitle(if (accepted)' not in s
    assert '.setTitle("測定データ")' not in s
    finish_tap = function("finishPrecisionTap")
    assert "last_marker" in finish_tap
    assert "dialog.show()" not in finish_tap

    assert "val precisionActive = scanning || captureRequested || pendingMark != null || markMode != 0" in s
    assert "RENDERMODE_WHEN_DIRTY" in s

    assert "ScanFieldRecorder.saveFailure(" in s
    assert "precisionPoints = precisionLogPoints.toList()" in s
    assert "precisionDiagnostic = precisionLastDiagnostic" in s
    recorder = Path("app/src/main/java/jp/example/greenreader/field/ScanFieldRecorder.kt").read_text(encoding="utf-8")
    assert "precision_depth_points.csv" in recorder
    assert "precision_diagnostics.txt" in recorder
    assert "marker_diagnostics.txt" in recorder
    assert "collector_diagnostics.txt" in recorder
    assert "frame_timestamp_ns" in recorder
    assert "fun saveFailure(" in recorder

    assert "NeonScanOverlayView" in s
    assert "if (::liveHud.isInitialized && liveHud.scanning != scanning)" in s
    green_ui = Path("app/src/main/java/jp/example/greenreader/ui/GreenMapView.kt").read_text(encoding="utf-8")
    overlay_ui = Path("app/src/main/java/jp/example/greenreader/ui/CameraOverlayResultView.kt").read_text(encoding="utf-8")
    live_ui = Path("app/src/main/java/jp/example/greenreader/ui/NeonScanOverlayView.kt").read_text(encoding="utf-8")
    assert "postInvalidateOnAnimation()" in green_ui
    assert "postInvalidateOnAnimation()" in overlay_ui
    assert "DEPTH SCAN // ACTIVE" in live_ui

    assert "val arInitializing = trackingStateText != TrackingState.TRACKING.name" in s
    assert "if (arInitializing || precisionActive) 33L else 250L" in s
    assert 'status.text = "AR準備完了。ボール位置から設定してください"' in s
    live_ui = Path("app/src/main/java/jp/example/greenreader/ui/NeonScanOverlayView.kt").read_text(encoding="utf-8")
    assert "LAYER_TYPE_SOFTWARE" not in live_ui
    assert "setShadowLayer" not in live_ui

    assert "GREEN READER  //  PRECISION" not in s
    assert "AR SLOPE ENGINE  //  FIELD MODE" not in s
    assert 'text = "MENU ︿"' in s
    assert "fun setControlsExpanded(expanded: Boolean)" in s
    assert "expandedMenu.visibility = View.GONE" in s
    assert 'scanButton = button("▶  SCAN")' in s

    camera_ui = Path("app/src/main/java/jp/example/greenreader/ui/CameraOverlayResultView.kt").read_text(encoding="utf-8")
    map_ui = Path("app/src/main/java/jp/example/greenreader/ui/GreenMapView.kt").read_text(encoding="utf-8")
    roll_ui = Path("app/src/main/java/jp/example/greenreader/ui/PrecisionRollPath.kt").read_text(encoding="utf-8")
    assert "PrecisionRollPath.build(" in camera_ui
    assert "drawAdaptiveChevrons" in camera_ui
    assert "drawAdaptiveFlowChevrons" in map_ui
    assert "max(96, report.segments.size * 24)" in roll_ui
    assert "raw[i] - endDrift * t" in roll_ui

    assert "precisionCollector.size() >= 250 && precisionCollector.uniqueFrames() >= 3" in s
    assert "precisionWindowElapsedMs < 1200L" in s
    assert "val precisionMinWindows = 5" in s
    assert "val precisionMaxWindows = 8" in s
    assert '"追加測定中… "' in s
    assert 'recordPrecisionScanFailure("追加測定しても結果が安定しませんでした。もう一度スキャンしてください")' in s

    gradle = Path("app/build.gradle.kts").read_text(encoding="utf-8")
    assert 'versionName = "6.9"' in gradle and 'versionCode = 690' in gradle
    assert 'appVersion = "Precision 6.9"' in s


verify()

# Negative check: the historical v32 regression must still be detected.
original = s
s = s.replace('            ball = p\n            markMode = 2\n',
              '            ball = p\n            markMode = 0\n', 1)
assert s != original, "Regression mutation did not reach Ball success branch"
try:
    verify()
except AssertionError as error:
    assert "Successful Ball" in str(error), str(error)
else:
    raise AssertionError("Verifier failed to detect disabled Cup taps")
s = original
print("Final Precision v6.9 marker pipeline verified: fresh-frame tap + Depth fallback guards active")
