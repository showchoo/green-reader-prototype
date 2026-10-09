#!/usr/bin/env python3
"""Privacy-preserving Green Reader per-putt repeatability and integrity audit.

Reads metadata/identity/quality and optional collector diagnostics, but NEVER
reads photos or raw depth point clouds. Supports one/many Session ZIPs or dirs.

  python3 scripts/analyze_precision_session_consistency.py Session.zip \
      --scan-csv scan_summary.csv --putt-csv putt_repeatability.csv

Research-only: consistency is NOT absolute slope accuracy or putt direction
truth. A direction disagreement may reflect an actual change in alignment.
"""
import argparse
import csv
import io
import json
import math
from pathlib import Path
import re
import statistics
import zipfile

SCAN_FIELDS = [
    "archive", "scan_path", "session_id", "hole_number", "putt_id",
    "scan_index", "app_version", "outcome", "metadata_state",
    "distance_m", "cross_percent", "long_percent", "quality_score",
    "quality_tier", "uncertainty_percent", "unique_depth_frames",
    "raw_accepted_frames", "full_accepted_frames", "tracking_ratio",
    "camera_travel_m", "pose_blocks", "recorded_camera_pose_rows",
    "potential_depth_pose_rows", "note"
]
PUTT_FIELDS = [
    "session_id", "hole_number", "putt_id", "total_scans", "successes",
    "failures", "comparable_successes", "distance_span_m",
    "heading_span_deg", "cross_span_percent", "long_span_percent",
    "strong_sign_conflict", "repeatability_status", "evidence_warning"
]


def finite(value):
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (ValueError, TypeError):
        return None


def rounded(value):
    return "" if value is None else round(value, 5)


def parse_json(data):
    if data is None:
        return None, "missing"
    try:
        return json.loads(data), "valid"
    except (ValueError, UnicodeDecodeError):
        return None, "invalid"


def recover_legacy_v71(raw, identity):
    """Best effort ONLY for the known v7.1 raw triple-quoted JSON issue.

    Do not overwrite the original file, do not use as evidence of correctness
    for arbitrary free-text fields. Normal JSON parsing is tried first.
    """
    doc, state = parse_json(raw)
    if doc is not None:
        return doc, state
    if not raw or not identity or identity.get("app_version") != "Precision 7.1":
        return None, state
    try:
        text = raw.decode("utf8")
        if not re.match(r'^\s*\{\s*\\"schema_version\\":', text):
            return None, state
        repaired = text.replace(r'\"', '"')
        loaded = json.loads(repaired)
        if not isinstance(loaded, dict) or loaded.get("app_version") != "Precision 7.1":
            return None, state
        return loaded, "legacy_recovered_untrusted"
    except (ValueError, UnicodeDecodeError):
        return None, state


def maybe_read(reader, name):
    try:
        return reader(name)
    except (KeyError, OSError, FileNotFoundError):
        return None


def read_record(archive, scan_dir, reader):
    base = scan_dir.rstrip("/") + "/"
    identity, identity_state = parse_json(maybe_read(reader, base+"record_identity.json"))
    identity = identity if isinstance(identity, dict) else {}
    metadata, state = recover_legacy_v71(maybe_read(reader, base+"metadata.json"), identity)
    metadata = metadata if isinstance(metadata, dict) else {}
    quality, _ = parse_json(maybe_read(reader, base+"scan_quality.json"))
    quality = quality if isinstance(quality, dict) else {}
    collector_bytes = maybe_read(reader, base+"collector_diagnostics.txt")
    collector = collector_bytes.decode("utf8", "replace") if collector_bytes else ""
    starts = list(re.finditer(r"(?m)^FRAME_POSE_V1_BEGIN\b", collector))
    pose_lines = len(re.findall(r"(?m)^\d+,\d+,(?:raw|full),", collector))
    motion_lines = 0
    for line in collector.splitlines():
        if not re.match(r"^\d+,\d+,(raw|full),", line):
            continue
        cells = next(csv.reader([line]))
        # v8.7 extends 23 existing columns with nearest-frame details.
        if len(cells) >= 27 and all(cells[-4:]):
            motion_lines += 1
    status = metadata.get("outcome", "success" if "overall_cross_percent" in metadata else "unknown")
    fields = {
        "archive": archive, "scan_path": scan_dir,
        "session_id": identity.get("session_id", ""),
        "hole_number": identity.get("hole_number", ""),
        "putt_id": identity.get("putt_id", ""),
        "scan_index": identity.get("scan_index", ""),
        "app_version": identity.get("app_version", metadata.get("app_version", "")),
        "outcome": status, "metadata_state": state,
        "distance_m": rounded(finite(metadata.get("distance_m"))),
        "cross_percent": rounded(finite(metadata.get("overall_cross_percent"))),
        "long_percent": rounded(finite(metadata.get("overall_longitudinal_percent"))),
        "quality_score": quality.get("score", ""),
        "quality_tier": quality.get("tier", ""),
        "uncertainty_percent": rounded(finite(quality.get("estimated_slope_uncertainty_percent"))),
        "unique_depth_frames": quality.get("unique_depth_frames", ""),
        "raw_accepted_frames": quality.get("raw_accepted_frames", ""),
        "full_accepted_frames": quality.get("full_accepted_frames", ""),
        "tracking_ratio": rounded(finite(quality.get("tracking_ratio"))),
        "camera_travel_m": rounded(finite(quality.get("camera_travel_m"))),
        "pose_blocks": len(starts), "recorded_camera_pose_rows": pose_lines,
        "potential_depth_pose_rows": motion_lines,
        "note": ""
    }
    if identity_state != "valid":
        fields["note"] = "missing_or_invalid_record_identity"
    if state == "legacy_recovered_untrusted":
        fields["note"] = (fields["note"] + ";" if fields["note"] else "") + "legacy_v71_best_effort_numbers"
    if status == "success" and (finite(fields["distance_m"]) is None or finite(fields["cross_percent"]) is None):
        fields["note"] = (fields["note"] + ";" if fields["note"] else "") + "success_missing_slope"
    # Keep marker heading only in internal group comparison, never export camera coords.
    try:
        ball, cup = metadata["ball_world"], metadata["cup_world"]
        forward = (float(cup["x"])-float(ball["x"]),
                   float(cup["z"])-float(ball["z"]))
        if not all(math.isfinite(v) for v in forward) or math.hypot(*forward) < .05:
            forward = None
    except (TypeError, ValueError, KeyError):
        forward = None
    return fields, forward


