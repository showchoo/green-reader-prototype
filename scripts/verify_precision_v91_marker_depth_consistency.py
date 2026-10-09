"""Generated APK regression assertions for marker/ground discrepancy diagnostic."""
from pathlib import Path
s=Path("app/src/main/java/jp/example/greenreader/MainActivity.kt").read_text()
g=Path("app/build.gradle.kts").read_text()
audit=Path("app/src/main/java/jp/example/greenreader/precision/PrecisionMarkerDepthHeightAudit.kt").read_text()
assert 'versionName = "9.1"' in g and 'versionCode = 910' in g
assert 'appVersion = "Precision 9.1"' in s
assert 'PrecisionMarkerDepthHeightAudit.evaluate(' in s
assert 'markerGeometryTrusted =' in s and '!precisionMarkerDepthDisagreement' in s
assert 'precisionLastDiagnostic += " | " + markerDepthCheck.summary()' in s
assert '⚠ AR目印の高低差とDepth地面形状が矛盾' in s
assert 'Status.INSUFFICIENT_COVERAGE' in audit and 'Status.DISAGREEMENT' in audit
assert 'independentGroundTruth=false' in audit
assert 'PrecisionSlopeAnalyzer.analyze(' in s
assert 'PrecisionScaleDirectionAudit.evaluate(' in s
assert 'PrecisionPairedFlankAudit.evaluate(' in s
assert 'precisionFramePoseScanSummary()' in s
assert 'PrecisionRepeatScanRecovery.decide(' in s
assert 'button("次のパット")' in s and 'button("結果入力")' in s
assert 'bitmap = failureBitmap' in s
print("v9.1 marker-depth mismatch confidence + old features verified")
