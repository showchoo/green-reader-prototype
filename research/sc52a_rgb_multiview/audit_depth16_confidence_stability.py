#!/usr/bin/env python3
"""Read-only DEPTH16 confidence and repeatability audit of local private ZIPs.

A valid range is not a calibrated, accurate distance. Android DEPTH16 confidence
code: 0=100%, 1=0%, 2..7=(code-1)/7. Not an error bound.
No raw frames/images/IMU or point coordinates written into reports.
"""
import argparse
from array import array
import csv
import io
import json
from pathlib import Path
import statistics
import sys
import zipfile

HIGH_CONF_CODES={0,5,6,7}
STRIDE=4

def csv_rows(z,name):
    return list(csv.DictReader(io.StringIO(z.read(name).decode("utf-8-sig"))))

def percentile(values,p):
    if not values:return None
    a=sorted(values)
    x=(len(a)-1)*p/100
    low=int(x);high=min(low+1,len(a)-1)
    if low==high:return round(a[low],3)
    return round(a[low]*(high-x)+a[high]*(x-low),3)

def pixels(raw,width,height):
    if len(raw)!=width*height*2:raise ValueError("DEPTH16 raw size mismatch")
    p=array('H');p.frombytes(raw)
    if sys.byteorder!="little":p.byteswap()
    return p

def regions(width,height):
    l=width//4;r=(width*3)//4
    t=height//4;b=(height*3)//4
    return {"center":(l,r,t,b),"left_band":(0,l,t,b),
            "right_band":(r,width,t,b)}

def frame_summary(data,width,height):
    counts=[0]*8;valid=0
    boxes=regions(width,height)
    rois={k:{"valid":0,"codes":[0]*8,"sample":[]} for k in boxes}
    for index,packed in enumerate(data):
        mm=packed & 8191
        if mm==0:continue
        conf=packed>>13
        counts[conf]+=1;valid+=1
        y,x=divmod(index,width)
        for name,(x0,x1,y0,y1) in boxes.items():
            if x0<=x<x1 and y0<=y<y1:
                roi=rois[name];roi["valid"]+=1;roi["codes"][conf]+=1
                if (x-x0)%STRIDE==0 and (y-y0)%STRIDE==0:
                    roi["sample"].append(mm)
    result={}
    for name,roi in rois.items():
        x0,x1,y0,y1=boxes[name]
        result[name]={
            "valid_coverage_percent":round(100*roi["valid"]/((x1-x0)*(y1-y0)),3),
            "confidence_code_counts_valid":roi["codes"],
            "median_sampled_distance_mm":round(statistics.median(roi["sample"]),2) if roi["sample"] else None}
    return {"valid_pixels":valid,"confident_pixels":sum(counts[k] for k in HIGH_CONF_CODES),
            "confidence_code_counts_valid":counts,"roi":result}

def temporal_diagnostics(frames,width,box):
    x0,x1,y0,y1=box
    mad=[];firstlast=[];signed=[]
    if len(frames)>=2:
        for y in range(y0,y1,STRIDE):
            for x in range(x0,x1,STRIDE):
                i=y*width+x
                distances=[f[i]&8191 for f in frames]
                if not all(distances):continue
                center=statistics.median(distances)
                mad.append(statistics.median(abs(v-center) for v in distances))
                change=distances[-1]-distances[0]  # signed ints; no unsigned wrap
                firstlast.append(abs(change));signed.append(change)
    return {"sampled_persistent_pixels":len(mad),
            "median_pixel_mad_mm":percentile(mad,50),
            "median_first_last_abs_difference_mm":percentile(firstlast,50),
            "median_first_last_signed_difference_mm":percentile(signed,50)}

