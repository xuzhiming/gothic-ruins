"""Approved t24u contract, pure layout (no Blender)."""
import unittest, json, sys, importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
class Layout(unittest.TestCase):
 def setUp(self):
  self.P=json.loads((ROOT/'params.json').read_text())
 def module(self):
  self.assertIsNotNone(importlib.util.find_spec('alley_layout'),'missing approved alley layout module')
  import alley_layout;return alley_layout
 def test_eight_real_net_width_reservations(self):
  m=self.module(); gaps=[]
  for side in 'WE':
   hs=m.row_layout(self.P['houses'],side)
   self.assertEqual(len(hs),5)
   gaps += [a['south']-b['north']-2*self.P['houses']['alleys']['finish_allowance'] for a,b in zip(hs,hs[1:])]
  self.assertEqual(len(gaps),8);self.assertTrue(all(g>=1.4-1e-6 for g in gaps),gaps)
 def test_depth_datums_and_proportional_widths(self):
  m=self.module();self.assertEqual(self.P['houses']['row_x'],[20.35,31.35])
  for s,end in [('W',-32.9),('E',-32.901)]:
   hs=m.row_layout(self.P['houses'],s);self.assertAlmostEqual(hs[0]['north'],30.3);self.assertAlmostEqual(hs[-1]['south'],end,places=6)
   ratios=[h['w']/h['w_px'] for h in hs];self.assertLess(max(ratios)-min(ratios),1e-7)
 def test_partition_stair_clearance(self):
  m=self.module()
  for s in 'WE':
   for h in m.row_layout(self.P['houses'],s):
    v=m.partition_v(self.P['houses'],h['w']);self.assertGreater(v-.45,7.40);self.assertLessEqual(v+.75,h['w']-.35+1e-6)
 def test_original_ground_window_slots_and_door_clearance(self):
  m=self.module();self.assertTrue(hasattr(m,'ground_window_centers'),'missing slot-preserving GF layout')
  for side in 'WE':
   for h in m.row_layout(self.P['houses'],side):
    centers=m.ground_window_centers(self.P['houses'],h)
    baseline=[v for v in self.P['houses']['list'] if v['row']==side]
    oldw=round(63.2*h['w_px']/sum(v['w_px'] for v in baseline),3)
    dv=oldw*h['door'];xs=[1.2+(oldw-2.4)*(i+.5)/h['win'][0] for i in range(h['win'][0])]
    expected=sum(abs(x-dv)>1.5 for x in xs)
    self.assertEqual(len(centers),expected,h['id'])
    for x in centers:self.assertGreater(abs(x-h['w']*h['door']),.6+h['win_w']/2+.1,h['id'])
 def test_pane_damage_is_semantic_not_row_rng_order(self):
  m=self.module();self.assertTrue(hasattr(m,'preserve_window_damage'),'missing stable per-slot ruin preservation')
  H=self.P['houses'];ops=[{'glass':True} for _ in H['window_damage']['W1/street/F2/E']]
  result=m.preserve_window_damage(H,'W1','street',2,'E',ops)
  self.assertEqual([o['pane_missing'] for o in result],H['window_damage']['W1/street/F2/E'])
 def test_routes_and_outer_extension(self):
  m=self.module();routes=m.alley_routes(self.P)
  self.assertEqual(sum(r['kind']=='alley' for r in routes),8)
  self.assertEqual(sum(r['kind']=='rear' for r in routes),2)
  self.assertEqual(sum(r['kind']=='north_turn' for r in routes),2)
  self.assertEqual(self.P['site']['main'][:2],[-33.15,33.15])
  for r in routes:
   if r['kind']=='north_turn':
    self.assertEqual(r['path'][-1][1],44.)
    self.assertEqual(abs(r['path'][-1][0]),12.5)
if __name__=='__main__':unittest.main(verbosity=2)
