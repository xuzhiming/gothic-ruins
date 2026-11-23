"""Full saved-Blend window audit. Does not rebuild, save or modify the asset.
blender -b building.blend -P check/audit_all_windows.py -- INVENTORY OUTDIR
"""
import bpy,json,sys,hashlib,math,struct,csv,os
from pathlib import Path
from collections import Counter,defaultdict
from mathutils import Vector
from mathutils.bvhtree import BVHTree
args=sys.argv[sys.argv.index('--')+1:]; inv=json.load(open(args[0]));dest=Path(args[1]);dest.mkdir(parents=True,exist_ok=True)
root=Path(bpy.data.filepath).parent

def ph(pts):return hashlib.sha256(json.dumps(sorted(tuple(round(float(x),5) for x in p) for p in pts)).encode()).hexdigest()
def matinfo(m):
 b=m.node_tree.nodes.get('Principled BSDF') if m and m.use_nodes else None
 if not b:return dict(name=m.name if m else None,alpha=1,transmission=0,transparent=False)
 a=b.inputs['Alpha'].default_value;tr=b.inputs['Transmission Weight'].default_value
 return dict(name=m.name,alpha=a,transmission=tr,metallic=b.inputs['Metallic'].default_value,roughness=b.inputs['Roughness'].default_value,ior=b.inputs['IOR'].default_value,surface_render_method=m.surface_render_method,transparent=(a<.999 and m.surface_render_method=='BLENDED') or tr>.01,base_color_images=[n.image.name for n in m.node_tree.nodes if n.type=='TEX_IMAGE' and n.image])
materials={m.name:matinfo(m) for m in bpy.data.materials}
byhash=defaultdict(set)
for r in inv['windows']:
 for h in r['generated_face_hashes']:byhash[h].add(r['id'])
actual=defaultdict(list);vs=[];fstruct=[];structmeta=[];fpanes=[];panemeta=[];fdecor=[];decormeta=[];unknown=[]
for o in bpy.context.scene.objects:
 if o.type!='MESH':continue
 base=len(vs);world=[o.matrix_world@v.co for v in o.data.vertices];vs.extend(world)
 for p in o.data.polygons:
  m=o.data.materials[p.material_index];mi=materials[m.name];h=ph([world[i] for i in p.vertices]);ids=sorted(byhash.get(h,[]));meta=dict(object=o.name,polygon=p.index,material=m.name,window_ids=ids)
  if ids:
   actual[h].append(meta);fpanes.append([base+i for i in p.vertices]);panemeta.append(meta)
  else:
   if o.name.startswith(('Glass_','GlassBlind_')):unknown.append(meta)
   # Alpha decals do not count as opaque backing; original frames stay in the evidence BVH.
   if mi['transparent'] or o.get('role')=='decor':
    fdecor.append([base+i for i in p.vertices]);decormeta.append(meta)
   if not mi['transparent'] and o.get('role')!='decor':
    fstruct.append([base+i for i in p.vertices]);structmeta.append(meta)
Tb=BVHTree.FromPolygons(vs,fstruct);Tg=BVHTree.FromPolygons(vs,fpanes);Td=BVHTree.FromPolygons(vs,fdecor)

def hits(T,meta,a,bb,maximum=24):
 a=Vector(a);bb=Vector(bb);v=bb-a;length=v.length
 if length<1e-6:return []
 d=v/length;out=[];travel=0.
 for i in range(maximum):
  p,n,index,dist=T.ray_cast(a+d*travel,d,length-travel)
  if p is None:break
  row=dict(meta[index]);row.update(distance=round(travel+dist,5),point=[round(x,5) for x in p]);out.append(row)
  travel+=dist+.0002
  if travel>=length:break
 return out

def typ(name):
 if name.startswith(('WinFrame_','Tracery_')):return 'frame'
 if name.startswith('Chimneys_'):return 'original_chimney'
 if name.startswith('DoorLeaf_'):return 'door_leaf'
 if 'rubble' in name.lower() or name.startswith('Debris_'):return 'ruin_rubble'
 if 'timber' in name.lower():return 'structural_timber'
 if 'slate' in name.lower() or 'Roof' in name:return 'roof'
 return 'wall_or_floor'

def inside(x,y,poly):
 c=False
 for (a,b),(d,e) in zip(poly,poly[1:]+poly[:1]):
  if (b>y)!=(e>y) and x<(d-a)*(y-b)/(e-b)+a:c=not c
 return c

