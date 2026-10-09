"""v9.7 scan-failure facts stay intact; no score or slope shortcuts."""
from pathlib import Path
root=Path("app/src/main/java/jp/example/greenreader")
m=(root/"MainActivity.kt").read_text(encoding="utf8")
g=Path("app/build.gradle.kts").read_text(encoding="utf8")
c=(root/"precision/PrecisionScanFailureAdvisor.kt").read_text(encoding="utf8")
assert 'versionName = "9.7"' in g and "versionCode = 970" in g
assert 'appVersion = "Precision 9.7"' in m
assert 'failureAdvice.message()' in m
assert 'precisionLastDiagnostic += " | " + failureAdvice.diagnostic()' in m
assert 'PrecisionScanFailureAdvisor.evaluate(' in m
assert "Reason.FULL_DEPTH_WITHOUT_GROUND" in c
assert "Reason.NO_VALID_LOCAL_FITS" in c
assert "Reason.MOSTLY_FULL_DEPTH_WITH_NO_VALID_FITS" in c
assert "val precisionMaxWindows = 8" in m
assert 'PrecisionSlopeAnalyzer.analyze(' in m
assert 'PrecisionRepeatScanRecovery.decide(' in m
assert 'PrecisionMarkerDepthHeightAudit.evaluate(' in m
assert 'PrecisionMotionEvidenceGate.evaluate(' in m
assert '@Volatile private var markMode = 1' in m
assert 'button("次のパット")' in m
assert 'button("結果入力")' in m
assert 'DriveBackupScheduler.onScanSaved(context)' in (
    root/"field/ScanFieldRecorder.kt").read_text()
assert 'ゴルフ場スキャンデータ' in (
    root/"field/DriveBackupScheduler.kt").read_text()
print("v9.7 failure reason, markers, quality, AR and Drive compatibility PASS")
