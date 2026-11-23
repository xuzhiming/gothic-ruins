import sys,os,unittest
sys.path.insert(0,os.path.join(os.path.dirname(os.path.dirname(__file__)),'src'))
import geom
from mathutils import Vector
from mathutils.bvhtree import BVHTree
import window_apertures as wa
class ApertureTests(unittest.TestCase):
 def test_rectangular_through_hole(self):
  b=geom.Bucket('test','stone')
  wa.panel(b,[(0,0),(4,0),(4,4),(0,4)], [[(1,1),(3,1),(3,3),(1,3)]], (0,0,0),(1,0,0),(0,0,1),1)
  t=BVHTree.FromPolygons(b.v,b.f)
  self.assertIsNone(t.ray_cast(Vector((2,-2,2)),Vector((0,1,0)),4)[0])
  self.assertIsNotNone(t.ray_cast(Vector((.5,-2,2)),Vector((0,1,0)),4)[0])
  area=sum(geom.newell([b.v[i] for i in f]).length/2 for f in b.f if abs(geom.newell([b.v[i] for i in f]).normalized().y)>.99)
  self.assertAlmostEqual(area,24,places=4)
 def test_clipping_preserves_loop_uv_alignment(self):
  b=geom.Bucket('test','slate'); b.uvframe=(Vector((0,0,0)),Vector((1,0,0)),Vector((0,1,0)))
  geom.box(b,0,4,0,4,0,.2)
  planes=[(Vector((1,0,0)),2.5),(Vector((-1,0,0)),-1.5),(Vector((0,1,0)),2.5),(Vector((0,-1,0)),-1.5)]
  wa.clip_new_roof(b,0,[planes])
  self.assertEqual(len(b.v),sum(len(f) for f in b.f),'make_obj foreach_set requires loop-aligned UVs')
  for f in b.f:
   for i in f:
    self.assertAlmostEqual(b.uv[i][0],b.v[i].x/2,places=5)
    self.assertAlmostEqual(b.uv[i][1],b.v[i].y/2,places=5)
 def test_gable_preserves_bounds(self):
  b=geom.Bucket('test','plaster')
  wa.panel(b,[(0,0),(6,0),(3,5)], [[(2.5,1),(3.5,1),(3.5,2),(2.5,2)]], (0,0,0),(1,0,0),(0,0,1),.3)
  self.assertEqual(min(v.x for v in b.v),0)
  self.assertEqual(max(v.z for v in b.v),5)
if __name__=='__main__':
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ApertureTests))
 if not result.wasSuccessful(): raise SystemExit(1)
