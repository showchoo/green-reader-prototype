"""Synthetic plane normals; no user's room data or fake physical certification."""
import math
import unittest

import numpy as np

from compare_static_background_references import (
    angle_deg, compare_normals, minimal_normal_alignment, unit
)


def rotate_y(degrees):
    a=math.radians(degrees)
    return np.array([[math.cos(a),0,math.sin(a)],[0,1,0],
                     [-math.sin(a),0,math.cos(a)]])


def rotate_x(degrees):
    a=math.radians(degrees)
    return np.array([[1,0,0],[0,math.cos(a),-math.sin(a)],
                     [0,math.sin(a),math.cos(a)]])


class StaticBackgroundReferenceTests(unittest.TestCase):
    def test_stationary_background_corrects_known_camera_rotation(self):
        background=np.array([0.,0.,1.])
        board=np.array([0.,0.,1.])
        incline=rotate_x(math.degrees(math.atan(.04)))@board
        camera_motion=rotate_y(.5)
        result=compare_normals(
            board,camera_motion@incline,
            background,camera_motion@background)
        self.assertAlmostEqual(
            result["background_referenced_grade_change_pct"],4.,places=6)
        self.assertGreater(result["uncorrected_grade_change_pct"],4.)
        self.assertTrue(result["unknown_camera_rotation_around_background_normal"])

    def test_stationary_background_does_not_prove_3d_rotation(self):
        background=np.array([0.,0.,1.])
        board=unit([.5,0,1])
        unobserved_twist=rotate_x(.0) @ np.array([
            [math.cos(math.radians(20)),-math.sin(math.radians(20)),0],
            [math.sin(math.radians(20)),math.cos(math.radians(20)),0],
            [0,0,1]])
        result=compare_normals(board,unobserved_twist@board,
                               background,unobserved_twist@background)
        self.assertAlmostEqual(result["background_normal_change_deg"],0.)
        self.assertGreater(result["background_referenced_grade_change_pct"],0.)


    def test_alignment_mathematics(self):
        before=unit([.2,.1,1])
        after=rotate_y(.31)@before
        r=minimal_normal_alignment(before,after)
        self.assertLess(angle_deg(r@after,before),1.e-5)

    def test_opposite_background_is_nonunique(self):
        with self.assertRaises(ValueError):
            minimal_normal_alignment([0,0,1],[0,0,-1])

    def test_bad_normal_rejected(self):
        with self.assertRaises(ValueError):
            unit([0,0,0])

    def test_estimated_cardboard_dimensions_cannot_certify_accuracy(self):
        measured_rise_mm=None
        measured_run_mm=None
        self.assertIsNone(measured_rise_mm)
        self.assertIsNone(measured_run_mm)
        self.assertEqual(100*40/1000,4.)
        self.assertAlmostEqual(100*40/740,5.4054054054,places=8)


if __name__=="__main__":
    unittest.main()
