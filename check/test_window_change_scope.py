import json,sys,unittest
x=json.load(open(sys.argv[1]));sys.argv=sys.argv[:1]
class Scope(unittest.TestCase):
 def test_only_confirmed_defect_meshes_changed(self):
  self.assertEqual(set(x['changed']),{'House_NW_slate','Decal_decal_crack'},'No roof edits on already-clear E1/W3 windows')
if __name__=='__main__':unittest.main(verbosity=2)
