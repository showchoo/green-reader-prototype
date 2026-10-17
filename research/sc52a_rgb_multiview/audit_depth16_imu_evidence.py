#!/usr/bin/env python3
"""Audit new Camera2 DEPTH16 research IMU recordings without trusting gravity alone.

Consumes user-owned opt-in v11.1 Session_HW_DEPTH_*.zip offline. Reads raw
accelerometer, gyroscope, vendor uncalibrated gyroscope and TYPE_GRAVITY when
available. Only checks relative timing and within-capture motion evidence.
Never certifies global phone pose, measured board tilt or putting accuracy.
"""
import argparse
import csv
import io
import json
import math
import statistics
import zipfile
from collections import defaultdict
from pathlib import Path

SENSOR_TYPES={"gravity","accelerometer","gyroscope","gyroscope_uncalibrated"}


def _read_csv(z,name):
    return list(csv.DictReader(io.StringIO(z.read(name).decode("utf-8-sig"))))


def _median_vector(rows):
    return [
        statistics.median(float(r[k]) for r in rows)
        for k in ("x","y","z")
    ]


def _angle_deg(a,b):
    am=math.sqrt(sum(t*t for t in a))
    bm=math.sqrt(sum(t*t for t in b))
    if min(am,bm)<1e-12:
        return None
    cosine=sum(x*y for x,y in zip(a,b))/(am*bm)
    return math.degrees(math.acos(max(-1.,min(1.,cosine))))


