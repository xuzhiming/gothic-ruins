import bpy,sys,hashlib,json,struct
from pathlib import Path
args=sys.argv[sys.argv.index('--')+1:]
def snapshot(path):
 bpy.ops.wm.open_mainfile(filepath=path);out={}
 for o in bpy.context.scene.objects:
  if o.type!='MESH':continue
  m=o.data;h=hashlib.sha256()
  for v in m.vertices:h.update(struct.pack('<3f',*v.co))
  for p in m.polygons:h.update(struct.pack('<I',len(p.vertices)));h.update(struct.pack('<'+'I'*len(p.vertices),*p.vertices));h.update(struct.pack('<I',p.material_index))
  for l in m.uv_layers:
   for u in l.data:h.update(struct.pack('<2f',*u.uv))
  h.update(json.dumps([ma.name for ma in m.materials]).encode());out[o.name]=dict(sha256=h.hexdigest(),polygons=len(m.polygons))
 return out
before=snapshot(args[0]);after=snapshot(args[1]);changed={k:dict(before=before.get(k),after=after.get(k)) for k in set(before)|set(after) if before.get(k)!=after.get(k)}
Path(args[2]).write_text(json.dumps(dict(changed=changed,unchanged=len(set(before)&set(after))-len(changed),before_objects=len(before),after_objects=len(after)),indent=2));print('IDENTITY_CHANGED',json.dumps(changed))
