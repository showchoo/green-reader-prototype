from pathlib import Path

p=Path("app/src/main/java/jp/example/greenreader/MainActivity.kt")
s=p.read_text(encoding="utf-8")

s=s.replace(
    "PrecisionSurfaceBuilder.build(precisionPoints)",
    "PrecisionSurfaceBuilder.build(precisionPoints, marks.first, marks.second)"
)
s=s.replace(
    "PrecisionSurfaceBuilder.build(precisionLogPoints)",
    "PrecisionSurfaceBuilder.build(precisionLogPoints, marks.first, marks.second)"
)

if "PrecisionSurfaceBuilder.build(precisionPoints, marks.first, marks.second)" not in s:
    raise SystemExit("v3.8 target missing: precisionPoints corridor build")
if "PrecisionSurfaceBuilder.build(precisionLogPoints, marks.first, marks.second)" not in s:
    raise SystemExit("v3.8 target missing: precisionLogPoints corridor build")

p.write_text(s,encoding="utf-8")
print("Applied Precision v3.8 putt-corridor surface calls")
