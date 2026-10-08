#!/usr/bin/env python3
"""Offline-only camera-view/Depth sampling diagnostics (v8.5/v8.6).

Reads scan archives or directories WITHOUT opening camera.jpg. v8.6 records
local camera rays and native pixel intrinsics, enabling an estimate of where
each depth point fell in the camera image. No slope is corrected and these
metrics cannot distinguish real green curvature from sensor distortion.

Usage:
  python3 scripts/analyze_precision_view_geometry.py path/to/Session.zip \
      --output /tmp/greenreader_view_geometry.csv
"""
import argparse
from collections import defaultdict
import csv
import io
import math
from pathlib import Path
import statistics
import sys
import zipfile

DIAGNOSTIC = "collector_diagnostics.txt"
POINTS = "precision_depth_points.csv"
SOURCES = "precision_depth_sources.csv"
CSV_COLUMNS = [
    "scan", "status", "pose_records", "pose_raw", "pose_full",
    "duplicate_pose_keys", "sampled_points", "matched_sampled_points",
    "matched_fraction", "sampled_rays", "pixel_inside_fraction",
    "camera_span_m", "camera_height_median", "camera_pitch_down_median_deg",
    "camera_pitch_span_deg", "depth_age_median_ms", "depth_age_p95_ms",
    "axial_range_median_m", "off_axis_angle_median_deg",
    "off_axis_angle_p95_deg", "raw_rays", "full_rays",
    "same_voxel_view_pairs", "edge_minus_center_height_median_mm",
    "view_comparison_status"
]


def pct(values, p):
    if not values:
        return None
    values = sorted(values)
    k = p * (len(values) - 1)
    lo = int(k)
    hi = min(lo + 1, len(values) - 1)
    return values[lo] + (values[hi] - values[lo]) * (k - lo)


def rounded(value):
    return "" if value is None or not math.isfinite(value) else round(value, 5)


def load_poses(text):
    """Parse repeated FRAME_POSE blocks with per-window headers and footer."""
    parsed, duplicates = {}, set()
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        if not lines[index].startswith("FRAME_POSE_V1_BEGIN"):
            index += 1
            continue
        start = index + 1
        index = start
        while index < len(lines) and not lines[index].startswith("FRAME_POSE_V1_END"):
            index += 1
        if index >= len(lines):
            break  # Truncated block cannot be treated as evidence.
        rows = lines[start:index]
        index += 1
        if not rows or not rows[0].startswith("depth_timestamp_ns,"):
            continue
        for row in csv.DictReader(rows):
            try:
                k = (int(row["depth_timestamp_ns"]), row["source"])
                if k[1] not in {"raw", "full"}:
                    continue
            except (KeyError, TypeError, ValueError):
                continue
            if k in parsed:
                duplicates.add(k)
            else:
                parsed[k] = row
    # Reused depth-frame keys across windows cannot safely be disambiguated.
    for k in duplicates:
        parsed.pop(k, None)
    return parsed, len(duplicates)


def getnum(row, key):
    try:
        v = float(row[key])
        return v if math.isfinite(v) else None
    except (KeyError, TypeError, ValueError):
        return None


def ray_metrics(point, pose):
    fields = (
        "camera_local_x_m", "camera_local_y_m", "camera_local_z_m",
        "camera_forward_local_x", "camera_forward_local_y",
        "camera_forward_local_z", "camera_right_local_x",
        "camera_right_local_y", "camera_right_local_z",
        "intrinsics_fx", "intrinsics_fy", "intrinsics_cx", "intrinsics_cy",
        "projection_width", "projection_height"
    )
    vals = [getnum(pose, key) for key in fields]
    if any(x is None for x in vals):
        return None
    (px, py, pz, fxv, fyv, fzv, rx, ry, rz,
     intrfx, intrfy, cx, cy, width, height) = vals
    if min(intrfx, intrfy, width, height) <= 0:
        return None
    vx = point[0] - px
    vy = point[1] - py
    vz = point[2] - pz
    axial = vx * fxv + vy * fyv + vz * fzv
    if axial <= 0.001:
        return None
    right = vx * rx + vy * ry + vz * rz
    # In a right-handed camera frame, UP = RIGHT cross FORWARD.
    ux = ry * fzv - rz * fyv
    uy = rz * fxv - rx * fzv
    uz = rx * fyv - ry * fxv
    up = vx * ux + vy * uy + vz * uz
    angle = math.degrees(math.atan2(math.hypot(right, up), axial))
    pixelx = intrfx * (right / axial) + cx
    pixely = cy - intrfy * (up / axial)
    inside = 0 <= pixelx < width and 0 <= pixely < height
    return axial, angle, inside


