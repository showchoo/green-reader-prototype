"""Build v11.1 from the exact v11.0 research base, preserving old raw files.

v11.1 adds inert opt-in Camera2/IMU telemetry only. No slope/direction or
ARCore production calculation changes; no automatic capture is enabled.
"""
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
subprocess.run([sys.executable,"scripts/build_precision_v110_camera2_depth16.py"],
               cwd=ROOT,check=True)

gradle=ROOT/"app/build.gradle.kts"
g=gradle.read_text(encoding="utf-8")
for old,new in (
    ('versionCode = 1100','versionCode = 1110'),
    ('versionName = "11.0-depth16-acquisition"',
     'versionName = "11.1-depth16-imu-evidence"'),
):
    if g.count(old)!=1:raise RuntimeError("Unexpected v11.0 build version: "+old)
    g=g.replace(old,new,1)
gradle.write_text(g,encoding="utf-8")

main=ROOT/"app/src/main/java/jp/example/greenreader/MainActivity.kt"
m=main.read_text(encoding="utf-8")
old="Precision 11.0 Camera2深度研究"
if m.count(old)<2:raise RuntimeError("Missing v11.0 research UI text")
m=m.replace(old,"Precision 11.1 Camera2 IMU研究")
main.write_text(m,encoding="utf-8")

capture=ROOT/"app/src/main/java/jp/example/greenreader/Camera2DepthCaptureActivity.kt"
s=capture.read_text(encoding="utf-8")
old='text="Camera2 深度カメラ（研究専用）"'
if s.count(old)!=1:raise RuntimeError("Missing v11.0 sensor research Activity heading")
s=s.replace(old,'text="Camera2 深度＋IMU（研究専用）"',1)
capture.write_text(s,encoding="utf-8")

subprocess.run([sys.executable,
                "scripts/verify_precision_v111_camera2_sensor_evidence.py"],
               cwd=ROOT,check=True)
print("v11.1: direct Camera2 DEPTH16 + bounded raw IMU, never certified grade")
