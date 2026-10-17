"""Synthetic private-annotation HTML regression tests; no real user DEPTH16."""
import base64
import json
from pathlib import Path
import re
import struct
import tempfile
import unittest
import zipfile

from render_private_depth_annotation import render,sha256,preview_images
from test_audit_depth16_confidence_stability import fixture as small_fixture
from audit_depth16_confidence_stability import read_session


class AnnotationViewerTests(unittest.TestCase):
    def test_html_binds_to_exact_zip_and_embeds_valid_png(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"test-session.zip"
            small_fixture(path)
            text,meta=render(path)
            self.assertEqual(meta["sha256"],sha256(path))
            self.assertEqual((meta["width"],meta["height"]),(16,8))
            self.assertTrue(meta["board_semantics_unproven"])
            self.assertFalse(meta["four_corners_independently_verified"])
            self.assertFalse(meta["physical_slope_certified"])
            self.assertIn("完全オフライン",text)
            self.assertIn("manual_depth_view",text)
            self.assertIn("pointerdown",text)
            self.assertIn("corners_px",text)
            imgs=re.findall(r'const (?:DISTANCE|CONFIDENCE)="([^"]+)";',text)
            self.assertEqual(len(imgs),2)
            for png in map(base64.b64decode,imgs):
                self.assertTrue(png.startswith(b"\x89PNG\r\n\x1a\n"))
                self.assertEqual(struct.unpack(">II",png[16:24]),(16,8))
            self.assertNotIn("<script src=",text.lower())
            self.assertNotIn("fetch(",text)
            self.assertNotIn("XMLHttpRequest",text)
            self.assertNotIn("__METADATA__",text)
            self.assertNotIn("__DISTANCE_PNG__",text)

    def test_invalid_empty_zip_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"broken.zip"
            with zipfile.ZipFile(path,"w") as z:z.writestr("x.txt","empty")
            with self.assertRaises(ValueError):render(path)

    def test_vendor_low_confidence_does_not_automatically_approve_board(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"low.zip";small_fixture(path,conf=3)
            result,meta=render(path)
            self.assertIn("板の四隅",result)
            self.assertFalse(meta["four_corners_independently_verified"])
            self.assertIn("confidence_preview_uses_last_valid_frame",meta)
            self.assertTrue(meta["confidence_map_not_a_ground_truth_accuracy_metric"])

    def test_privacy_escapes_zip_filename_json(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'bad<script>alert(1).zip'
            small_fixture(path)
            html,meta=render(path)
            self.assertIn("\\u003c",html)
            self.assertNotIn("bad<script>alert(1).zip",html)
            self.assertEqual(meta["zip_name"],path.name)

if __name__=="__main__":unittest.main()
