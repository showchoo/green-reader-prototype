"""Synthetic v11.1 IMU ZIP tests: time domains, absent evidence, invalid rows."""
import csv
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from audit_depth16_imu_evidence import audit

ROOT="Session_HW_DEPTH_TEST/Putt_000/Scan_01_DEPTH16"


def csv_text(fields,rows):
    out=io.StringIO()
    writer=csv.DictWriter(out,fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue()


def make_zip(path,source=1,gyro=True):
    rows=[]
    count={"accelerometer":6,"gravity":6,"gyroscope":6 if gyro else 0,
           "gyroscope_uncalibrated":0}
    for name,num in count.items():
        for i in range(num):
            rows.append({
                "sensor_type":name,
                "sensor_timestamp_ns":1000000000+i*20000000,
                "callback_elapsed_ns":1000001000+i*20000000,
                "x":0.1 if name=="gyroscope" else 0,
                "y":0,"z":1 if name=="gravity" else 9.8,
                "bias_x":"","bias_y":"","bias_z":"","accuracy":3})
    imu=csv_text([
        "sensor_type","sensor_timestamp_ns","callback_elapsed_ns",
        "x","y","z","bias_x","bias_y","bias_z","accuracy"
    ],rows)
    frames=csv_text(["image_timestamp_ns"],
                    [{"image_timestamp_ns":1000000000+i*20000000}
                     for i in range(6)])
    gravity=csv_text(["sensor_timestamp_ns","gx","gy","gz"],
                     [{"sensor_timestamp_ns":1000000000+i*20000000,
                       "gx":0,"gy":0,"gz":9.8} for i in range(6)])
    md={"camera_timestamp_source":source,
        "camera_vs_sensor_timestamp_comparable":source==1,
        "sensor_listener_registered":{k:(v>0) for k,v in count.items()},
        "per_sensor_sample_count":count,
        "per_sensor_cap_dropped":{k:0 for k in count},
        "per_sensor_out_of_order_dropped":{k:0 for k in count}}
    bundle={
        "camera2_sensor_metadata.json":json.dumps(md),
        "camera2_calibration.json":json.dumps(
            {"sensor_timestamp_source":source}),
        "camera2_depth_summary.json":json.dumps(
            {"frame_count":6,"schema_version":2}),
        "camera2_sensor_events.csv":imu,
        "camera2_depth_frames.csv":frames,
        "camera2_gravity.csv":gravity,
        "record_identity.json":"{}",
    }
    with zipfile.ZipFile(path,"w") as z:
        for name,s in bundle.items():
            z.writestr(ROOT+"/"+name,s)


class ImuEvidenceAuditTests(unittest.TestCase):
    def test_realtime_data_is_still_not_pose_certification(self):
        with tempfile.TemporaryDirectory() as tmp:
            f=Path(tmp)/"capture.zip"
            make_zip(f)
            report=audit(f)
            self.assertEqual(report["diagnostic_state"],
                             "RAW_MOTION_EVIDENCE_AVAILABLE")
            self.assertTrue(report["camera_sensor_timebases_comparable"])
            self.assertFalse(report["board_grade_accuracy_certified"])
            self.assertFalse(report["device_mount_moved_proven"])
            self.assertEqual(report["frame_times_within_sensor_stream"]["gyroscope"],6)

    def test_unknown_camera_timestamp_source_blocks_alignment(self):
        with tempfile.TemporaryDirectory() as tmp:
            f=Path(tmp)/"unknown.zip"
            make_zip(f,source=0)
            report=audit(f)
            self.assertFalse(report["camera_sensor_timebases_comparable"])
            self.assertEqual(report["frame_times_within_sensor_stream"],{})
            self.assertEqual(report["diagnostic_state"],
                             "TIMESTAMP_OR_RAW_MOTION_EVIDENCE_INCOMPLETE")

    def test_missing_gyroscope_fails_motion_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            f=Path(tmp)/"no_gyro.zip"
            make_zip(f,gyro=False)
            report=audit(f)
            self.assertFalse(report["gyro_and_accelerometer_both_recorded"])
            self.assertFalse(report["board_grade_accuracy_certified"])

    def test_old_v11_zip_never_claims_v111_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            f=Path(tmp)/"old.zip"
            with zipfile.ZipFile(f,"w") as z:
                z.writestr("old/camera2_gravity.csv","x\n")
            with self.assertRaises(ValueError):
                audit(f)

if __name__=="__main__":
    unittest.main()
