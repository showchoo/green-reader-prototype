"""Tests for private-data-safe per-putt audit and v7.1 legacy recovery."""
import csv
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze_precision_session_consistency as checker


def mock_scan(index, slope=1.6, distance=1.5, app="Precision 8.8",
              session="20261009_fixture", hole=1, putt=1,
              heading=(0,-1), failure=False, invalid_legacy=False):
    prefix = f"Session_{session}/Putt_{putt:03d}/Scan_{index:02d}_fixture"
    id = {"session_id":session,"hole_number":hole,"putt_id":putt,
          "scan_index":index,"app_version":app}
    metadata = {"schema_version":2 if failure else 1,
                "app_version":app,
                "outcome":"failure" if failure else "success",
                "ball_world":{"x":0,"y":0,"z":0},
                "cup_world":{"x":heading[0],"y":0,"z":heading[1]}}
    if not failure:
        metadata.update({"distance_m":distance,
                         "overall_cross_percent":slope,
                         "overall_longitudinal_percent":1.0})
    text=json.dumps(metadata,ensure_ascii=False,indent=2)
    if invalid_legacy:
        text=text.replace('"',r'\"')
    output = {
        f"{prefix}/record_identity.json":json.dumps(id).encode("utf8"),
        f"{prefix}/metadata.json":text.encode("utf8"),
        f"{prefix}/collector_diagnostics.txt":b"attempts=20",
    }
    if not failure:
        output[f"{prefix}/scan_quality.json"] = json.dumps({
            "score":90,"tier":"GOOD","unique_depth_frames":32,
            "raw_accepted_frames":5,"full_accepted_frames":27,
            "estimated_slope_uncertainty_percent":.4,
            "tracking_ratio":1.0,"camera_travel_m":.11
        }).encode()
    return output


def process(*data):
    with tempfile.TemporaryDirectory() as folder:
        archive=Path(folder)/"session.zip"
        with zipfile.ZipFile(archive,"w") as z:
            for payload in data:
                for name, value in payload.items():
                    z.writestr(name,value)
            z.writestr("Session/camera.jpg",b"not a real JPEG")
        return list(checker.records_in_zip(archive))


class SessionConsistencyTests(unittest.TestCase):
    def test_valid_json_and_one_scan_not_repeatable(self):
        records=process(mock_scan(1))
        self.assertEqual("valid",records[0][0]["metadata_state"])
        self.assertEqual(90,records[0][0]["quality_score"])
        groups=checker.summarize_putts(records)
        self.assertEqual(1,len(groups))
        self.assertEqual("insufficient_successful_repeats",groups[0]["repeatability_status"])

    def test_v71_invalid_quote_metadata_is_labeled_untrusted_not_ignored(self):
        records=process(mock_scan(1,app="Precision 7.1",invalid_legacy=True))
        self.assertEqual("legacy_recovered_untrusted",records[0][0]["metadata_state"])
        self.assertEqual(1.6,records[0][0]["cross_percent"])
        self.assertIn("legacy_v71_best_effort_numbers",records[0][0]["note"])
        newer=process(mock_scan(1,app="Precision 8.8",invalid_legacy=True))
        self.assertEqual("invalid",newer[0][0]["metadata_state"])
        self.assertEqual("unknown",newer[0][0]["outcome"])

    def test_opposite_slope_signs_same_aligned_putt_are_flagged(self):
        records=process(mock_scan(1,slope=2.2),
                        mock_scan(2,slope=-2.0))
        result=checker.summarize_putts(records)[0]
        self.assertEqual("opposite_strong_signs",result["repeatability_status"])
        self.assertEqual(2,result["comparable_successes"])
        self.assertTrue(result["strong_sign_conflict"])
        self.assertAlmostEqual(4.2,result["cross_span_percent"])

    def test_small_variation_still_not_claimed_as_ground_truth(self):
        records=process(mock_scan(1,slope=1.6),mock_scan(2,slope=1.5))
        group=checker.summarize_putts(records)[0]
        self.assertEqual("internally_consistent_not_ground_truth",group["repeatability_status"])
        self.assertIn("does not validate physical slope truth",group["evidence_warning"])

    def test_distance_mismatch_prevents_false_repeatability(self):
        records=process(mock_scan(1,distance=1.5),
                        mock_scan(2,distance=3.0,slope=-2.3))
        result=checker.summarize_putts(records)[0]
        self.assertEqual("distance_mismatch",result["repeatability_status"])
        self.assertEqual(0,result["comparable_successes"])

    def test_heading_mismatch_prevents_false_repeatability(self):
        records=process(mock_scan(1,heading=(0,-1)),
                        mock_scan(2,slope=-1.9,heading=(1,0)))
        result=checker.summarize_putts(records)[0]
        self.assertEqual("heading_mismatch",result["repeatability_status"])
        self.assertEqual(90,result["heading_span_deg"])
        self.assertEqual(0,result["comparable_successes"])

    def test_a_failure_is_not_a_successful_repeat(self):
        records=process(mock_scan(1),mock_scan(2,failure=True))
        result=checker.summarize_putts(records)[0]
        self.assertEqual(1,result["successes"])
        self.assertEqual(1,result["failures"])
        self.assertEqual("insufficient_successful_repeats",result["repeatability_status"])

    def test_directory_source_and_writing_no_raw_depth_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name,data in mock_scan(1).items():
                path=root/name
                path.parent.mkdir(parents=True,exist_ok=True)
                path.write_bytes(data)
            items=list(checker.records_in_directory(root))
            self.assertEqual(1,len(items))
            scanout=root/"out"/"scans.csv"
            puttout=root/"out"/"putts.csv"
            checker.main([str(root),"--scan-csv",str(scanout),"--putt-csv",str(puttout)])
            with scanout.open(encoding="utf8") as f:
                rows=list(csv.DictReader(f))
            self.assertEqual("valid",rows[0]["metadata_state"])
            self.assertNotIn("camera.jpg",scanout.read_text())


if __name__=="__main__":
    unittest.main()
