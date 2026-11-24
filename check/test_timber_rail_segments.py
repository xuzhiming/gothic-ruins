"""Unit tests for timber_face horizontal-rail gaps at wall openings.

Fails until src.geom.timber_rail_segments exists and splits sole/mid rails
around door (and any other vertically overlapping) openings, while leaving
the storey head rail continuous when it sits above the opening.
"""
import sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


class TimberRailSegments(unittest.TestCase):
    W = 12.0
    z0 = 4.2
    z1 = 7.4
    ops = [
        {"s": 5.4, "w": 1.2, "h": 2.4, "kind": "flat"},
        {"s": 2.0, "w": 0.9, "h": 1.2, "sill": 1.0, "kind": "flat"},
    ]
    # jamb posts sit at s ± w/2 ± 0.09; rails must stop there
    door_gap = (5.4 - 0.6 - 0.09, 5.4 + 0.6 + 0.09)  # (4.71, 6.09)

    def segs(self, zz):
        from timber_rails import timber_rail_segments
        return timber_rail_segments(self.W, self.z0, self.z1, zz, self.ops)

    def test_import(self):
        from timber_rails import timber_rail_segments  # noqa: F401

    def test_sole_rail_gaps_door_only(self):
        segs = self.segs(self.z0 + 0.08)
        self.assertEqual(len(segs), 2)
        self.assertAlmostEqual(segs[0][0], 0.05)
        self.assertAlmostEqual(segs[0][1], self.door_gap[0])
        self.assertAlmostEqual(segs[1][0], self.door_gap[1])
        self.assertAlmostEqual(segs[1][1], self.W - 0.05)
        # gap covers the full 1.2 m door plus jamb posts
        self.assertGreater(segs[1][0] - segs[0][1], 1.2)
        # window at s=2.0, sill 1.0 does not meet the sole rail
        self.assertTrue(any(a < 2.0 < b for a, b in segs))

    def test_mid_rail_gaps_door_only(self):
        segs = self.segs(self.z0 + 0.85)
        self.assertEqual(len(segs), 2)
        self.assertAlmostEqual(segs[0][1], self.door_gap[0])
        self.assertAlmostEqual(segs[1][0], self.door_gap[1])

    def test_head_rail_stays_continuous_above_door(self):
        segs = self.segs(self.z1 - 0.14)
        self.assertEqual(segs, [(0.05, self.W - 0.05)])

    def test_no_openings_is_one_full_rail(self):
        from timber_rails import timber_rail_segments
        segs = timber_rail_segments(self.W, self.z0, self.z1, self.z0 + 0.08, [])
        self.assertEqual(segs, [(0.05, self.W - 0.05)])

    def test_round_door_taller_opening_still_gapped(self):
        from timber_rails import timber_rail_segments
        ops = [{"s": 5.4, "w": 1.2, "h": 2.75, "kind": "round"}]
        segs = timber_rail_segments(self.W, self.z0, self.z1, self.z0 + 0.85, ops)
        self.assertEqual(len(segs), 2)
        self.assertAlmostEqual(segs[0][1], self.door_gap[0])


if __name__ == "__main__":
    unittest.main()
