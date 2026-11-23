import bpy,json,hashlib,sys
from pathlib import Path
args=sys.argv[sys.argv.index('--')+1:]; dest=args[0]
def fingerprint(o):
 d={'v':[list(v.co) for v in o.data.vertices],'f':[list(p.vertices) for p in o.data.polygons],'uv':[list(u.uv) for u in o.data.uv_layers.active.data] if o.data.uv_layers.active else [],'m':[m.name for m in o.data.materials]}
 return hashlib.sha256(json.dumps(d,sort_keys=True).encode()).hexdigest()
obj={o.name:fingerprint(o) for o in bpy.data.objects if o.type=='MESH'}
glass=[]
for o in bpy.data.objects:
 if o.type=='MESH' and o.name.startswith(('Glass_glass','GlassBlind_')):
  uv=o.data.uv_layers.active.data
  for p in o.data.polygons:
   poly=[(list(o.data.vertices[o.data.loops[i].vertex_index].co),list(uv[i].uv)) for i in p.loop_indices]
   glass.append(json.dumps(poly))
protected=[]
for o in bpy.data.objects:
 if o.type!='MESH' or not o.name.startswith('House_E4_') or 'slate' in o.name: continue
 uv=o.data.uv_layers.active.data
 for p in o.data.polygons:
  if max(o.data.vertices[i].co.z for i in p.vertices)>14.1001: continue
  poly=sorted((list(o.data.vertices[o.data.loops[i].vertex_index].co),list(uv[i].uv)) for i in p.loop_indices)
  protected.append(json.dumps((o.name,o.data.materials[p.material_index].name,poly)))
obj['__E4_mainstoreys_geometry_material_uv__']=hashlib.sha256(''.join(sorted(protected)).encode()).hexdigest()
obj['__all_glazing_and_blind_geometry_uv__']=hashlib.sha256(''.join(sorted(glass)).encode()).hexdigest()
Path(dest).write_text(json.dumps(obj,indent=2))
print('FINGERPRINTS',len(obj),dest)