glb_trees={}
if (dest/'glb_decoded.json').exists():
 for k,v in json.load(open(dest/'glb_decoded.json')).items():
  glb_trees[k]=(BVHTree.FromPolygons(v['vertices'],v['triangles'],all_triangles=True),[dict(material=n) for n in v['materials']])
windows=[]
for rec in inv['windows']:
 r=dict(rec);r.pop('generated_face_hashes',None)
 own=[];unmatched=[]
 for h in rec['generated_face_hashes']:
  if h in actual:own.extend(actual[h])
  else:unmatched.append(h)
 r['actual_face_count']=len({(x['object'],x['polygon']) for x in own});r['unmatched_generated_faces']=len(unmatched)
 r['materials']=dict(Counter(x['material'] for x in own));r['material_transparent']=bool(own) and all(materials[x['material']]['transparent'] for x in own)
 r['material_opaque']=bool(own) and not r['material_transparent']
 o=Vector(r['origin']);S=Vector(r['along']);N=Vector(r['normal']).normalized();T=Vector((0,0,1));poly=[tuple(p) for p in r['polygon']]
 xmin,xmax=min(p[0] for p in poly),max(p[0] for p in poly);ymin,ymax=min(p[1] for p in poly),max(p[1] for p in poly)
 # Cross-panel pane anchors lie outside the masonry. Audit a longer interior wall band.
 exterior=r['wall_thickness']/2+.16;interior=exterior
 if r['category'] in ('attic','dormer'):exterior=.35;interior=.56
 if r['category']=='decorative_blind':exterior=.72;interior=.72
 probes=[];blockers=Counter();deepinside=Counter();deepoutside=Counter();structclear=0;frameclear=0;glass_seen=0;own_glass_seen=0;layers=Counter()
 for fx in (.06,.12,.25,.38,.62,.75,.88,.94):
  for fy in (.06,.12,.25,.38,.62,.75,.88,.94):
   x=xmin+(xmax-xmin)*fx;y=ymin+(ymax-ymin)*fy
   if not inside(x,y,poly):continue
   p=o+S*x+T*y;a=p+N*exterior;bb=p-N*interior
   out=hits(Tb,structmeta,a,bb);inn=hits(Tb,structmeta,bb,a);paneout=hits(Tg,panemeta,a,bb);panein=hits(Tg,panemeta,bb,a);decalhits=hits(Td,decormeta,a,bb)
   for h in out:h['kind']=typ(h['object']);blockers[(h['object'],h['kind'])]+=1
   noframe=[h for h in out if h['kind']!='frame']
   structclear+=not noframe;frameclear+=not out;glass_seen+=bool(paneout)
   own_glass_seen+=any(rec['id'] in h['window_ids'] for h in paneout);layers[len(paneout)]+=1
   di=hits(Tb,structmeta,bb-N*.005,bb-N*4,1);do=hits(Tb,structmeta,a+N*.005,a+N*4,1)
   if di:deepinside[di[0]['object']]+=1
   if do:deepoutside[do[0]['object']]+=1
   glbrays={k:dict(outside=hits(tree,met,a,bb),inside=hits(tree,met,bb,a)) for k,(tree,met) in glb_trees.items()}
   probes.append(dict(glb_pane_rays=glbrays,local=[round(x,5),round(y,5)],point=list(p),from_outside=out,from_inside=inn,pane_from_outside=paneout,pane_from_inside=panein,transparent_decor_layers=decalhits,first_deep_inside=di,first_deep_outside=do))
 r['ray_evidence']=probes;r['probe_count']=len(probes);r['clear_wall_samples']=structclear;r['clear_including_frame_samples']=frameclear;r['own_pane_samples']=own_glass_seen;r['any_pane_samples']=glass_seen;r['pane_surface_layer_histogram']=dict(layers)
 r['near_blockers']=[dict(object=k[0],kind=k[1],surface_hits=v) for k,v in blockers.most_common()]
 r['glb_ray_presence_mismatches']={k:sum(bool(p['pane_from_outside'])!=bool(p['glb_pane_rays'][k]['outside']) or bool(p['pane_from_inside'])!=bool(p['glb_pane_rays'][k]['inside']) for p in probes) for k in glb_trees}
 r['near_transparent_decor_layers']=dict(Counter(h['object'] for p in probes for h in p['transparent_decor_layers']))
 r['deep_inside_first_hits']=dict(deepinside);r['deep_outside_first_hits']=dict(deepoutside)
 r['wall_clear_fraction']=round(structclear/len(probes),4) if probes else None
 r['view_center']=list(o+S*((xmin+xmax)/2)+T*((ymin+ymax)/2))
 r['diagnostic']='decorative_opaque_preserved' if r['category']=='decorative_blind' else ('unclassified_near_obstruction' if structclear<len(probes) else ('missing_ruin_pane_open' if r['pane_missing'] else 'transparent_clear_wall'))
 windows.append(r)

