#!/usr/bin/env python3
"""Read an authorized research Session ZIP and evaluate RGB capture usability.

NO inferred accurate putt lines. Camera poses are ARCore VIO diagnostics,
not surveyed physical truth. Uses only standard-library modules.
"""
import argparse
import csv
import io
import json
import math
import re
import statistics
import zipfile
from pathlib import Path

IMAGE_PATTERN = re.compile(r"rgb_([0-9]{4})\.jpg$")
FIELDS = {"index", "ar_frame_timestamp_ns", "cpu_image_timestamp_ns",
          "width", "height", "fx", "fy", "cx", "cy",
          "camera_tx", "camera_ty", "camera_tz",
          "tracking"}

def numeric(row, name):
    try:
        x = float(row[name])
        return x if math.isfinite(x) else None
    except (KeyError, ValueError, TypeError):
        return None

def report_scan(z, prefix):
    status = json.loads(z.read(prefix + "/rgb_capture_status.json"))
    manifest = prefix + "/rgb_frames.csv"
    if manifest not in z.namelist():
        return {"scan": prefix, "status": "MISSING_MANIFEST",
                "metric_slope_certified": False}
    with z.open(manifest) as stream:
        rows = list(csv.DictReader(io.TextIOWrapper(stream, encoding="utf-8")))
    if not rows:
        return {"scan": prefix, "status": "NO_RGB_FRAMES",
                "frame_count": 0, "capture_status": status,
                "metric_slope_certified": False}
    if not FIELDS.issubset(rows[0]):
        return {"scan": prefix, "status": "MALFORMED_HEADER",
                "missing": sorted(FIELDS.difference(rows[0])),
                "metric_slope_certified": False}
    poses, times, timing_deltas, missing = [], [], [], []
    indices = set()
    for row in rows:
        try:
            index = int(row["index"])
            t_frame = int(row["ar_frame_timestamp_ns"])
            t_image = int(row["cpu_image_timestamp_ns"])
        except (KeyError, ValueError):
            return {"scan": prefix, "status": "INVALID_TIMESTAMP_OR_INDEX",
                    "metric_slope_certified": False}
        if index in indices:
            return {"scan": prefix, "status": "DUPLICATE_IMAGE_INDEX",
                    "metric_slope_certified": False}
        indices.add(index)
        filename = prefix + "/rgb_%04d.jpg" % index
        # A previous S20+ capture created 19 zero-byte JPEGs while
        # the manifest was empty. Presence of a filename is not success.
        valid=False
        if filename in z.namelist():
            info=z.getinfo(filename)
            if info.file_size>=1024:
                data=z.read(filename)
                valid=data[:2]==b"\\xff\\xd8" and data[-2:]==b"\\xff\\xd9"
        if not valid:
            missing.append(index)
        timing_deltas.append(abs(t_frame - t_image) / 1e6)
        times.append(t_frame)
        pose = [numeric(row, f"camera_t{axis}") for axis in "xyz"]
        if all(p is not None for p in pose):
            poses.append(pose)
    baseline = 0.0
    for i in range(len(poses)):
        for j in range(i + 1, len(poses)):
            baseline = max(baseline, math.dist(poses[i], poses[j]))
    duration = (max(times) - min(times)) / 1e9
    time_ok = all(a < b for a, b in zip(times, times[1:]))
    max_delay = max(timing_deltas)
    # Same-frame CameraImage normally shares frame timestamp, but zero error
    # remains an observation rather than external ground truth.
    enough = len(rows) >= 12 and len(poses) >= 12 and baseline >= 0.12
    expected_saves=status.get("jpeg_saved")
    saves_ok=(expected_saves==len(rows))
    structural = not missing and time_ok and max_delay <= 50.0 and saves_ok
    assessment = ("READY_FOR_OFFLINE_MULTIVIEW_ATTEMPT"
                  if enough and structural else
                  "INSUFFICIENT_OR_INVALID_RESEARCH_CAPTURE")
    return {"scan": prefix, "status": assessment,
            "frame_count": len(rows), "missing_or_invalid_jpeg_indices": missing,
            "jpeg_saved_counter_matches_manifest": saves_ok,
            "frame_timestamp_monotonic": time_ok,
            "duration_s": round(duration, 2),
            "observed_frame_rate_hz":
                round((len(rows) - 1)/duration, 2) if duration > 0 else None,
            "max_frame_vs_image_timestamp_delta_ms": round(max_delay, 3),
            "arcore_vio_travel_m": round(baseline, 3),
            "observed_image_width": int(rows[0]["width"]),
            "observed_image_height": int(rows[0]["height"]),
            "capture_status": status,
            "metric_slope_certified": False,
            "device_hardware_impossibility_proven": False}


def evaluate_zip(path):
    with zipfile.ZipFile(path) as z:
        scan_paths=sorted(n.rsplit("/",1)[0] for n in z.namelist()
                          if n.endswith("/rgb_capture_status.json"))
        return {"filename": Path(path).name,
                "instrument": "S20+ ARCore RGB research, not an accuracy-certified meter",
                "scans": [report_scan(z, s) for s in scan_paths],
                "scans_with_rgb_status": len(scan_paths),
                "metric_slope_certified": False}


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("session_zip",type=Path)
    p.add_argument("--output",type=Path)
    a=p.parse_args()
    output=json.dumps(evaluate_zip(a.session_zip),ensure_ascii=False,indent=2)
    if a.output:
        a.output.write_text(output,encoding="utf-8")
    else:
        print(output)