def read_session(path):
    path=Path(path)
    with zipfile.ZipFile(path) as z:
        names=z.namelist()
        roots={n.rsplit("/",1)[0]+"/" for n in names
               if n.endswith("/camera2_depth_frames.csv")}
        if len(roots)!=1:raise ValueError("Expected one DEPTH16 session")
        root=roots.pop()
        needed=("camera2_calibration.json","camera2_depth_frames.csv",
                "camera2_depth_summary.json","record_identity.json")
        if not all(root+n in names for n in needed):
            raise ValueError("Incomplete DEPTH16 metadata")
        cal=json.loads(z.read(root+"camera2_calibration.json"))
        summary=json.loads(z.read(root+"camera2_depth_summary.json"))
        rows=csv_rows(z,root+"camera2_depth_frames.csv")
        width=int(cal["width"]);height=int(cal["height"]);count=len(rows)
        if not (2<=width<=4096 and 2<=height<=4096 and
                width%2==0 and height%2==0 and 1<=count<=48):
            raise ValueError("Invalid dimensions or frame count")
        if count!=int(summary["frame_count"]):
            raise ValueError("Frame count mismatch")
        if (int(summary["width"]),int(summary["height"]))!=(width,height):
            raise ValueError("Summary geometry mismatch")
        decoded=[];summaries=[]
        for i,row in enumerate(rows,1):
            if int(row["index"])!=i or (int(row["width"]),int(row["height"]))!=(width,height):
                raise ValueError("Frame index/dimensions mismatch")
            name=root+f"depth_{i:04d}.bin"
            if name not in names:raise ValueError("Missing DEPTH16 frame")
            if z.getinfo(name).file_size!=width*height*2:
                raise ValueError("DEPTH16 raw size invalid")
            values=pixels(z.read(name),width,height)
            stats=frame_summary(values,width,height)
            if (stats["valid_pixels"]!=int(row["valid_pixels"]) or
                    stats["confident_pixels"]!=int(row["confident_pixels"])):
                raise ValueError("DEPTH16-vs-CSV counters mismatch")
            if abs(stats["valid_pixels"]/(width*height)-float(row["coverage"]))>1e-5:
                raise ValueError("DEPTH16 coverage mismatch")
            decoded.append(values);summaries.append(stats)
        if len([n for n in names if n.startswith(root) and n.endswith(".bin")])!=count:
            raise ValueError("Unexpected DEPTH16 raw frame")
    accepted=[data for data,stat in zip(decoded,summaries) if stat["valid_pixels"]>0]
    counts=[sum(s["confidence_code_counts_valid"][k] for s in summaries) for k in range(8)]
    valid=sum(counts);high=sum(counts[k] for k in HIGH_CONF_CODES)
    rois={}
    for key,box in regions(width,height).items():
        rois[key]=temporal_diagnostics(accepted,width,box)
        if accepted:rois[key]["last_frame"]=summaries[-1]["roi"][key]
    return {"source":path.name,"frame_count":count,"nonempty_frames":len(accepted),
            "width":width,"height":height,"camera_id":cal.get("camera_id"),
            "intrinsics":cal.get("lens_intrinsic_calibration"),
            "sensor_orientation_degrees":cal.get("sensor_orientation_degrees"),
            "raw_frames":accepted,
            "confidence_code_counts_valid":counts,
            "total_valid_distance_samples":valid,
            "high_confidence_samples":high,
            "high_confidence_percent_valid":round(100*high/valid,7) if valid else 0,
            "confidence_at_least_50_percent_definition":"code 0 or 5,6,7; code 0 means 100%",
            "frame_confident_min":min(s["confident_pixels"] for s in summaries),
            "frame_confident_max":max(s["confident_pixels"] for s in summaries),
            "frame_valid_min":min(s["valid_pixels"] for s in summaries),
            "frame_valid_max":max(s["valid_pixels"] for s in summaries),
            "roi":rois,
            "certified_metric_grade_available":False,
            "physical_surface_roi_confirmed":False,
            "sensor_confidence_is_measured_error_bound":False}

def between_sessions(a,b):
    compatible=(a["width"]==b["width"] and a["height"]==b["height"] and
                a["camera_id"]==b["camera_id"] and
                a["sensor_orientation_degrees"]==b["sensor_orientation_degrees"] and
                a["intrinsics"]==b["intrinsics"])
    result={"geometry_metadata_compatible":compatible,
            "physical_scene_alignment_verified":False,
            "physical_metric_accuracy_verified":False,"roi":{}}
    if not compatible:return result
    width,height=a["width"],a["height"]
    fa,fb=a["raw_frames"],b["raw_frames"]
    for key,(x0,x1,y0,y1) in regions(width,height).items():
        signed=[];absolute=[];common=0;total=0
        for y in range(y0,y1,STRIDE):
            for x in range(x0,x1,STRIDE):
                total+=1;i=y*width+x
                da=[f[i]&8191 for f in fa if f[i]&8191]
                db=[f[i]&8191 for f in fb if f[i]&8191]
                if not da or not db:continue
                common+=1
                delta=statistics.median(db)-statistics.median(da)
                signed.append(delta);absolute.append(abs(delta))
        result["roi"][key]={
            "sampled_common_valid_pixels":common,"sampled_total_pixels":total,
            "median_signed_difference_mm":percentile(signed,50),
            "median_abs_difference_mm":percentile(absolute,50),
            "p95_abs_difference_mm":percentile(absolute,95)}
    return result

def sanitized(s):
    return {key:val for key,val in s.items() if key not in ("raw_frames","intrinsics")}

def audit(*paths):
    if len(paths) not in (1,2):raise ValueError("Pass one or two local ZIPs")
    sessions=[read_session(x) for x in paths]
    result={"sessions":[sanitized(s) for s in sessions],
            "board_vs_background_segmentation_verified":False,
            "physical_grade_accuracy_certified":False,
            "qualification":"Repeatability and vendor confidence are not measured ground-truth error."}
    if len(sessions)==2:result["pair"]=between_sessions(*sessions)
    return result

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("zip",type=Path,nargs="+")
    parser.add_argument("--output",type=Path,help="PRIVATE local JSON only")
    args=parser.parse_args()
    try:
        report=json.dumps(audit(*args.zip),ensure_ascii=False,indent=2)+"\n"
    except (ValueError,KeyError,zipfile.BadZipFile) as e:parser.error(str(e))
    if args.output:args.output.write_text(report,encoding="utf-8")
    else:print(report,end="")