# Four modeled spire lucarne masses are not glazed openings: explicitly inventory them instead of silently omitting.
P=json.load(open(root/'params.json'));c=P['cathedral'];tw=c['tower_sw'];xs=tw['x'];ys=tw['y'];x0=xs[0]+.5;x1=xs[1]-.2;y0=ys[0]+.3;y1=ys[1]-.5;cxs=(x0+x1)/2;cys=(y0+y1)/2
ornaments=[]
for k in range(4):
 a=math.pi*k/2;lx=cxs+.62*tw['spire_r']*math.cos(a);ly=cys+.62*tw['spire_r']*math.sin(a)
 ornaments.append(dict(id='Cathedral/decorative_spire_lucarne/'+str(k+1),building_id='Cathedral',category='decorative_spire_lucarne',component='tower_SW_spire',floor='spire',orientation=('E','N','W','S')[k],center=[lx,ly,tw['top']+1.],glass_modeled=False,opening_modeled=False,diagnostic='solid_stone_roof_ornament_not_a_glazed_window',source='build.py upper_tower spire lucarnes: box stone + cone slate; no window definition'))

coverage=dict(expected_generated_faces=sum(len(x['generated_face_hashes']) for x in inv['windows']),matched_unique_hashes=len(actual),missing_generated_face_occurrences=sum(r['unmatched_generated_faces'] for r in windows),unknown_glass_faces=unknown,unmatched_window_slots=[r['id'] for r in windows if not r['pane_missing'] and r['actual_face_count']==0],source_sha256=inv['source_sha256'],blend_sha256=hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest())
glb={}
for filename in ('building.glb','web/building_opt.glb'):
 path=root/filename
 with path.open('rb') as f:
  f.read(12);length,_=struct.unpack('<II',f.read(8));doc=json.loads(f.read(length))
 mats={m['name']:m for m in doc['materials']};counts=Counter()
 for mesh in doc['meshes']:
  for pr in mesh['primitives']:counts[doc['materials'][pr['material']]['name']]+=doc['accessors'][pr['indices']]['count']//3
 glb[filename]=dict(bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),window_materials={k:mats[k] for k in ('Glass','Glass_blind') if k in mats},triangles_by_window_material={k:counts[k] for k in ('Glass','Glass_blind')})
report=dict(schema='gothic.window-audit.v1',scope='LOCAL Blender assets only, not production browser at 8bca20e',coverage=coverage,materials=materials,glb=glb,windows=windows,decorative_spire_ornaments=ornaments)
(dest/'windows_full.json').write_text(json.dumps(report,indent=2))
keys=['id','building_id','category','component','floor','orientation','pane_missing','material_transparent','material_opaque','actual_face_count','probe_count','clear_wall_samples','own_pane_samples','wall_clear_fraction','diagnostic']
with (dest/'windows_full.csv').open('w') as f:
 w=csv.DictWriter(f,keys);w.writeheader();w.writerows({k:r.get(k) for k in keys} for r in windows)
summary={}
for bid in sorted({r['building_id'] for r in windows}):
 a=[r for r in windows if r['building_id']==bid];true=[r for r in a if r['category']!='decorative_blind'];summary[bid]=dict(true_windows=len(true),transparent_glazed=sum(r['material_transparent'] for r in true),opaque_glazed=sum(r['material_opaque'] for r in true),missing_ruin_panes=sum(r['pane_missing'] for r in true),any_structural_occlusion=sum(r['clear_wall_samples']<r['probe_count'] for r in true),fully_structurally_blocked=sum(r['clear_wall_samples']==0 for r in true),decorative_blinds=len(a)-len(true),by_floor_direction={})
 floors=sorted({r['floor'] for r in a})
 for fl in floors:
  summary[bid]['by_floor_direction'][fl]={di:dict(Counter(r['category'] for r in a if r['floor']==fl and r['orientation']==di)) for di in ('N','E','S','W')}
(dest/'summary_initial.json').write_text(json.dumps(summary,indent=2))
print('COVERAGE',coverage);print('SUMMARY',json.dumps(summary));print('WRITTEN',dest/'windows_full.json')
