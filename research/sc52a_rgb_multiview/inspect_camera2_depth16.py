#!/usr/bin/env python3
"""Validate direct Camera2 DEPTH16 research ZIP, never imply slope accuracy.

Input: owned/user-authorized Session_HW_DEPTH_*.zip.
Reads packed 16-bit little-endian millimetre range + 3 confidence bits.
Reports data validity and intraframe/temporal stability only.
Uses no raw photos and no external network.
"""
import argparse
import csv
import io
import json
import statistics
import struct
import zipfile
from pathlib import Path

def decode_depth16(raw, width, height):
    if width <= 0 or height <= 0 or len(raw) != width*height*2:
        raise ValueError("Invalid DEPTH16 frame byte count")
    ranges = []
    high_conf = 0
    code_one = 0
    center_ranges = []
    sample_stride = 1 if width*height <= 80000 else 2
    for i in range(0, width*height, sample_stride):
        (packed,) = struct.unpack_from('<H',raw,i*2)
        mm = packed & 0x1fff
        code = (packed >> 13) & 7
        if mm == 0:
            continue
        ranges.append(mm)
        if code==0 or code>=5:
            high_conf += 1
        if code==1:
            code_one += 1
        y,x=divmod(i,width)
        if width//3 <= x < 2*width//3 and height//3 <= y < 2*height//3:
            center_ranges.append(mm)
    pixels_sampled = (width*height+sample_stride-1)//sample_stride
    return dict(
        width=width,height=height,source_pixel_count=width*height,
        sample_stride=sample_stride,
        valid_fraction=round(len(ranges)/pixels_sampled,4),
        high_conf_fraction_of_nonzero=
            round(high_conf/len(ranges),4) if ranges else 0,
        invalid_conf_fraction_of_nonzero=
            round(code_one/len(ranges),4) if ranges else 0,
        median_mm=statistics.median(ranges) if ranges else None,
        central_median_mm=
            statistics.median(center_ranges) if center_ranges else None,
        min_mm=min(ranges) if ranges else None,
        max_mm=max(ranges) if ranges else None)

def inspect_zip(path):
    path=Path(path)
    with zipfile.ZipFile(path) as z:
        roots=sorted({n.rsplit('/',1)[0] for n in z.namelist()
                      if n.endswith('/camera2_depth_summary.json')})
        reports=[]
        for root in roots:
            status=json.loads(z.read(root+'/camera2_depth_summary.json'))
            calib=json.loads(z.read(root+'/camera2_calibration.json'))
            w,h=status.get('width',0),status.get('height',0)
            if w != calib.get('width') or h != calib.get('height'):
                reports.append(dict(root=root,status="INVALID_CALIBRATION_DIMENSIONS",
                                    metric_slope_certified=False))
                continue
            info=list(csv.DictReader(io.StringIO(
                z.read(root+'/camera2_depth_frames.csv').decode('utf-8'))))
            if len(info)!=status.get('frame_count'):
                reports.append(dict(root=root,status="INVALID_FRAME_COUNT",
                                    csv_rows=len(info),
                                    status_count=status.get('frame_count'),
                                    metric_slope_certified=False))
                continue
            frames=[]
            valid_structure=True
            last_timestamp=-1
            for row in info:
                i=int(row['index'])
                filename=root+'/depth_%04d.bin'%i
                if filename not in z.namelist():
                    valid_structure=False
                    break
                b=z.read(filename)
                try:
                    decoded=decode_depth16(b,int(row['width']),int(row['height']))
                    timestamp=int(row['image_timestamp_ns'])
                    if timestamp <= last_timestamp:
                        valid_structure=False
                    last_timestamp=timestamp
                    frames.append(decoded)
                except (ValueError,KeyError):
                    valid_structure=False
                    break
            if not valid_structure:
                state="MALFORMED_OR_MISSING_DEPTH16_DATA"
            elif len(frames)<3:
                state="INSUFFICIENT_DIRECT_DEPTH_FRAMES"
            elif sum(f['valid_fraction']>0.1 for f in frames)<3:
                state="DEPTH_FORMAT_AVAILABLE_BUT_NO_USEFUL_RANGE"
            else:
                state="DIRECT_DEPTH16_RANGE_FRAMES_CAPTURED"
            medians=[f['central_median_mm'] for f in frames
                     if f['central_median_mm'] is not None]
            reports.append(dict(
                root=root,status=state,
                frame_count=len(frames),
                image_dimensions=[w,h],
                camera_id=calib.get('camera_id'),
                first_error=status.get('first_error',''),
                capture_stop_reason=status.get('stop_reason',''),
                camera_reports_valid_packed_range=state=="DIRECT_DEPTH16_RANGE_FRAMES_CAPTURED",
                median_valid_fraction=round(statistics.median(
                    [f['valid_fraction'] for f in frames]),4) if frames else 0,
                median_high_conf_fraction=round(statistics.median(
                    [f['high_conf_fraction_of_nonzero'] for f in frames]),4) if frames else 0,
                median_center_range_mm=statistics.median(medians) if medians else None,
                center_range_spread_mm=round(max(medians)-min(medians),1)
                    if len(medians)>1 else None,
                intrinsics_available=len(calib.get('lens_intrinsic_calibration',[]))>=5,
                lens_pose_available=len(calib.get('lens_pose_rotation',[]))==4 and
                    len(calib.get('lens_pose_translation',[]))==3,
                gravity_reference_independently_verified=False,
                range_sensor_identity_tof_verified=False,
                metric_slope_certified=False,
                frames=frames
            ))
    return dict(filename=path.name,scans=reports,
                interpretation="DEPTH16 range capture viability only. A stable camera-to-ground distance is not independently surveyed ground surface grade.")

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument('zip',type=Path)
    p.add_argument('--output',type=Path)
    a=p.parse_args()
    output=json.dumps(inspect_zip(a.zip),ensure_ascii=False,indent=2)
    if a.output:a.output.write_text(output,encoding='utf-8')
    else:print(output)
