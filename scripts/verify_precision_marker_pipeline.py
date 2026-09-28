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

    gradle = Path("app/build.gradle.kts").read_text(encoding="utf-8")
    assert 'versionName = "5.8"' in gradle and 'versionCode = 580' in gradle
    assert 'appVersion = "Precision 5.8"' in s


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
print("Final Precision v5.8 marker pipeline verified: fresh-frame tap + Depth fallback guards active")
