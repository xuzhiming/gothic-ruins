import unittest,sys
sys.path.insert(0,'src')
import face_materials as F
class TestFaces(unittest.TestCase):
 def test_south(self):
  self.assertEqual(F.select('House_E4_brick','Brick',(25.8,-32.901,9),(0,-1,0)), 'south')
 def test_street(self):
  self.assertEqual(F.select('House_E4_plaster','Plaster',(20.34,-24,9),(-1,0,0)), 'street')
 def test_excludes(self):
  for obj,mat,c,n in [('House_E3_brick','Brick',(20.35,-24,9),(-1,0,0)),('House_E4_timber','Timber',(25,-32.901,9),(0,-1,0)),('House_E4_brick','Brick',(31.35,-24,9),(1,0,0)),('House_E4_brick','Brick',(25,-14.574,9),(0,1,0)),('House_E4_brick','Brick',(20.35,-24,9),(0,0,1)),('House_E4_brick','Brick',(20.8,-24,9),(-1,0,0))]:
   self.assertIsNone(F.select(obj,mat,c,n))
if __name__=='__main__': unittest.main()
