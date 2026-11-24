"""Unit tests for timber_face horizontal-rail gaps at explicit street doors only.

Windows (including low-sill ones that vertically overlap the mid rail, and
round-headed ones) must leave both sole and mid rails continuous — that through-
window rail is the existing facade style. kind=flat/round is shared by doors
and windows and must not be used as the discriminator. Only ops with
opening == "door" split sole/mid rails, stopping at the jamb posts. The
storey head rail stays continuous when it sits above the door.
"""
import sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


class TimberRailSegments(unittest.TestCase):
    W = 12.0
    z0 = 4.2
    z1 = 7.4
    door = {"s": 5.4, "w": 1.2, "h": 2.4, "kind": "flat", "opening": "door"}
    window = {"s": 2.0, "w": 0.9, "h": 1.2, "sill": 1.0, "kind": "flat", "glass": True}
    ops = [door, window]
    # jamb posts sit at s ± w/2 ± 0.09; rails must stop there
    door_gap = (5.4 - 0.6 - 0.09, 5.4 + 0.6 + 0.09)  # (4.71, 6.09)

    def segs(self, zz, ops=None):
        from timber_rails import timber_rail_segments
        return timber_rail_segments(self.W, self.z0, self.z1, zz, self.ops if ops is None else ops)

    def test_import(self):
        from timber_rails import timber_rail_segments  # noqa: F401

    def test_sole_rail_gaps_explicit_door_only(self):
        segs = self.segs(self.z0 + 0.08)
        self.assertEqual(len(segs), 2)
        self.assertAlmostEqual(segs[0][0], 0.05)
        self.assertAlmostEqual(segs[0][1], self.door_gap[0])
        self.assertAlmostEqual(segs[1][0], self.door_gap[1])
        self.assertAlmostEqual(segs[1][1], self.W - 0.05)
        self.assertGreater(segs[1][0] - segs[0][1], 1.2)
        # neighbouring window is not a cut
        self.assertTrue(any(a < 2.0 < b for a, b in segs))

    def test_mid_rail_gaps_explicit_door_only(self):
        segs = self.segs(self.z0 + 0.85)
        self.assertEqual(len(segs), 2)
        self.assertAlmostEqual(segs[0][1], self.door_gap[0])
        self.assertAlmostEqual(segs[1][0], self.door_gap[1])

    def test_head_rail_stays_continuous_above_door(self):
        segs = self.segs(self.z1 - 0.14)
        self.assertEqual(segs, [(0.05, self.W - 0.05)])

    def test_no_openings_is_one_full_rail(self):
        segs = self.segs(self.z0 + 0.08, ops=[])
        self.assertEqual(segs, [(0.05, self.W - 0.05)])

    def test_windows_only_both_horizontal_rails_stay_continuous(self):
        """Default facade windows (sill 0.9) may overlap the mid rail; do not cut."""
        wins = [
            {"s": 2.0, "w": 0.9, "h": 2.25, "sill": 0.9, "kind": "flat", "glass": True},
            {"s": 6.0, "w": 0.9, "h": 2.55, "sill": 0.9, "kind": "round", "glass": True},
        ]
        for zz in (self.z0 + 0.08, self.z0 + 0.85):
            self.assertEqual(self.segs(zz, ops=wins), [(0.05, self.W - 0.05)], zz)

    def test_low_sill_zero_window_covering_mid_rail_is_not_cut(self):
        """A window whose height covers the mid rail still must not split it."""
        win = {"s": 3.0, "w": 1.0, "h": 2.25, "sill": 0.0, "kind": "flat", "glass": True}
        for zz in (self.z0 + 0.08, self.z0 + 0.85):
            self.assertEqual(self.segs(zz, ops=[win]), [(0.05, self.W - 0.05)], zz)

    def test_unmarked_flat_or_round_opening_is_not_a_door(self):
        """kind is shared by doors and windows; without opening=='door' do not gap."""
        for kind, h in (("flat", 2.4), ("round", 2.75)):
            op = {"s": 5.4, "w": 1.2, "h": h, "kind": kind}
            segs = self.segs(self.z0 + 0.85, ops=[op])
            self.assertEqual(segs, [(0.05, self.W - 0.05)], kind)

    def test_explicit_round_door_still_gapped_at_jambs(self):
        ops = [{"s": 5.4, "w": 1.2, "h": 2.75, "kind": "round", "opening": "door"}]
        segs = self.segs(self.z0 + 0.85, ops=ops)
        self.assertEqual(len(segs), 2)
        self.assertAlmostEqual(segs[0][1], self.door_gap[0])
        self.assertAlmostEqual(segs[1][0], self.door_gap[1])
        # head rail above the taller round door remains continuous
        self.assertEqual(self.segs(self.z1 - 0.14, ops=ops), [(0.05, self.W - 0.05)])


if __name__ == "__main__":
    unittest.main()
