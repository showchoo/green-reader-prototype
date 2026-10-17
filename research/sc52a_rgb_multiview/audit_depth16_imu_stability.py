#!/usr/bin/env python3
"""v11.1 Camera2/IMU fixed-mount diagnostics, using private local ZIPs only.

Measured relative differences are NOT phone pose, board tilt, calibrated
DEPTH16, or a certificate of putting accuracy. stdlib only; no field data.
"""
import argparse
import csv
import io
import json
import math
import statistics
import zipfile
from pathlib import Path

AXES=("x","y","z")
STREAMS=("gravity","accelerometer","gyroscope","gyroscope_uncalibrated")

def read_csv(z,name):
    return list(csv.DictReader(io.StringIO(z.read(name).decode("utf-8-sig"))))

def median_xyz(rows):
    return [statistics.median(float(r[k]) for r in rows) for k in AXES] if rows else None

def angle_deg(a,b):
    if a is None or b is None:return None
    an=math.sqrt(sum(x*x for x in a)); bn=math.sqrt(sum(x*x for x in b))
    if min(an,bn)<1e-9:return None
    return math.degrees(math.acos(max(-1,min(1,sum(x*y for x,y in zip(a,b))/(an*bn)))))

def rnd(x,n=5):
    return None if x is None else round(x,n)

def subset(rows,start,end):
    return [r for r in rows if start<=int(r["sensor_timestamp_ns"])<=end]

def preflight(z,root):
    required=("camera2_sensor_events.csv","camera2_sensor_metadata.json",
              "camera2_calibration.json","camera2_depth_frames.csv",
              "camera2_depth_summary.json","camera2_gravity.csv",
              "record_identity.json")
    if not all(root+x in z.namelist() for x in required):
        raise ValueError("Incomplete v11.1 archive")
    meta=json.loads(z.read(root+"camera2_sensor_metadata.json"))
    cal=json.loads(z.read(root+"camera2_calibration.json"))
    summary=json.loads(z.read(root+"camera2_depth_summary.json"))
    frames=read_csv(z,root+"camera2_depth_frames.csv")
    rows=read_csv(z,root+"camera2_sensor_events.csv")
    if not frames or len(frames)!=int(summary.get("frame_count",-1)):
        raise ValueError("Depth frame count mismatch")
    if meta.get("camera_timestamp_source")!=cal.get("sensor_timestamp_source"):
        raise ValueError("Camera timestamp sources disagree")
    timestamps=[int(r["image_timestamp_ns"]) for r in frames]
    if any(b<=a for a,b in zip(timestamps,timestamps[1:])):
        raise ValueError("Non-monotonic Camera2 timestamps")
    bytype={k:[] for k in STREAMS}
    for r in rows:
        kind=r["sensor_type"]
        if kind not in bytype:raise ValueError("Unknown sensor stream")
        if not all(math.isfinite(float(r[k])) for k in AXES):
            raise ValueError("Non-finite IMU vector")
        bytype[kind].append(r)
    counts=meta.get("per_sensor_sample_count",{})
    for kind,items in bytype.items():
        if len(items)!=int(counts.get(kind,0)):
            raise ValueError("Sensor counts disagree")
        ts=[int(x["sensor_timestamp_ns"]) for x in items]
        if any(b<=a for a,b in zip(ts,ts[1:])):
            raise ValueError("Non-monotonic sensor time")
    aligned=meta.get("camera_vs_sensor_timestamp_comparable") is True and cal.get("sensor_timestamp_source")==1
    clean=all(int(v)==0 for v in meta.get("per_sensor_cap_dropped",{}).values())
    clean=clean and all(int(v)==0 for v in meta.get("per_sensor_out_of_order_dropped",{}).values())
    reg=meta.get("sensor_listener_registered",{})
    raw=all(bool(reg.get(k)) and len(bytype[k])>=6 for k in ("accelerometer","gyroscope"))
    return frames,bytype,meta,cal,aligned,raw and clean

def gyro_integral(rows,start,end):
    """Trapezoid rate integral; trailing-0.5-s median is an UNCALIBRATED bias proxy."""
    if len(rows)<2 or end<=start:return None
    ts=[int(r["sensor_timestamp_ns"]) for r in rows]
    if ts[0]>start or ts[-1]<end:return None
    vs=[[float(r[k]) for k in AXES] for r in rows]
    def interpolate(t):
        for i in range(1,len(ts)):
            if ts[i-1]<=t<=ts[i]:
                s=(t-ts[i-1])/(ts[i]-ts[i-1])
                return [x+(y-x)*s for x,y in zip(vs[i-1],vs[i])]
        return None
    nodes=[(start,interpolate(start))]+[(t,v) for t,v in zip(ts,vs) if start<t<end]+[(end,interpolate(end))]
    tail=subset(rows,max(start,end-500_000_000),end)
    bias=median_xyz(tail) if len(tail)>=3 else None
    total=[0.,0.,0.]
    adjusted=[0.,0.,0.] if bias is not None else None
    abs_path=0.;peak=0.
    for (t,a),(u,b) in zip(nodes,nodes[1:]):
        if a is None or b is None:return None
        dt=(u-t)/1e9
        rate=[(x+y)/2 for x,y in zip(a,b)]
        total=[x+v*dt for x,v in zip(total,rate)]
        if bias is not None:
            adjusted=[x+(v-q)*dt for x,v,q in zip(adjusted,rate,bias)]
        abs_path+=math.sqrt(sum(v*v for v in rate))*dt
        peak=max(peak,math.sqrt(sum(v*v for v in a)),math.sqrt(sum(v*v for v in b)))
    return {
        "raw_integral_vector_deg":[rnd(math.degrees(x)) for x in total],
        "raw_integral_norm_deg":rnd(math.degrees(math.sqrt(sum(x*x for x in total)))),
        "trailing_bias_proxy_rad_s":[rnd(x,7) for x in bias] if bias is not None else None,
        "bias_proxy_adjusted_integral_norm_deg":rnd(math.degrees(math.sqrt(sum(x*x for x in adjusted)))) if adjusted is not None else None,
        "sum_absolute_rate_over_time_deg":rnd(math.degrees(abs_path)),
        "peak_rate_deg_s":rnd(math.degrees(peak))
    }

