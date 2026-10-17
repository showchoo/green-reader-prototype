#!/usr/bin/env python3
"""S20+ RGB research Session ZIP: pose-backed stereo *feasibility*, not truth.

Only consumes camera JPEGs + archived per-frame intrinsics/pose, never ARCore
Depth. Camera pose still comes from ARCore VIO and is NOT an independently
surveyed camera trajectory. Outputs numerical diagnostics only; no user images
are written and NO physical accuracy / aim-line success is certified.

Requirements: numpy scipy opencv-python-headless.
"""
import argparse
import csv
import io
import json
import math
import zipfile
from pathlib import Path

import cv2
import numpy as np
from scipy.spatial.transform import Rotation

S = np.diag([1.0, -1.0, -1.0])  # ARCore (+x,+y,-z) -> OpenCV (+x,+down,+z)


def projection(center, camera_quat_xyzw, K):
    R = Rotation.from_quat(camera_quat_xyzw).as_matrix()
    world_to_cv = S @ R.T
    return K @ np.column_stack((world_to_cv, -world_to_cv @ center))


def project(P, xyz):
    homogeneous = P @ np.column_stack((xyz, np.ones(len(xyz)))).T
    return (homogeneous[:2] / homogeneous[2]).T


def triangulate_pair(P0, P1, points0, points1):
    """Return world xyz, per-point maximum reprojection error, positive depths."""
    p0 = np.asarray(points0, dtype=np.float64)
    p1 = np.asarray(points1, dtype=np.float64)
    if not len(p0):
        return np.empty((0, 3)), np.empty(0), np.empty(0, dtype=bool)
    homogeneous = cv2.triangulatePoints(P0, P1, p0.T, p1.T).T
    xyz = homogeneous[:, :3] / homogeneous[:, 3, None]
    reprojection = np.maximum(
        np.linalg.norm(project(P0, xyz) - p0, axis=1),
        np.linalg.norm(project(P1, xyz) - p1, axis=1))
    z0 = (P0 @ np.column_stack((xyz, np.ones(len(xyz)))).T)[2]
    z1 = (P1 @ np.column_stack((xyz, np.ones(len(xyz)))).T)[2]
    return xyz, reprojection, (z0 > 0) & (z1 > 0)


def fit_height_plane(points, expected_floor_y, seed=13):
    """RANSAC geometric consistency only, no floor-grade certification."""
    points = np.asarray(points, dtype=float)
    pts = points[np.isfinite(points).all(axis=1)]
    pts = pts[np.abs(pts[:, 1] - expected_floor_y) < 0.18]
    if len(pts) < 60:
        return None
    xy = np.column_stack((pts[:, 0], pts[:, 2], np.ones(len(pts))))
    height = pts[:, 1]
    rng = np.random.default_rng(seed)
    best = np.zeros(len(pts), dtype=bool)
    for _ in range(240):
        subset = rng.choice(len(pts), 5, replace=False)
        design = xy[subset]
        if np.linalg.cond(design) > 10000:
            continue
        slope = np.linalg.lstsq(design, height[subset], rcond=None)[0]
        if abs(slope[0]) > 0.30 or abs(slope[1]) > 0.30:
            continue
        inliers = abs(xy @ slope - height) < 0.020
        if inliers.sum() > best.sum():
            best = inliers
    if best.sum() < 55:
        return None
    fit = np.linalg.lstsq(xy[best], height[best], rcond=None)[0]
    resid = xy[best] @ fit - height[best]
    return dict(candidate_count=len(pts), inlier_count=int(best.sum()),
                plane=(float(fit[0]), float(fit[1]), float(fit[2])),
                inlier_rmse_mm=round(float(1000*np.sqrt(np.mean(resid**2))), 1))


def allowed_jpeg(raw):
    return len(raw) > 1024 and raw[:2] == b"\xff\xd8" and raw[-2:] == b"\xff\xd9"


