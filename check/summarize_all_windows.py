"""Summarize exhaustive local audit without changing evidence or model geometry."""
import json,csv,gzip,sys,collections,hashlib
from pathlib import Path
root=Path(__file__).resolve().parents[1];d=root/'window-audit';a=json.load(open(d/'after/windows_full.json'));before=json.load(open(d/'before/windows_full.json'));B={r['id']:r for r in before['windows']}
for r in a['windows']:
 reasons=[]
 for hit in r['near_blockers']:
  kind=hit['kind'];obj=hit['object']
  if kind=='frame':continue
  if obj=='Cathedral_stone':reason='original_shared_nave_tower_wall' if '/tier_1/E/' in r['id'] or 'tower_SE_stage' in r['id'] or 'nave_clerestory' in r['component'] else 'original_flying_buttress'
  elif obj=='CathInterior_timber':reason='original_tower_floor'
  elif obj=='CathRoof_timber':reason='original_cathedral_roof_timber'
  elif kind=='roof' and r['building_id']=='W1' and r['category']=='main':reason='original_sagged_eave'
  elif kind=='roof':reason='REVIEW_UNEXPLAINED_ROOF'
  elif kind=='structural_timber':reason='original_structural_half_timber'
  elif kind=='original_chimney':reason='original_chimney_preserved'
  elif kind=='ruin_rubble':reason='original_ruin_end_masonry_preserved'
  else:reason='REVIEW_'+obj
  if reason not in reasons:reasons.append(reason)
 r['occlusion_reasons']=reasons
 r['diagnostic']='decorative_opaque_preserved' if r['category']=='decorative_blind' else ('STRUCTURALLY_OCCLUDED_NOT_OPAQUE_GLASS' if reasons else ('PASS_MISSING_RUIN_PANE_OPEN' if r['pane_missing'] else 'PASS_TRANSPARENT_CLEAR_WALL'))
 r['repair_ray_delta']=dict(before_clear=B[r['id']]['clear_wall_samples'],after_clear=r['clear_wall_samples'],total=r['probe_count'],before_decor=B[r['id']]['near_transparent_decor_layers'],after_decor=r['near_transparent_decor_layers'])
summary={}
for bid in sorted({r['building_id'] for r in a['windows']}):
 rows=[r for r in a['windows'] if r['building_id']==bid];true=[r for r in rows if r['category']!='decorative_blind']
 summary[bid]=dict(true_windows=len(true),transparent_glazed=sum(r['material_transparent'] for r in true),opaque_glazed=sum(r['material_opaque'] for r in true),entire_ruin_panes_missing=sum(r['pane_missing'] for r in true),partly_or_fully_structurally_occluded=sum(bool(r['occlusion_reasons']) for r in true),fully_blocked_near_band=sum(r['clear_wall_samples']==0 for r in true),decorative_blinds=len(rows)-len(true),categories=dict(collections.Counter(r['category'] for r in rows)),floor_orientation={})
 for fl in sorted({r['floor'] for r in rows}):summary[bid]['floor_orientation'][fl]={direction:[r['id'] for r in rows if r['floor']==fl and r['orientation']==direction] for direction in ('N','E','S','W')}
S=dict(total_true_windows=sum(s['true_windows'] for s in summary.values()),transparent_glazed=sum(s['transparent_glazed'] for s in summary.values()),opaque_glazed=sum(s['opaque_glazed'] for s in summary.values()),entire_ruin_panes_missing=sum(s['entire_ruin_panes_missing'] for s in summary.values()),structurally_occluded=sum(s['partly_or_fully_structurally_occluded'] for s in summary.values()),fully_blocked=sum(s['fully_blocked_near_band'] for s in summary.values()),decorative_blinds=5,solid_spire_ornaments=4,probe_points=sum(r['probe_count'] for r in a['windows']),glb_ray_mismatches=sum(sum(r['glb_ray_presence_mismatches'].values()) for r in a['windows']),unexplained=[r['id'] for r in a['windows'] if any(v.startswith('REVIEW') for v in r['occlusion_reasons'])])
a['summary']=S;a['buildings']=summary
with gzip.open(d/'windows_all.json.gz','wt') as f:json.dump(a,f)
(d/'summary.json').write_text(json.dumps(dict(totals=S,buildings=summary),indent=2))
keys=['id','building_id','category','component','floor','orientation','pane_missing','material_transparent','material_opaque','actual_face_count','probe_count','clear_wall_samples','own_pane_samples','wall_clear_fraction','diagnostic','occlusion_reasons','glb_ray_presence_mismatches']
with (d/'windows_all.csv').open('w') as f:
 w=csv.DictWriter(f,keys);w.writeheader();w.writerows({k:json.dumps(r[k]) if isinstance(r[k],(list,dict)) else r[k] for k in keys} for r in a['windows'])
(d/'decorative_ornaments.json').write_text(json.dumps(a['decorative_spire_ornaments'],indent=2))
print(json.dumps(S));print('BUILDING TABLE')
for k,v in summary.items():print(k,v['true_windows'],v['transparent_glazed'],v['entire_ruin_panes_missing'],v['partly_or_fully_structurally_occluded'],v['fully_blocked_near_band'])
print('REPAIR CHANGES',[(r['id'],r['repair_ray_delta']) for r in a['windows'] if r['repair_ray_delta']['before_clear']!=r['repair_ray_delta']['after_clear'] or r['repair_ray_delta']['before_decor']!=r['repair_ray_delta']['after_decor']])