def records_in_zip(path):
    with zipfile.ZipFile(path) as z:
        names = set(n for n in z.namelist() if not n.endswith("/"))
        dirs = sorted(n.removesuffix("record_identity.json").rstrip("/")
                      for n in names if n.endswith("/record_identity.json"))
        for directory in dirs:
            yield read_record(path.name, directory, z.read)


def records_in_directory(path):
    for identity in sorted(path.rglob("record_identity.json")):
        directory = identity.parent
        def reader(name):
            return (path/name).read_bytes()
        yield read_record(path.name, str(directory.relative_to(path)), reader)


def summarize_putts(records):
    groups = {}
    for row, heading in records:
        key = (str(row["session_id"]), str(row["hole_number"]), str(row["putt_id"]))
        groups.setdefault(key, []).append((row, heading))
    results = []
    for key, entries in sorted(groups.items()):
        successes = [(r,h) for r,h in entries
                     if r["outcome"] == "success" and
                     finite(r["distance_m"]) is not None and
                     finite(r["cross_percent"]) is not None and
                     finite(r["long_percent"]) is not None]
        failed = sum(r["outcome"] == "failure" for r,_ in entries)
        result = dict.fromkeys(PUTT_FIELDS, "")
        result.update({
            "session_id": key[0], "hole_number": key[1], "putt_id": key[2],
            "total_scans": len(entries), "successes": len(successes), "failures": failed,
            "comparable_successes": 0, "strong_sign_conflict": False,
            "repeatability_status": "insufficient_successful_repeats",
            "evidence_warning": "Internal consistency does not validate physical slope truth"
        })
        if len(successes) < 2:
            results.append(result)
            continue
        distances = [float(r["distance_m"]) for r,_ in successes]
        headings = [h for _,h in successes]
        span = max(distances) - min(distances)
        result["distance_span_m"] = rounded(span)
        tolerance = max(.20, .15 * statistics.median(distances))
        if span > tolerance:
            result["repeatability_status"] = "distance_mismatch"
            results.append(result)
            continue
        if any(h is None for h in headings):
            result["repeatability_status"] = "heading_unknown"
            results.append(result)
            continue
        degrees = []
        head0 = headings[0]
        for h in headings[1:]:
            dot = head0[0]*h[0]+head0[1]*h[1]
            norm = math.hypot(*head0)*math.hypot(*h)
            degrees.append(math.degrees(math.acos(max(-1.0,min(1.0,dot/norm)))))
        heading_span = max(degrees, default=0.)
        result["heading_span_deg"] = rounded(heading_span)
        if heading_span > 15.:
            result["repeatability_status"] = "heading_mismatch"
            results.append(result)
            continue
        cross = [float(r["cross_percent"]) for r,_ in successes]
        along = [float(r["long_percent"]) for r,_ in successes]
        result["comparable_successes"] = len(successes)
        result["cross_span_percent"] = rounded(max(cross)-min(cross))
        result["long_span_percent"] = rounded(max(along)-min(along))
        conflict = any(a > 1.2 and b < -1.2 for a in cross for b in cross)
        result["strong_sign_conflict"] = conflict
        result["repeatability_status"] = (
            "opposite_strong_signs" if conflict else
            "cross_slopes_vary" if max(cross)-min(cross) >= 1.5 else
            "internally_consistent_not_ground_truth"
        )
        results.append(result)
    return results


def write_csv(path, fieldnames, values):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf8", newline="") as stream:
        w = csv.DictWriter(stream, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(values)


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("inputs", nargs="+", type=Path)
    p.add_argument("--scan-csv", required=True, type=Path)
    p.add_argument("--putt-csv", required=True, type=Path)
    args=p.parse_args(argv)
    collected=[]
    for path in args.inputs:
        if path.is_dir():
            collected.extend(records_in_directory(path))
        elif path.is_file() and zipfile.is_zipfile(path):
            collected.extend(records_in_zip(path))
        else:
            p.error(f"Not a ZIP archive or directory: {path}")
    scans=[r for r,h in collected]
    putts=summarize_putts(collected)
    write_csv(args.scan_csv,SCAN_FIELDS,scans)
    write_csv(args.putt_csv,PUTT_FIELDS,putts)
    counts={}
    for g in putts:
        k=g["repeatability_status"]
        counts[k]=counts.get(k,0)+1
    print("Scans:",len(scans),"Putt groups:",len(putts))
    print("Repeatability categories:",counts)
    print("Legacy metadata recovered:",sum(r["metadata_state"]=="legacy_recovered_untrusted" for r in scans))
    print("CAUTION: consistency cannot establish true cross-slope sign or absolute accuracy.")


if __name__=="__main__":
    main()