def _parse_sources(text):
    rows = {}
    for row in csv.DictReader(io.StringIO(text)):
        try:
            i = int(row["index"])
            frame = int(row["frame_timestamp_ns"])
            src = row["depth_source"]
        except (KeyError, ValueError, TypeError):
            continue
        if src in {"raw", "full"}:
            rows[i] = (frame, src)
    return rows


def matched_view_height_shift(samples):
    """Compare CENTER vs EDGE views of the SAME (source, 5cm XY-ground voxel).

    Samples contain (source, x_voxel, z_voxel, offaxis_deg, local_height_m,
    frame_timestamp). Require >=2 distinct frames per viewpoint group so
    multiple pixels in one frame cannot fabricate temporal replication.

    These comparisons remove much *spatial* green slope confounding but
    may still reflect AR tracking drift, occlusion or sample selection.
    The number is a research diagnostic, NOT a slope correction.
    """
    groups = defaultdict(lambda: {"center": defaultdict(list),
                                  "edge": defaultdict(list)})
    for source, ix, iz, angle, height, timestamp in samples:
        if not math.isfinite(height):
            continue
        view = "center" if angle <= 12. else "edge" if angle >= 20. else None
        if view is None:
            continue
        groups[source, ix, iz][view][timestamp].append(height)
    differences = []
    for grouped in groups.values():
        center_frames = grouped["center"]
        edge_frames = grouped["edge"]
        if len(center_frames) < 2 or len(edge_frames) < 2:
            continue
        center = [statistics.median(heights) for heights in center_frames.values()]
        edge = [statistics.median(heights) for heights in edge_frames.values()]
        medc = statistics.median(center)
        mede = statistics.median(edge)
        # A cell that jumps around across frames is not a stable reference.
        madc = statistics.median(abs(h-medc) for h in center)
        made = statistics.median(abs(h-mede) for h in edge)
        if madc > 0.025 or made > 0.025:
            continue
        differences.append((mede - medc)*1000.)
    return len(differences), (statistics.median(differences) if differences else None)


def analyze_scan(name, diag, points, sources, sample_step=8):
    out = {col: "" for col in CSV_COLUMNS}
    out["scan"] = name
    poses, duplicates = load_poses(diag)
    out["pose_records"] = len(poses)
    out["pose_raw"] = sum(k[1] == "raw" for k in poses)
    out["pose_full"] = sum(k[1] == "full" for k in poses)
    out["duplicate_pose_keys"] = duplicates
    out["status"] = "legacy_no_pose" if not poses else "legacy_pose_no_view_axes"
    if not poses:
        return out
    source_map = _parse_sources(sources) if sources else {}
    ages, heights, pitch, positions = [], [], [], []
    for (timestamp, _), pose in poses.items():
        frame = getnum(pose, "camera_frame_timestamp_ns")
        if frame is not None:
            ages.append((frame - timestamp) / 1e6)  # signed milliseconds
        xyz = [getnum(pose, c) for c in (
            "camera_local_x_m", "camera_local_y_m", "camera_local_z_m")]
        if all(v is not None for v in xyz):
            positions.append(xyz)
            heights.append(xyz[1])
        local_y = getnum(pose, "camera_forward_local_y")
        if local_y is not None:
            pitch.append(math.degrees(math.asin(max(-1., min(1., -local_y)))))
    if positions:
        spans = [max(p[i] for p in positions) - min(p[i] for p in positions)
                 for i in range(3)]
        out["camera_span_m"] = rounded(math.sqrt(sum(s*s for s in spans)))
    out["camera_height_median"] = rounded(pct(heights, .5))
    out["camera_pitch_down_median_deg"] = rounded(pct(pitch, .5))
    if pitch:
        out["camera_pitch_span_deg"] = rounded(max(pitch) - min(pitch))
    out["depth_age_median_ms"] = rounded(pct(ages, .5))
    out["depth_age_p95_ms"] = rounded(pct(ages, .95))
    if not source_map:
        out["status"] = "pose_without_source_sidecar"
        return out
    matched, sampled, rays, inside = 0, 0, 0, 0
    ranges, angles, repeated_view_samples = [], [], []
    rays_by_source = {"raw": 0, "full": 0}
    for rownum, row in enumerate(csv.DictReader(io.StringIO(points))):
        if rownum % sample_step != 0:
            continue
        sampled += 1
        try:
            i = int(row["index"])
            x, y, z = [float(row[k]) for k in ("x_m", "y_m", "z_m")]
            if not all(math.isfinite(v) for v in (x,y,z)):
                continue
        except (KeyError, TypeError, ValueError):
            continue
        key = source_map.get(i)
        if key is None or key not in poses:
            continue
        matched += 1
        ray = ray_metrics((x,y,z), poses[key])
        if ray is None:
            continue
        depth, angle, is_inside = ray
        ranges.append(depth)
        angles.append(angle)
        repeated_view_samples.append((
            key[1], math.floor(x / .05), math.floor(z / .05),
            angle, y, key[0]
        ))
        rays += 1
        inside += is_inside
        rays_by_source[key[1]] += 1
    out["sampled_points"] = sampled
    out["matched_sampled_points"] = matched
    out["matched_fraction"] = rounded(matched / sampled) if sampled else ""
    out["sampled_rays"] = rays
    out["pixel_inside_fraction"] = rounded(inside / rays) if rays else ""
    out["axial_range_median_m"] = rounded(pct(ranges, .5))
    out["off_axis_angle_median_deg"] = rounded(pct(angles, .5))
    out["off_axis_angle_p95_deg"] = rounded(pct(angles, .95))
    out["raw_rays"] = rays_by_source["raw"]
    out["full_rays"] = rays_by_source["full"]
    shared_voxels, view_shift = matched_view_height_shift(repeated_view_samples)
    out["same_voxel_view_pairs"] = shared_voxels
    out["edge_minus_center_height_median_mm"] = rounded(view_shift)
    out["view_comparison_status"] = (
        "comparable_view_groups" if shared_voxels >= 8
        else "insufficient_shared_voxels"
    )
    out["status"] = (
        "geometry_ready" if rays >= 20 and matched >= 20
        else "insufficient_geometry" if rays == 0 else "low_geometry_coverage"
    )
    return out


