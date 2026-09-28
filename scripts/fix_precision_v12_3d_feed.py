from pathlib import Path

p = Path("app/src/main/java/jp/example/greenreader/MainActivity.kt")
s = p.read_text(encoding="utf-8")

wrong = """        mapView.grain = grain
        precisionSurface?.let { surface ->
            view3d.surface = surface
            view3d.ball = b
            view3d.cup = c
        }
        val g = grain
"""
right = """        mapView.grain = grain
        val g = grain
"""
if wrong not in s:
    raise SystemExit("Precision v1.2 misplaced 3D feed not found")
s = s.replace(wrong, right, 1)

target = """        mapView.report = report
        mapView.advice = adv
        mapView.grain = grain
"""
replacement = """        mapView.report = report
        mapView.advice = adv
        mapView.grain = grain
        precisionSurface?.let { surface ->
            view3d.surface = surface
            view3d.ball = b
            view3d.cup = c
        }
"""
if target not in s:
    raise SystemExit("Precision v1.2 final analysis block not found")
s = s.replace(target, replacement, 1)
p.write_text(s, encoding="utf-8")
print("Fixed Precision v1.2 3D result feed placement")