def summarize_stream(rows):
    if not rows:
        return {"samples":0,"median_spacing_ms":None,
                "first_vs_final_direction_deg":None,
                "end_window_direction_spread_deg":None,
                "median_vector":None}
    timestamps=[int(row["sensor_timestamp_ns"]) for row in rows]
    if any(b<=a for a,b in zip(timestamps,timestamps[1:])):
        raise ValueError("Non-monotonic sensor timestamps")
    if any(not all(math.isfinite(float(row[k])) for k in ("x","y","z"))
           for row in rows):
        raise ValueError("Non-finite sensor values")
    deltas=[(b-a)/1e6 for a,b in zip(timestamps,timestamps[1:])]
    window=max(3,min(50,len(rows)//3))
    initial=_median_vector(rows[:window])
    final=_median_vector(rows[-window:])
    angle=_angle_deg(initial,final)
    final_spread=max(
        filter(lambda x:x is not None,
               (_angle_deg([float(r[k]) for k in ("x","y","z")],final)
                for r in rows[-window:])),
        default=None)
    return {
        "samples":len(rows),
        "first_sensor_timestamp_ns":timestamps[0],
        "last_sensor_timestamp_ns":timestamps[-1],
        "median_spacing_ms":round(statistics.median(deltas),3) if deltas else None,
        "first_vs_final_direction_deg":round(angle,4) if angle is not None else None,
        "end_window_direction_spread_deg":
            round(final_spread,4) if final_spread is not None else None,
        "median_vector":[round(v,6) for v in _median_vector(rows)],
    }


def audit(path):
    path=Path(path)
    with zipfile.ZipFile(path) as z:
        roots={x.rsplit("/",1)[0] for x in z.namelist()
               if x.endswith("/camera2_sensor_metadata.json")}
        if len(roots)!=1:raise ValueError("Not one complete v11.1 research session")
        root=roots.pop()
        names=set(z.namelist())
        required=("camera2_sensor_events.csv",
                  "camera2_sensor_metadata.json",
                  "camera2_calibration.json","camera2_depth_frames.csv",
                  "camera2_depth_summary.json","camera2_gravity.csv",
                  "record_identity.json")
        if any(root+"/"+name not in names for name in required):
            raise ValueError("Missing v11.1 archive component")
        metadata=json.loads(z.read(root+"/camera2_sensor_metadata.json"))
        calibration=json.loads(z.read(root+"/camera2_calibration.json"))
        depth_summary=json.loads(z.read(root+"/camera2_depth_summary.json"))
        events=_read_csv(z,root+"/camera2_sensor_events.csv")
        frames=_read_csv(z,root+"/camera2_depth_frames.csv")
        legacy_gravity=_read_csv(z,root+"/camera2_gravity.csv")
        if len(frames)!=int(depth_summary["frame_count"]):
            raise ValueError("Inconsistent saved depth frame count")
        if int(metadata.get("camera_timestamp_source",-1))!=int(
                calibration.get("sensor_timestamp_source",-2)):
            raise ValueError("Camera timestamp source mismatch")
    by_type=defaultdict(list)
    for ev in events:
        type_name=ev.get("sensor_type","")
        if type_name not in SENSOR_TYPES:
            raise ValueError("Unexpected sensor type: "+type_name)
        by_type[type_name].append(ev)
    counts=metadata.get("per_sensor_sample_count",{})
    summaries={}
    for type_name in sorted(SENSOR_TYPES):
        if len(by_type[type_name]) != int(counts.get(type_name,0)):
            raise ValueError("Sensor sample count metadata mismatch")
        summaries[type_name]=summarize_stream(by_type[type_name])

    registered=metadata.get("sensor_listener_registered",{})
    raw_available=all(bool(registered.get(s)) and summaries[s]["samples"]>=6
                      for s in ("accelerometer","gyroscope"))
    real_time=(metadata.get("camera_vs_sensor_timestamp_comparable") is True
               and calibration.get("sensor_timestamp_source")==1)
    frame_times=[int(x["image_timestamp_ns"]) for x in frames]
    if any(b<=a for a,b in zip(frame_times,frame_times[1:])):
        raise ValueError("Non-monotonic DEPTH16 timestamps")
    # Camera2 UNKNOWN cannot be compared with IMU Event timestamps; callback
    # delivery can be compared but is not exposure-time synchronization.
    overlap={}
    if real_time and raw_available and frame_times:
        for type_name in ("accelerometer","gyroscope","gravity"):
            stream=summaries[type_name]
            if stream["samples"]>0:
                overlap[type_name]=sum(
                    stream["first_sensor_timestamp_ns"]<=ts<=
                    stream["last_sensor_timestamp_ns"]
                    for ts in frame_times)
    no_overflow=all(int(v)==0 for v in
                    metadata.get("per_sensor_cap_dropped",{}).values())
    no_disorder=all(int(v)==0 for v in
                    metadata.get("per_sensor_out_of_order_dropped",{}).values())
    state=("RAW_MOTION_EVIDENCE_AVAILABLE" if raw_available and
           real_time and no_overflow and no_disorder else
           "TIMESTAMP_OR_RAW_MOTION_EVIDENCE_INCOMPLETE")
    return {
        "source":path.name,
        "schema":depth_summary.get("schema_version"),
        "valid_depth_frames_recorded":int(depth_summary["frame_count"]),
        "original_gravity_rows":len(legacy_gravity),
        "camera_timestamp_source":metadata.get("camera_timestamp_source"),
        "camera_sensor_timebases_comparable":real_time,
        "gyro_and_accelerometer_both_recorded":raw_available,
        "no_per_sensor_buffer_overflow":no_overflow,
        "no_sensor_timestamp_disorder":no_disorder,
        "frame_times_within_sensor_stream":overlap,
        "streams":summaries,
        "diagnostic_state":state,
        "device_mount_moved_proven":False,
        "absolute_gravity_frame_verified":False,
        "board_grade_accuracy_certified":False,
        "limitation":"Raw gyro rate is not an independently surveyed 3D world-pose reference; sensor fusion is uncalibrated for this physical mount."
    }


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("archive",type=Path)
    p.add_argument("--output",type=Path)
    a=p.parse_args()
    result=json.dumps(audit(a.archive),ensure_ascii=False,indent=2)
    if a.output:a.output.write_text(result,encoding="utf-8")
    else:print(result)
