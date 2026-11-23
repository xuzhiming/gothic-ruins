"""Full-window saved-asset regression; audit report must be freshly regenerated."""
import json,sys,unittest
report=json.load(open(sys.argv[1]));sys.argv=sys.argv[:1]
W={r['id']:r for r in report['windows']}
class AllWindows(unittest.TestCase):
 def test_exhaustive_geometry_mapping(self):
  c=report['coverage'];self.assertEqual(c['missing_generated_face_occurrences'],0);self.assertFalse(c['unknown_glass_faces']);self.assertFalse(c['unmatched_window_slots']);self.assertEqual(len(W),365)
 def test_true_glass_material_not_opaque(self):
  for r in W.values():
   if r['category']!='decorative_blind' and not r['pane_missing']:self.assertTrue(r['material_transparent'],r['id'])
 def test_nw_dormer_has_no_uncut_roof_lip(self):
  r=W['NW/dormer/dormer/attic/S/1'];bad=[h for p in r['ray_evidence'] for h in p['from_outside'] if h['kind']=='roof'];self.assertFalse(bad,repr(bad))
 def test_rose_has_no_wall_weather_decal_across_opening(self):
  r=W['Cathedral/rose/facade_rose/upper_facade/S/1'];self.assertFalse(r['near_transparent_decor_layers'])
 def test_glb_preserves_alpha_and_geometry(self):
  for doc in report['glb'].values():
   m=doc['window_materials']['Glass'];self.assertEqual(m['alphaMode'],'BLEND');self.assertTrue(m['doubleSided']);self.assertAlmostEqual(m['pbrMetallicRoughness']['baseColorFactor'][3],.24,places=5);self.assertEqual(m['pbrMetallicRoughness']['metallicFactor'],0);self.assertEqual(doc['triangles_by_window_material'],{'Glass':5516,'Glass_blind':440})
 def test_each_exported_glb_window_matches_scene_ray_presence(self):
  for r in W.values():
   self.assertEqual(set(r['glb_ray_presence_mismatches']),{'building.glb','web/building_opt.glb'})
   self.assertTrue(all(v==0 for v in r['glb_ray_presence_mismatches'].values()),r['id'])
 def test_each_window_has_bidirectional_evidence(self):
  for r in W.values():
   self.assertGreater(r['probe_count'],15,r['id'])
   for p in r['ray_evidence']:self.assertEqual(bool(p['from_outside']),bool(p['from_inside']),r['id']);self.assertEqual(bool(p['pane_from_outside']),bool(p['pane_from_inside']),r['id'])
 def test_decorative_blinds_remain_opaque(self):
  a=[r for r in W.values() if r['category']=='decorative_blind'];self.assertEqual(len(a),5);self.assertTrue(all(r['material_opaque'] for r in a));self.assertEqual(len(report['decorative_spire_ornaments']),4)
if __name__=='__main__':unittest.main(verbosity=2)