def inspect_session(filename, floor_color="wood"):
    """Aggregate stats only. Floor color mask is an indoor experiment parameter."""
    filename = Path(filename)
    with zipfile.ZipFile(filename) as z:
        prefixes = sorted(n.rsplit("/", 1)[0] for n in z.namelist()
                          if n.endswith("/rgb_frames.csv"))
        if not prefixes:
            return {"status": "NO_RGB_MANIFEST", "metric_slope_certified": False}
        result = []
        for prefix in prefixes:
            rows = list(csv.DictReader(io.StringIO(
                z.read(prefix+"/rgb_frames.csv").decode("utf-8"))))
            if len(rows) < 12:
                result.append({"scan": prefix, "status": "NOT_ENOUGH_FRAMES",
                               "frames": len(rows)})
                continue
            frames, images, cameras, rotations, matrices, times, widths = [], [], [], [], [], [], []
            try:
                for row in rows:
                    idx = int(row["index"])
                    path = prefix + "/rgb_%04d.jpg" % idx
                    raw = z.read(path)
                    if not allowed_jpeg(raw):
                        raise ValueError("Invalid or zero-byte JPEG at frame "+str(idx))
                    image = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
                    if image is None:
                        raise ValueError("JPEG decode failure at frame "+str(idx))
                    if image.shape[1] != int(row.get("jpeg_width",row["width"])) or image.shape[0] != int(row.get("jpeg_height",row["height"])):
                        raise ValueError("JPEG dimension mismatch "+str(idx))
                    center = np.array([float(row["camera_t"+k]) for k in "xyz"])
                    quat = np.array([float(row["camera_q"+k]) for k in "xyzw"])
                    K = np.array([[float(row.get("jpeg_fx",row["fx"])), 0.0, float(row.get("jpeg_cx",row["cx"]))],
                                  [0.0, float(row.get("jpeg_fy",row["fy"])), float(row.get("jpeg_cy",row["cy"]))],
                                  [0., 0., 1.]])
                    t = int(row["ar_frame_timestamp_ns"])
                    ti = int(row["cpu_image_timestamp_ns"])
                    frames.append((t, ti))
                    images.append(image)
                    cameras.append(center)
                    rotations.append(quat)
                    matrices.append(projection(center,quat,K))
                    widths.append(K)
                centers = np.array(cameras)
                ft = np.array(frames, dtype=np.int64)
                if not (np.diff(ft[:,0]) > 0).all():
                    raise ValueError("Nonmonotonic frame timestamps")
                max_time_delta_ms = float(np.max(abs(ft[:,0]-ft[:,1]))/1e6)
                if max_time_delta_ms > 50:
                    raise ValueError("Unaligned frame/image timestamps")
                baseline = float(np.max(np.linalg.norm(centers[:,None]-centers[None],axis=-1)))
                if baseline < .12:
                    result.append({"scan":prefix,"status":"LOW_CAMERA_BASELINE",
                                   "images":len(images),"baseline_m":round(baseline,3)})
                    continue
                # Indoor color segmentation is deliberately not a generic golf
                # turf segmentation model. Reports are research-only.
                gray = [cv2.cvtColor(im,cv2.COLOR_BGR2GRAY) for im in images]
                masks = []
                for im in images:
                    if floor_color == "wood":
                        hsv = cv2.cvtColor(im,cv2.COLOR_BGR2HSV)
                        mask = cv2.inRange(hsv,np.array([10,35,55]),np.array([23,185,245]))
                        mask=cv2.morphologyEx(mask,cv2.MORPH_OPEN,np.ones((3,3),np.uint8))
                        mask=cv2.erode(mask,np.ones((5,5),np.uint8))
                    else:
                        mask=np.ones(im.shape[:2],dtype=np.uint8)*255
                    masks.append(mask)
                sift=cv2.SIFT_create(nfeatures=2500,contrastThreshold=.01,edgeThreshold=16)
                feat=[sift.detectAndCompute(im,mask) for im,mask in zip(gray,masks)]
                matcher=cv2.BFMatcher(cv2.NORM_L2)
                anchor_y = None
                for row in rows:
                    try:
                        by=float(row["ball_world_y"]);cy=float(row["cup_world_y"])
                        anchor_y = (by+cy)/2
                        break
                    except (KeyError,ValueError):
                        continue
                if anchor_y is None:
                    raise ValueError("Missing ball/cup anchor reference for floor mask")
                baseline_vec=np.array([
                    float(rows[0]["cup_world_x"])-float(rows[0]["ball_world_x"]),
                    float(rows[0]["cup_world_z"])-float(rows[0]["ball_world_z"])
                ])
                if np.linalg.norm(baseline_vec) < .4:
                    raise ValueError("Short ball/cup baseline")
                baseline_vec /= np.linalg.norm(baseline_vec)
                candidate_pairs=[]
                for i in range(0,len(images),3):
                    for step in (7,10,14,18):
                        j=i+step
                        if j < len(images) and np.linalg.norm(centers[i]-centers[j]) >= .08:
                            candidate_pairs.append((i,j))
                pairs=[]
                for i,j in candidate_pairs:
                    kpi,dsi=feat[i];kpj,dsj=feat[j]
                    if dsi is None or dsj is None:continue
                    ratios=matcher.knnMatch(dsi,dsj,k=2)
                    good=[a for a,b in ratios if a.distance < .72*b.distance]
                    if len(good)<30:continue
                    p0=np.float32([kpi[m.queryIdx].pt for m in good])
                    p1=np.float32([kpj[m.trainIdx].pt for m in good])
                    H,inliers=cv2.findHomography(p0,p1,cv2.RANSAC,2.5)
                    if inliers is None:continue
                    idx=np.where(inliers.ravel().astype(bool))[0]
                    if len(idx)<40:continue
                    if len(idx)>350:idx=idx[np.linspace(0,len(idx)-1,350).astype(int)]
                    p0,p1=p0[idx],p1[idx]
                    xyz,reproj,positive=triangulate_pair(matrices[i],matrices[j],p0,p1)
                    ray0=xyz-centers[i];ray1=xyz-centers[j]
                    cosine=(ray0*ray1).sum(axis=1)/np.maximum(
                        np.linalg.norm(ray0,axis=1)*np.linalg.norm(ray1,axis=1),1.e-9)
                    angle=np.rad2deg(np.arccos(np.clip(cosine,-1,1)))
                    depth0=np.linalg.norm(ray0,axis=1);depth1=np.linalg.norm(ray1,axis=1)
                    valid=positive & (reproj<2) & (angle>.6) & (depth0>.25) & (depth1>.25) & (depth0<6) & (depth1<6)
                    plane=fit_height_plane(xyz[valid],anchor_y,seed=13)
                    entry={"frames":[i+1,j+1],"matches":len(good),
                           "homography_inliers":int(inliers.sum()),
                           "triangulated_candidates":int(valid.sum()),
                           "camera_baseline_cm":round(float(100*np.linalg.norm(centers[i]-centers[j])),1)}
                    if plane:
                        a,b,_=plane["plane"]
                        entry.update({"floor_inliers":plane["inlier_count"],
                                      "floor_fit_rmse_mm":plane["inlier_rmse_mm"],
                                      "candidate_long_grade_percent":round(float(100*np.dot([a,b],baseline_vec)),2),
                                      "candidate_cross_grade_percent":round(float(100*np.dot([a,b],[-baseline_vec[1],baseline_vec[0]])),2)})
                    pairs.append(entry)
                grades=[q["candidate_long_grade_percent"] for q in pairs
                        if "candidate_long_grade_percent" in q]
                result.append({
                    "scan":prefix,"status":"GEOMETRIC_CANDIDATES_NOT_CERTIFIED",
                    "device":rows[0].get("device","SC-52A"),
                    "image_count":len(images),
                    "max_camera_baseline_cm":round(100*baseline,1),
                    "rgb_cpu_image_offset_ms_median":
                        round(float(np.median((ft[:,1]-ft[:,0])/1e6)),3),
                    "rgb_resolution":list(images[0].shape[1::-1]),
                    "image_pairs":pairs,
                    "triangulated_candidate_observations":sum(x["triangulated_candidates"] for x in pairs),
                    "candidate_long_grade_span_pp":
                        round(float(max(grades)-min(grades)),2) if len(grades)>1 else None,
                    "metric_slope_certified":False,
                    "slope_accuracy_claim":"NONE: paired floor estimates share ARCore VIO pose errors"
                })
            except (KeyError,ValueError,zipfile.BadZipFile) as e:
                result.append({"scan":prefix,"status":"INVALID_RGB_CAPTURE",
                               "reason":str(e),"metric_slope_certified":False})
        return {"source":filename.name,"surface_selector":floor_color,
                "session_status":"RESEARCH_NOT_PRODUCT",
                "scans":result,"metric_slope_certified":False,
                "limitations":"Not independent SfM; metric stereo uses ARCore camera poses. Image color mask only suits this indoor wood-floor feasibility test. Grade comparisons are internal, not independently surveyed physical accuracy."}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("session_zip",type=Path)
    parser.add_argument("--surface",choices=["wood","all"],default="wood")
    parser.add_argument("--output",type=Path)
    args=parser.parse_args()
    result=inspect_session(args.session_zip,args.surface)
    contents=json.dumps(result,ensure_ascii=False,indent=2)
    if args.output:args.output.write_text(contents,encoding="utf-8")
    else:print(contents)


if __name__=="__main__":
    main()
