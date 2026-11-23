"""Compare saved material recipes and isolated geometry against backed-up Blend."""
import bpy,json,sys,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
import face_materials
baseline=Path(sys.argv[sys.argv.index('--')+1]);current=Path(bpy.data.filepath)
def snapshot():
 mats={}
 for m in bpy.data.materials:
  nodes=[]
  if m.use_nodes:
   for n in m.node_tree.nodes:
    inputs={}
    for i in n.inputs:
     if not hasattr(i,'default_value'):continue
     v=i.default_value
     if isinstance(v,(str,int,float,bool)):inputs[i.name]=v
     elif hasattr(v,'__len__'):inputs[i.name]=list(v)
    nodes.append(dict(name=n.name,type=n.type,inputs=inputs,image=n.image.name if n.type=='TEX_IMAGE' and n.image else None))
  mats[m.name]=dict(nodes=nodes,surface=m.surface_render_method)
 geo={}
 for o in bpy.context.scene.objects:
  if o.type=='MESH' and (o.name.startswith(('Cathedral_','CathRoof_','CathInterior_','Tracery_','Finials_','House_NW_','House_NE_'))):
   data=[[[round(float(c),6) for c in v.co] for v in o.data.vertices],[list(f.vertices) for f in o.data.polygons]]
   geo[o.name]=hashlib.sha256(json.dumps(data).encode()).hexdigest()
 return mats,geo
newmat,newgeo=snapshot();P=json.loads((ROOT/'params.json').read_text());C=P['houses']['face_material_overrides'];counts={k:0 for k in C['faces']};errors=[]
for ob in bpy.context.scene.objects:
 if ob.type!='MESH':continue
 for f in ob.data.polygons:
  name=ob.data.materials[f.material_index].name
  key=next((k for k,s in C['faces'].items() if s['material_name']==name),None)
  if key is None and face_materials.select(ob.name,name,ob.matrix_world@f.center,(ob.matrix_world.to_3x3()@f.normal).normalized(),C):
   errors.append([ob.name,f.index,'eligible face missing M13 binding'])
  if key:
   spec=C['faces'][key];c=ob.matrix_world@f.center;n=(ob.matrix_world.to_3x3()@f.normal).normalized()
   if face_materials.select(ob.name,'Brick',c,n,C)!=key:errors.append([ob.name,f.index,'wrong M13 plane'])
   for li in f.loop_indices:
    p=ob.matrix_world@ob.data.vertices[ob.data.loops[li].vertex_index].co
    expected=(p[spec['u_axis']]*spec['u_sign']/spec['tile_m']+spec['phase'][0],p.z/spec['tile_m']+spec['phase'][1])
    actual=ob.data.uv_layers.active.data[li].uv
    if max(abs(actual[i]-expected[i]) for i in (0,1))>1e-5:errors.append([ob.name,f.index,'M13 UV phase drift'])
   counts[key]+=1
assert all(counts.values()),counts
bpy.ops.wm.open_mainfile(filepath=str(baseline));oldmat,oldgeo=snapshot()
changedmat=[k for k,v in oldmat.items() if newmat.get(k)!=v];changedgeo=[k for k,v in oldgeo.items() if newgeo.get(k)!=v]
oldP=json.loads((baseline.parent/'params.json').read_text());preserved={k:P['houses'][k]==oldP['houses'][k] for k in ['windows','plaster','face_material_overrides'] if k in P['houses']}
# M12 coat values live in plaster_layer, preserve every untouched configuration key too.
for k in P['houses']:
 if k not in ('list','alleys','window_damage'):preserved[k]=P['houses'][k]==oldP['houses'][k]
report=dict(PASS=not errors and not changedmat and not changedgeo and all(preserved.values()),M13_face_counts=counts,M13_errors=errors,changed_material_recipes=changedmat,changed_isolated_meshes=changedgeo,isolated_mesh_count=len(oldgeo),preserved_house_settings=preserved)
(ROOT/'t24u-evidence/material_preservation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2));assert report['PASS'],report
