"""Regression guards for v7.9 cross-axis mapping and fail-closed UI."""
from pathlib import Path
root=Path("app/src/main/java/jp/example/greenreader")
main=(root/"MainActivity.kt").read_text(encoding="utf8")
over=(root/"ui/CameraOverlayResultView.kt").read_text(encoding="utf8")
mp=(root/"ui/GreenMapView.kt").read_text(encoding="utf8")
gate=(root/"precision/PrecisionDirectionSafety.kt").read_text(encoding="utf8")
gradle=Path("app/build.gradle.kts").read_text(encoding="utf8")
assert 'versionName = "7.9"' in gradle and 'versionCode = 790' in gradle
assert 'appVersion = "Precision 7.9"' in main
assert "levelFrame.localToWorld(midLocal)" in main
assert "levelFrame.localToWorld(sideLocal)" in main
assert "referencePose.transformPoint(midLocal)" not in main
assert "referencePose.transformPoint(sideLocal)" not in main
assert "PrecisionDirectionSafety.evaluate(" in main
assert "precisionDirectionTrustworthy = directionVerdict.trustworthy" in main
assert "directionVerified = precisionDirectionTrustworthy" in main
assert "allowDirection = precisionDirectionTrustworthy" in main
assert "val nx = projectedCross?.x ?: uy" not in over
assert "方向の判定を保留" in over
assert "方向の判定を保留" in mp
assert "reliable.size < 4" in gate
assert "opposing-windows" in gate
assert "opposing-segments" in gate
assert "MAX_USABLE_SLOPE_PERCENT = 12f" in (root/"precision/PrecisionSlopeAnalyzer.kt").read_text()
assert "precision_depth_sources.csv" in (root/"field/ScanFieldRecorder.kt").read_text()
assert 'button("次のホール")' in main and 'button("結果入力")' in main
assert 'button("カップ再指定")' in main and 'button("実測距離")' in main
assert "bitmap = failureBitmap" in main
print("Precision v7.9 direction guard regression checks passed")
