#!/usr/bin/env python3
"""Conservative, local-only annotated DEPTH16 plane diagnostics.

This does not identify a board automatically or certify surface grade.
Requires an independently prepared polygon manifest bound to each exact ZIP
SHA256. A file hash validates provenance, NOT the annotation's correctness.
All fitting is in the native camera image ray model, without calibrated
distortion correction. Camera movement and physical gravity remain unverified.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import statistics
import zipfile

from audit_depth16_confidence_stability import read_session

STEP=8
MARGIN_PX=12
MIN_POINTS=60
MAX_RMSE_MM=15.0
MIN_INLIER_FRACTION=0.8

def rounded(value,n=5):
    return None if value is None else round(value,n)

def sha256(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as file:
        for block in iter(lambda:file.read(1<<20),b""):
            h.update(block)
    return h.hexdigest()

def area2(points):
    return sum(x0*y1-x1*y0 for (x0,y0),(x1,y1) in
               zip(points,points[1:]+points[:1]))

def validate_corners(corners,width,height):
    """Explicit clockwise TL,TR,BR,BL order in image pixel coordinates."""
    if not isinstance(corners,list) or len(corners)!=4:
        raise ValueError("Exactly four ordered corners are required")
    if any(not isinstance(p,list) or len(p)!=2 for p in corners):
        raise ValueError("Each corner must be [x,y]")
    if any(not all(type(v) in (int,float) and math.isfinite(v) for v in p)
           for p in corners):
        raise ValueError("Nonfinite or nonnumeric corner")
    if any(not (3<=x<width-3 and 3<=y<height-3) for x,y in corners):
        raise ValueError("Corner lies near/outside frame boundary")
    if area2(corners)<=width*height*.06:
        raise ValueError("Corners must be ordered TL,TR,BR,BL with adequate area")
    if area2(corners)>width*height*1.6:
        raise ValueError("Oversized polygon")
    cross=[]
    for i in range(4):
        x0,y0=corners[i];x1,y1=corners[(i+1)%4];x2,y2=corners[(i+2)%4]
        cross.append((x1-x0)*(y2-y1)-(y1-y0)*(x2-x1))
    if min(cross)<=1e-7:
        raise ValueError("Polygon is concave, crossed, or degenerate")
    if not (corners[0][1]<corners[3][1] and
            corners[1][1]<corners[2][1] and
            corners[0][0]<corners[1][0] and
            corners[3][0]<corners[2][0]):
        raise ValueError("Expected TL,TR,BR,BL image-coordinate order")
    return [(float(x),float(y)) for x,y in corners]

def inner_polygon_samples(points,width,height,margin):
    xmin=max(0,int(min(x for x,y in points)))
    xmax=min(width-1,int(max(x for x,y in points))+1)
    ymin=max(0,int(min(y for x,y in points)))
    ymax=min(height-1,int(max(y for x,y in points))+1)
    selected=[]
    for y in range(ymin,ymax+1,STEP):
        for x in range(xmin,xmax+1,STEP):
            minimum=min(((bx-ax)*(y-ay)-(by-ay)*(x-ax))/
                        math.hypot(bx-ax,by-ay)
                        for (ax,ay),(bx,by) in
                        zip(points,points[1:]+points[:1]))
            if minimum>=margin:selected.append((x,y))
    return selected

def solve_3x3(rows):
    mat=[list(r) for r in rows]
    for i in range(3):
        k=max(range(i,3),key=lambda j:abs(mat[j][i]))
        if abs(mat[k][i])<1e-14:return None
        mat[i],mat[k]=mat[k],mat[i]
        pivot=mat[i][i]
        for j in range(i,4):mat[i][j]/=pivot
        for k in range(3):
            if k==i:continue
            f=mat[k][i]
            for j in range(i,4):mat[k][j]-=f*mat[i][j]
    return [mat[i][3] for i in range(3)]

def fit_inverse_depth(points):
    """Fit 1/Z = a*x_normalized + b*y_normalized + c."""
    if len(points)<MIN_POINTS:return None
    mat=[[0.0]*4 for _ in range(3)]
    for nx,ny,z,confidence in points:
        t=(nx,ny,1.0)
        for i in range(3):
            for j in range(3):mat[i][j]+=t[i]*t[j]
            mat[i][3]+=t[i]/z
    return solve_3x3(mat)

def pred(beta,x,y):
    p=beta[0]*x+beta[1]*y+beta[2]
    return 1/p if p>0 else None

def norm(v):
    d=math.sqrt(sum(x*x for x in v))
    return [x/d for x in v] if d>1e-12 else None

def angle_deg(a,b):
    if a is None or b is None:return None
    return math.degrees(math.acos(max(-1,min(1,abs(sum(x*y for x,y in zip(a,b)))))))

def robust_fit(points):
    """Keep ≥80% sampled rays in final plane. Inlier check is descriptive."""
    if len(points)<MIN_POINTS:return None
    fit=fit_inverse_depth(points)
    if fit is None:return None
    for _ in range(3):
        errors=[(abs(z-pred(fit,x,y)),(x,y,z,c))
                for x,y,z,c in points if pred(fit,x,y) is not None]
        if len(errors)<MIN_POINTS:return None
        errors.sort(key=lambda v:v[0])
        fit=fit_inverse_depth([p for _,p in errors[:max(MIN_POINTS,int(.85*len(errors)))]])
        if fit is None:return None
    residual=[abs(z-pred(fit,x,y)) for x,y,z,c in points
              if pred(fit,x,y) is not None]
    if len(residual)<MIN_POINTS:return None
    inliers=sum(r<=MAX_RMSE_MM for r in residual)
    rms=math.sqrt(sum(r*r for r in residual)/len(residual))
    return {"normal":norm(fit),"median_residual_mm":statistics.median(residual),
            "rmse_mm":rms,"inlier_fraction_15mm":inliers/len(residual),
            "usable_sample_count":len(residual)}

def frame_points(frame,coords,intrinsics,width):
    fx,fy,cx,cy=intrinsics[:4]
    result=[]
    for x,y in coords:
        value=int(frame[y*width+x])
        mm=value&8191
        if not mm:continue
        code=value>>13
        xn=(x-cx)/fx;yn=(y-cy)/fy
        # Android DEPTH16 gives radial distance (mm) on camera ray.
        z=mm/math.sqrt(1+xn*xn+yn*yn)
        result.append((xn,yn,z,code))
    return result

def session_diagnostic(path,entry):
    s=read_session(path)
    report={"source":Path(path).name,
            "status":"unresolved",
            "board_identity_independently_verified":False,
            "phone_pose_independently_verified":False,
            "distortion_calibration_verified":False,
            "absolute_slope_accuracy_certified":False}
    if entry is None:
        report["reason"]="manual_four_corners_not_supplied"
        return report,None,s
    if entry.get("sha256")!=sha256(path):
        raise ValueError("Annotation archive SHA256 does not match ZIP: "+Path(path).name)
    if entry.get("source") not in ("manual_depth_view","externally_registered_rgb"):
        raise ValueError("Annotation source must be explicit")
    corners=validate_corners(entry.get("corners_px"),s["width"],s["height"])
    intr=s.get("intrinsics")
    if (not isinstance(intr,list) or len(intr)<4 or
        not all(type(v) in (int,float) and math.isfinite(v) for v in intr[:4]) or
        intr[0]<=0 or intr[1]<=0):
        report["reason"]="lens_intrinsics_missing_or_invalid"
        return report,None,s
    def estimate(margin):
        coords=inner_polygon_samples(corners,s["width"],s["height"],margin)
        if len(coords)<MIN_POINTS:return None,{"reason":"polygon_interior_too_small","sample_count":len(coords)}
        fits=[];valid_frames=0
        high=0;nonzero=0
        for frame in s["raw_frames"]:
            ps=frame_points(frame,coords,intr,s["width"])
            if len(ps)<MIN_POINTS or len(ps)<.70*len(coords):continue
            fit=robust_fit(ps)
            if fit is None:continue
            valid_frames+=1
            fits.append(fit)
            for row in ps:
                nonzero+=1
                high+=row[3] in (0,5,6,7)
        if len(fits)<3:return None,{"reason":"insufficient_fittable_frames","fit_count":len(fits)}
        good=[fit for fit in fits if fit["inlier_fraction_15mm"]>=MIN_INLIER_FRACTION
              and fit["rmse_mm"]<=MAX_RMSE_MM]
        if len(good)<3 or len(good)<.70*len(fits):
            return None,{"reason":"plane_consistency_inadequate","fit_count":len(fits),
                          "acceptable_frames":len(good)}
        median_normal=norm([statistics.median(fit["normal"][i] for fit in good)
                            for i in range(3)])
        spread=[angle_deg(median_normal,fit["normal"]) for fit in good]
        return {"normal":median_normal,
                "median_rmse_mm":rounded(statistics.median(f["rmse_mm"] for f in good),3),
                "max_normal_deviation_deg":rounded(max(spread),5),
                "frames_accepted":len(good),
                "sampled_pixels_inside_polygon":len(coords),
                "high_confidence_fraction":rounded(high/nonzero if nonzero else 0,8)},None
    fit,fail=estimate(MARGIN_PX)
    if fail:
        report.update(fail)
        return report,None,s
    deep,fail_deep=estimate(MARGIN_PX+8)
    if fail_deep:
        report["reason"]="inner_polygon_sensitivity_unavailable"
        return report,None,s
    jitter=angle_deg(fit["normal"],deep["normal"])
    report.update({
        "status":"provisional_annotated_roi_plane",
        "reason":"roi_supplied_but_not_independently_physically_verified",
        "annotation_source":entry["source"],
        "margin_px":MARGIN_PX,
        "central_plane_rmse_mm":fit["median_rmse_mm"],
        "max_per_frame_normal_spread_deg":fit["max_normal_deviation_deg"],
        "inner_polygon_erosion_delta_deg":rounded(jitter,5),
        "frames_accepted":fit["frames_accepted"],
        "sampled_pixels_inside_polygon":fit["sampled_pixels_inside_polygon"],
        "high_confidence_fraction":fit["high_confidence_fraction"],
        "low_vendor_confidence_warning":fit["high_confidence_fraction"]<.01,
        "unverified_intrinsic_distortion_warning":True
    })
    # Apparent normal remains a research diagnostic and is never certified.
    return report,fit["normal"],s

def run(paths,annotations=None):
    if len(paths) not in (1,2):raise ValueError("Provide one or two ZIPs")
    manifest={"schema_version":1,"sessions":[]} if annotations is None else json.loads(Path(annotations).read_text(encoding="utf-8"))
    if manifest.get("schema_version")!=1 or not isinstance(manifest.get("sessions"),list):
        raise ValueError("Invalid annotation manifest schema")
    hashes=[item.get("sha256") for item in manifest["sessions"] if isinstance(item,dict)]
    if len(hashes)!=len(set(hashes)):
        raise ValueError("Duplicate annotations for the same archive")
    reports=[];normals=[];sessions=[]
    for path in paths:
        digest=sha256(path)
        entry=next((item for item in manifest["sessions"] if item.get("sha256")==digest),None)
        rep,n,s=session_diagnostic(path,entry)
        reports.append(rep);normals.append(n);sessions.append(s)
    result={
        "sessions":reports,
        "physical_grade_accuracy_certified":False,
        "manual_annotations_are_not_ground_truth":True,
        "calibration_bias_not_known":True,
        "camera_mount_stationarity_proven":False}
    if len(paths)==2:
        fields=("width","height","camera_id","intrinsics","sensor_orientation_degrees")
        geometry=all(sessions[0][f]==sessions[1][f] for f in fields)
        result["camera_geometry_compatible"]=geometry
        result["apparent_normal_change_deg"]=rounded(angle_deg(*normals),5) if geometry else None
        result["difference_is_physical_tilt_certified"]=False
        result["measured_board_slope_percent_points"]=None
    return result

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("zip",nargs="+",type=Path)
    p.add_argument("--annotations",type=Path,help="Private local JSON polygon manifest")
    p.add_argument("--output",type=Path,help="Private local report output")
    args=p.parse_args()
    try:out=json.dumps(run(args.zip,args.annotations),ensure_ascii=False,indent=2)+"\n"
    except (ValueError,KeyError,zipfile.BadZipFile) as e:p.error(str(e))
    if args.output:args.output.write_text(out,encoding="utf-8")
    else:print(out,end="")