def archive_rows(path, sample_step=8):
    with zipfile.ZipFile(path) as z:
        valid = {n for n in z.namelist() if not n.endswith("/")}
        for name in sorted(n for n in valid if n.endswith(DIAGNOSTIC)):
            root = name[:-len(DIAGNOSTIC)]
            point_name = root + POINTS
            if point_name not in valid:
                continue
            # Never inspect or extract camera.jpg or other private media.
            diag = z.read(name).decode("utf8", "replace")
            poses, _ = load_poses(diag)
            if poses:
                pts = z.read(point_name).decode("utf8", "replace")
                side = (z.read(root+SOURCES).decode("utf8","replace")
                        if root+SOURCES in valid else "")
            else:
                pts, side = "", ""
            yield analyze_scan(name[:-len(DIAGNOSTIC)].rstrip("/"),
                               diag, pts, side, sample_step)


def directory_rows(path, sample_step=8):
    for diagfile in sorted(path.rglob(DIAGNOSTIC)):
        pointfile = diagfile.parent / POINTS
        if not pointfile.is_file():
            continue
        diag = diagfile.read_text(encoding="utf8", errors="replace")
        poses, _ = load_poses(diag)
        if poses:
            pts = pointfile.read_text(encoding="utf8",errors="replace")
            sidefile = diagfile.parent / SOURCES
            side = sidefile.read_text(encoding="utf8",errors="replace") if sidefile.is_file() else ""
        else:
            pts, side = "", ""
        yield analyze_scan(str(diagfile.parent), diag, pts, side, sample_step)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("inputs", nargs="+", type=Path,
                    help="Session ZIP archive(s) or directory tree(s)")
    ap.add_argument("--output", required=True, type=Path,
                    help="destination summary CSV")
    ap.add_argument("--sample-step", type=int, default=8,
                    help="deterministic stride through saved depth points (default: 8)")
    args = ap.parse_args(argv)
    if args.sample_step < 1:
        ap.error("--sample-step must be >= 1")
    results = []
    for path in args.inputs:
        if path.is_dir():
            results.extend(directory_rows(path, args.sample_step))
        elif path.is_file() and zipfile.is_zipfile(path):
            results.extend(archive_rows(path, args.sample_step))
        else:
            ap.error(f"not a directory or ZIP archive: {path}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(results)
    status_counts = {}
    for r in results:
        status_counts[r["status"]] = status_counts.get(r["status"], 0) + 1
    print(f"Scans: {len(results)}  Status: {status_counts}")
    print(f"Saved summary: {args.output}")
    print("CAUTION: view coverage/timestamp statistics are diagnostics, not slope accuracy.")


if __name__ == "__main__":
    main()
