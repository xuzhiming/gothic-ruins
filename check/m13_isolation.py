"""Blender audit: before/after geometry + material/UV isolation, including shared node trees and textures."""
import bpy, json, os, hashlib, struct
ROOT='/workspace/gothic'
def sig(o):
 me=o.data; h=hashlib.sha256()
 for v in me.vertices: h.update(struct.pack('<3f',*v.co))
 for p in me.polygons: h.update(struct.pack('<%di'%len(p.vertices),*p.vertices))
 h.update(str([list(r) for r in o.matrix_world]).encode())
 return h.hexdigest()
def snap(path):
 bpy.ops.wm.open_mainfile(filepath=path); out={}
 for o in bpy.context.scene.objects:
  if o.type!='MESH': continue
  uv=o.data.uv_layers.active.data
  out[o.name]={'geom':sig(o),'faces':[(o.data.materials[p.material_index].name,[(round(uv[i].uv.x,6),round(uv[i].uv.y,6)) for i in p.loop_indices]) for p in o.data.polygons]}
 return out
A=snap(ROOT+'/tmp/before_m13/building.blend'); B=snap(ROOT+'/building.blend')
assert A.keys()==B.keys(),'objects changed'
changes=json.load(open(ROOT+'/check/m13_face_changes.json'));allowed={(c['object'],c['polygon']) for c in changes['changes']}
changed=[]
for n,a in A.items():
 b=B[n]; assert a['geom']==b['geom'],('geometry changed',n)
 assert len(a['faces'])==len(b['faces'])
 for i,(fa,fb) in enumerate(zip(a['faces'],b['faces'])):
  if fa!=fb:
   assert (n,i) in allowed,('non-target material or UV changed',n,i)
   changed.append((n,i))
assert set(changed)==allowed, ('expected change count',len(changed),len(allowed))
# All source textures byte-identical.
T=ROOT+'/tmp/before_m13/tex'; ts=[]
for f in sorted(os.listdir(T)):
 if not f.endswith('.png'): continue
 assert open(T+'/'+f,'rb').read()==open(ROOT+'/tex/'+f,'rb').read(),('texture changed',f)
 ts.append(f)
assert open(ROOT+'/ruin_log.json','rb').read()==open(ROOT+'/tmp/before_m13/ruin_log.json','rb').read(),'ruin changed'
assert open(ROOT+'/spaces.json','rb').read()==open(ROOT+'/tmp/before_m13/spaces.json','rb').read(),'spaces changed'
R={'PASS':True,'objects_identical':len(A),'geometry':'byte-identical coordinates/topology/transforms','changed_polygons':len(changed),'changed_faces':changes['counts'],'non_target_material_uv_changes':0,'source_textures_identical':len(ts),'spaces_identical':True,'ruin_identical':True}
json.dump(R,open(ROOT+'/check/m13_isolation.json','w'),indent=2);print('M13 ISOLATION',R)
