"""Regression guard on the FINAL generated activity, after all CI patches.

This catches downstream whole-function replacements which invalidate earlier
patches even though every individual replacement script succeeds.
"""
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
    assert "markMode = 2" in ball, "Successful Ball must enable Cup taps (v32 regression)"
    assert "markMode = 0" not in ball, "Ball must not disable touch input"
    assert "markMode = 0" in cup, "Successful Cup must end marking"
    assert 'if (ev.action == MotionEvent.ACTION_UP && markMode != 0)' in s
    assert 'markAt(ev.x, ev.y)' in s
    mark = function("markAt")
    assert "finishPrecisionTap(mode, false)" in mark
    assert "ballPointFromNeighborDepth(f, x, y)" in mark
    assert "PendingMark(" not in mark, "Never retry a stale tap on later frames"
    assert "tryResolvePendingMark(f)" not in s
    resolver = function("resolveMarkPoint")
    assert resolver.index('"exactSurface"') < resolver.index('"nearbySurface"') < resolver.index('"exactDepth"')
    for name in ("depthPointAtTap", "ballPointFromNeighborDepth"):
        body = function(name)
        assert "Coordinates2d.IMAGE_PIXELS" in body
        assert "val intr = frame.camera.imageIntrinsics" in body
        assert "val intr = frame.camera.textureIntrinsics" not in body
    assert "finishPrecisionTap(mode, true)" in apply
    assert "vertical > limit" in apply, "Keep immediate Cup height rejection"
    for name in ("exactSurfaceHitPoint", "tinyNearbyHitPoint", "currentAnalysisMarks"):
        function(name)
    gradle = Path("app/build.gradle.kts").read_text(encoding="utf-8")
    assert 'versionName = "5.5"' in gradle and 'versionCode = 550' in gradle
    assert 'appVersion = "Precision 5.5"' in s


verify()
# Confirm that the guard really catches the historical failure, not just a token
# elsewhere in applyMark (v32 had markMode=2 only in its reject path).
original = s
s = s.replace('            ball = p\n            markMode = 2\n',
              '            ball = p\n            markMode = 0\n', 1)
assert s != original, "Regression mutation did not reach the Ball success branch"
try:
    verify()
except AssertionError as error:
    assert "Successful Ball" in str(error), str(error)
else:
    raise AssertionError("Verifier failed to detect disabled Cup taps")
s = original
print("Final Precision v5.5 marker pipeline verified; v32 regression detected by negative check")
