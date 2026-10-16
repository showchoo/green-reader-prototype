"""Synthetic regression checks; no private room images or real-user ZIP included."""
import io
import json
import unittest
import zipfile
from pathlib import Path
import tempfile

import cv2
import numpy as np

from offline_probe import (consensus_gate, robust_plane, scan_raw,
                           slope_from_frame, track_rgb)


class IndependentGeometryTests(unittest.TestCase):
    def synthetic_frames(self, slopes, offsets):
        rng=np.random.default_rng(8901)
        records=[]
        for (long,cross),offset in zip(slopes,offsets):
            forward=rng.uniform(-.08,1.08,1400)
            lateral=rng.uniform(-.27,.27,1400)
            y=offset+long*forward/100+cross*lateral/100+rng.normal(0,.001,1400)
            records.append(slope_from_frame(
                np.column_stack((lateral,-forward,y)),0.,-1.,1.))
        return records

    def test_variable_height_offsets_on_real_flat_are_not_new_slopes(self):
        records=self.synthetic_frames([(0.,0.)]*6,
                                      [.02,.22,.04,.19,-.04,.10])
        self.assertTrue(all(r is not None for r in records))
        result=consensus_gate(records)
        self.assertEqual(result["status"],"INTERNAL_CONSENSUS_ONLY")
        self.assertFalse(result["certified_accuracy"])
        self.assertGreater(result["height_offset_span_cm"],20)
        self.assertLess(abs(result["long_pct"]),.2)

    def test_known_slope_is_not_forced_to_zero(self):
        records=self.synthetic_frames([(2.5,-1.3)]*6,
                                      [.02,.22,.04,.19,.04,.10])
        result=consensus_gate(records)
        self.assertEqual(result["status"],"INTERNAL_CONSENSUS_ONLY")
        self.assertAlmostEqual(result["long_pct"],2.5,delta=.2)
        self.assertAlmostEqual(result["cross_pct"],-1.3,delta=.2)

    def test_disagreeing_forward_slopes_are_rejected(self):
        records=self.synthetic_frames(
            [(-2,0),(2,0),(1,0),(-1,0),(3,0),(0,0)],[.10]*6)
        self.assertEqual(consensus_gate(records)["status"],"REJECT_INCONSISTENT")

    def test_three_frames_cannot_certify(self):
        records=self.synthetic_frames([(0,0)]*3,[.10]*3)
        self.assertEqual(consensus_gate(records)["status"],"INSUFFICIENT_FRAMES")

    def test_wide_but_true_cross_slope_is_not_zeroed(self):
        records=self.synthetic_frames([(0,5)]*6,[.10]*6)
        r=consensus_gate(records)
        self.assertEqual(r["status"],"INTERNAL_CONSENSUS_ONLY")
        self.assertAlmostEqual(r["cross_pct"],5.,delta=.2)


class RgbPlaneCorrespondenceTests(unittest.TestCase):
    def make_image(self):
        rng=np.random.default_rng(12345)
        im=np.zeros((1200,640),np.uint8)
        for _ in range(1000):
            pos=(int(rng.integers(20,620)),int(rng.integers(620,1160)))
            cv2.circle(im,pos,int(rng.integers(1,6)),
                       int(rng.integers(65,250)),-1)
        for y in [750,850,950,1050]:
            cv2.line(im,(10,y),(630,y),110,2)
        return im

    def run_pair(self,image_a,image_b):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"images.zip"
            with zipfile.ZipFile(p,"w") as z:
                for index,img in enumerate([image_a,image_b],start=1):
                    ok,buf=cv2.imencode(".jpg",img)
                    self.assertTrue(ok)
                    z.writestr(f"Putt_002/Scan_{index:02d}/camera.jpg",
                               buf.tobytes())
            with zipfile.ZipFile(p) as z:
                return track_rgb(z,"Putt_002")[0]

    def test_homography_matches_are_not_metric_heights(self):
        image=self.make_image()
        homography=np.array([[1.01,.008,13],[-.007,.996,17],
                             [.00002,.00004,1.]])
        transformed=cv2.warpPerspective(image,homography,(640,1200))
        result=self.run_pair(image,transformed)
        self.assertGreaterEqual(result["matched_2d_inliers"],40)
        self.assertTrue(result["trackable_floor_candidate"])
        self.assertFalse(result["measured_3d_height"])

    def test_duplicate_image_does_not_certify_slope(self):
        image=self.make_image()
        result=self.run_pair(image,image)
        self.assertGreaterEqual(result["matched_2d_inliers"],40)
        self.assertFalse(result["measured_3d_height"])


if __name__=="__main__":
    unittest.main()