def analyze(path):
    path=Path(path)
    with zipfile.ZipFile(path) as z:
        roots={x.rsplit("/",1)[0] for x in z.namelist() if x.endswith("/camera2_sensor_metadata.json")}
        if len(roots)!=1:raise ValueError("Expected exactly one complete research session")
        root=roots.pop()+"/"
        frames,bytype,meta,cal,aligned,clean=preflight(z,root)
    ts=[int(r["image_timestamp_ns"]) for r in frames]
    start,end=ts[0],ts[-1]
    directional={}
    for kind in ("gravity","accelerometer"):
        rows=bytype[kind]
        first_five=rows[:5]
        early=subset(rows,start,min(end,start+500_000_000)) if aligned else []
        late=subset(rows,end-500_000_000,end) if aligned else []
        full=subset(rows,start,end) if aligned else []
        late_v=median_xyz(late)
        directional[kind]={
            "samples":len(rows),
            "startup_first_five_vs_capture_end_deg":rnd(angle_deg(median_xyz(first_five),late_v)) if aligned and len(first_five)==5 and len(late)>=5 else None,
            "capture_first_half_second_vs_last_half_second_deg":rnd(angle_deg(median_xyz(early),late_v)) if len(early)>=5 and len(late)>=5 else None,
            "capture_end_median_xyz":[rnd(x,7) for x in late_v] if late_v is not None else None,
            "capture_samples":len(full)
        }
    gyro={k:gyro_integral(bytype[k],start,end) if aligned else None for k in ("gyroscope","gyroscope_uncalibrated")}
    confident=[int(r["confident_pixels"]) for r in frames]
    return {
        "source":path.name,"camera_id":cal.get("camera_id"),
        "frame_size":[cal.get("width"),cal.get("height")],
        "frames":len(frames),
        "nonempty_depth_frames":sum(int(r["valid_pixels"])>0 for r in frames),
        "median_confident_pixels":rnd(statistics.median(confident),2),
        "max_confident_pixels":max(confident),
        "camera_sensor_timebases_comparable":aligned,
        "capture_duration_s":rnd((end-start)/1e9,3),
        "raw_motion_diagnostics_available":aligned and clean and len(bytype["gyroscope"])>=6 and len(bytype["accelerometer"])>=6,
        "sensor_counts":{k:len(v) for k,v in bytype.items()},
        "sensor_overflow":meta.get("per_sensor_cap_dropped"),
        "sensor_out_of_order":meta.get("per_sensor_out_of_order_dropped"),
        "directional_streams":directional,"gyro_during_capture":gyro,
        "camera_physical_motion_proven":False,
        "absolute_slope_accuracy_proven":False
    }

def compare(a,b):
    x,y=analyze(a),analyze(b)
    compatible=x["camera_id"]==y["camera_id"] and x["frame_size"]==y["frame_size"]
    result={
        "a":x,"b":y,"camera_geometry_compatible":compatible,
        "camera_mount_pose_independently_verified":False,
        "absolute_slope_accuracy_proven":False,
        "caveat":"Sensor startup, accelerometer dynamics, physical micro-movement, and bias remain distinguishable only with independent evidence."
    }
    if compatible and x["camera_sensor_timebases_comparable"] and y["camera_sensor_timebases_comparable"]:
        result["cross_session_capture_end_direction_difference_deg"]={
            k:rnd(angle_deg(x["directional_streams"][k]["capture_end_median_xyz"],
                            y["directional_streams"][k]["capture_end_median_xyz"]))
            for k in ("gravity","accelerometer")
        }
    return result

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("archives",type=Path,nargs="+")
    p.add_argument("--output",type=Path,help="Local file only; never upload user data")
    args=p.parse_args()
    if len(args.archives) not in (1,2):p.error("Pass one or two v11.1 ZIP files")
    data=analyze(args.archives[0]) if len(args.archives)==1 else compare(*args.archives)
    value=json.dumps(data,indent=2,ensure_ascii=False)+"\n"
    if args.output:args.output.write_text(value,encoding="utf-8")
    else:print(value,end="")
