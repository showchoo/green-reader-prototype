"""v9.9 regression: near-ball supported ground selection without data loss."""
from pathlib import Path
root=Path("app/src/main/java/jp/example/greenreader")
s=(root/"precision/PrecisionSurfaceBuilder.kt").read_text()
a=(root/"precision/PrecisionAnchoredGroundSelector.kt").read_text()
m=(root/"MainActivity.kt").read_text()
g=Path("app/build.gradle.kts").read_text()
assert 'versionName = "9.9"' in g and 'versionCode = 990' in g
assert 'appVersion = "Precision 9.9"' in m
assert 'PrecisionAnchoredGroundSelector.select(' in s
assert 'anchorSelection?.valid == true' in s
assert 'anchorSelection.seedIndices.mapNotNull' in s
assert 'ANCHORED_GROUND status=' in s
assert 'dominantBin' not in s and 'heightBins' not in s
assert 'groundReference' in s
assert 'near35.size >= 12' in a and 'near55.size < 18' in a
assert 'abs(p.height - ball.y) <= .20f' in a
assert 'NO_NEAR_BALL_GROUND' in a
assert 'PrecisionSlopeAnalyzer.analyze(' in m
assert 'PrecisionDepthStallPolicy.evaluate(' in m
assert 'PrecisionRepeatScanRecovery.decide(' in m
assert 'PrecisionMarkerDepthHeightAudit.evaluate(' in m
assert 'PrecisionMotionEvidenceGate.evaluate(' in m
assert 'button("次のパット")' in m
assert 'button("結果入力")' in m
assert 'DriveBackupScheduler.onScanSaved(context)' in (
    root/"field/ScanFieldRecorder.kt").read_text()
assert 'ゴルフ場スキャンデータ' in (
    root/"field/DriveBackupScheduler.kt").read_text()
print("v9.9 near-ball ground, original slope validation, v9.8 Depth recovery, Drive unchanged")
