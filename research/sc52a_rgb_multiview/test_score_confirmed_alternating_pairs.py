"""Known-condition differential response must never imply surveyed accuracy."""
import math
import unittest
import numpy as np

from score_confirmed_alternating_pairs import directional_cosine


def incline(deg):
    t=math.radians(deg)
    return np.array([math.sin(t),0.,math.cos(t)])


class ConfirmedAlternatingPairTests(unittest.TestCase):
    def test_two_reproducible_tilts_have_matching_change_direction(self):
        a=directional_cosine(incline(0),incline(1.15),
                             incline(.15),incline(1.30))
        self.assertIsNotNone(a)
        self.assertGreater(a,.999)

    def test_reversed_tilt_not_mistaken_for_repeated(self):
        a=directional_cosine(incline(0),incline(1.15),
                             incline(.15),incline(-1.0))
        self.assertLess(a,-.99)

    def test_negligible_reference_motion_has_no_meaningful_direction(self):
        self.assertIsNone(directional_cosine(
            incline(0),incline(.01),incline(.01),incline(.02)))

    def test_nonfinite_reference_is_rejected(self):
        with self.assertRaises(ValueError):
            directional_cosine([0,0,1],[float('nan'),0,1],
                               [0,0,1],[.1,0,1])

    def test_direction_is_not_a_grade_magnitude(self):
        a=directional_cosine(incline(0),incline(.3),
                             incline(.2),incline(2.2))
        self.assertGreater(a,.999)
        # Yet the actual changes were 0.3 and 2.0 degrees.
        self.assertNotAlmostEqual(.3,2.0)


if __name__=="__main__":
    unittest.main()
