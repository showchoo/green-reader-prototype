from pathlib import Path

path = Path("app/src/main/java/jp/example/greenreader/MainActivity.kt")
s = path.read_text(encoding="utf-8")

old = "        val combined = SlopeConsensus.combine(consensusReports, minAgree = 4)\n"
new = """        val rawCombined = SlopeConsensus.combine(consensusReports, minAgree = 4)
        val combined = rawCombined?.let { FieldOrientationCalibration.correctCrossSign(it) }
"""
if old not in s:
    raise SystemExit("v0.8.15 consensus result target not found")
s = s.replace(old, new, 1)

if 'appVersion = "0.8.14"' not in s:
    raise SystemExit("v0.8.15 appVersion target not found")
s = s.replace('appVersion = "0.8.14"', 'appVersion = "0.8.15"', 1)

if s.count("FieldOrientationCalibration.correctCrossSign") != 1:
    raise SystemExit("v0.8.15 cross calibration must be applied exactly once")

path.write_text(s, encoding="utf-8")
print("Applied v0.8.15 field cross-sign calibration after consensus")
