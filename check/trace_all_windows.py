"""Enumerate every generator window, without editing production assets.
Blender -b -P check/trace_all_windows.py -- TRACE_ROOT OUTPUT_JSON
"""
import bpy,sys,os,json,runpy,hashlib,math
from collections import defaultdict
from mathutils import Vector
args=sys.argv[sys.argv.index('--')+1:]; root=os.path.abspath(args[0]); dest=args[1]
sys.path.insert(0,root+'/src'); os.environ['OUTDIR']=root;os.environ['NO_EXPORT']='1'
records=[]; current={}; extrudes={}; counter=defaultdict(int); rose=None
wallfile=root+'/src/geom.py'; buildfile=root+'/build.py'
wall_glass_line=next(i for i,s in enumerate(open(wallfile),1) if 'if q.get("glass") and glass is not None:' in s)
def stack_house(f):
 while f:
  if f.f_code.co_name=='house': return f.f_locals
  f=f.f_back
 return None
def orientation(n):
 return ('E' if n.x>0 else 'W') if abs(n.x)>abs(n.y) else ('N' if n.y>0 else 'S')
def new(bid,category,component,floor,origin,along,n,poly,wall_t,missing,source):
 key=(bid,category,component,floor,orientation(n));counter[key]+=1
 rec=dict(azimuth_deg=round(math.degrees(math.atan2(n.y,n.x))%360,4),id='/'.join(map(str,key))+'/'+str(counter[key]),building_id=bid,category=category,component=component,floor=floor,orientation=orientation(n),normal=list(n),origin=list(origin),along=list(along),polygon=poly,wall_thickness=wall_t,pane_missing=missing,source=source,generated_face_hashes=[],pane_parts=[])
 records.append(rec);return rec
def polyhash(pts):
 return hashlib.sha256(json.dumps(sorted(tuple(round(float(x),5) for x in p) for p in pts)).encode()).hexdigest()
def make_wall(f):
 l=f.f_locals; q=l['q']; S=l['S'];T=l['T'];N=l['Nw'];o=l['o']; hh=stack_house(f.f_back);call=f.f_back.f_lineno
 if hh:
  bid=hh['hid'];category='main';floor='F'+str(hh['f'])
  out=Vector(l['outdir'])
  component='street' if out.dot(hh['fr'].dir(-1,0))>.99 else ('rear' if out.dot(hh['fr'].dir(1,0))>.99 else 'end')
  if l['outdir'] is not None:
   out=Vector((*l['outdir'][:2],0));N=N if N.dot(out)>0 else -N
 else:
  bid='Cathedral';category='lancet';floor='aisle';component='other'
  anc=f.f_back
  while anc and anc.f_code.co_name!='tower_walls': anc=anc.f_back
  if anc:
   a=anc.f_locals;center=Vector(((a['x0']+a['x1'])/2,(a['y0']+a['y1'])/2,0))
   loc=o+S*q['s'];out=loc-center;out.z=0;N=N if N.dot(out)>0 else -N
   upper=anc.f_back.f_locals
   component=('tower_SW' if center.x<0 else 'tower_SE')+('_belfry' if abs(a['z0']-upper['zb'])<.001 else '_stage')
   floor='tier_'+str(a['t']+1)
  else:
   line=open(buildfile).readlines()[call-1]
   if 'opsU' in line: component='nave_clerestory';floor='clerestory'
   elif 'opsA' in line: component='aisle_side'
   elif 'AL[' in line: component='tower_base_front';floor='tower_base'
   elif '[lancet(abs' in line: component='aisle_north'
   elif 'sg*ra' in line: component='ambulatory_straight'
   elif 'p0, p1' in line: component='ambulatory_apse'
   elif 'q0, q1' in line: component='apse_clerestory';floor='clerestory'
   else: component='source_line_'+str(call)
   c=o+S*q['s']; out=Vector((c.x,c.y-38 if 'apse' in component or 'ambulatory' in component else 0,0));N=N if N.dot(out)>=0 else -N
 if not hh and component=='tower_base_front':N=Vector((0,-1,0))
 if not hh and component=='aisle_north':N=Vector((0,1,0))
 a,b=q['s']-q['w']/2,q['s']+q['w']/2;kind=q.get('kind','pointed');k=q.get('k',1.);sill=q.get('sill',0);top=min(q['h'],l['H']);spring=top-f.f_globals['arch_rise'](b-a,kind,k)
 poly=[(a,sill),(b,sill)]+([(b,spring),(a,spring)] if kind=='flat' else list(reversed(f.f_globals['arch_curve'](a,b,spring,kind,k))))
 rec=new(bid,category,component,floor,o,S,N,poly,l['t'],bool(l['lost']),{'function':'wall','line':call,'kind':kind,'spec':dict(q)})
 current[id(f)]=(rec,l['glass']); return rec

def trace(f,event,arg):
 global rose
 name=f.f_code.co_name;file=f.f_code.co_filename
 if event=='call':
  if file==wallfile and name=='wall': return trace
  if file==wallfile and name=='cross_panel':
   l=f.f_locals;hh=stack_house(f);caller=f.f_back;cat='dormer' if caller.f_code.co_name=='dormer' else 'attic'
   comp='dormer' if cat=='dormer' else ('end_gable' if 'vv' in open(buildfile).readlines()[caller.f_lineno-1] else 'street_gable')
   S=Vector(l['Sd']).normalized();N=Vector(l['outd']).normalized();o=Vector((l['c0'].x,l['c0'].y,0));w=l['w'];z0,z1=l['z0'],l['z1']
   rec=new(hh['hid'],cat,comp,'attic',o,S,N,[(0,z0),(w,z0),(w,z1),(0,z1)],.3,False,{'function':'cross_panel','line':caller.f_lineno})
   current[id(f)]=(rec,l['gb']);return trace
  if file==wallfile and name=='relief_arch':
   l=f.f_locals
   if l['bk'].group!='GlassBlind':return None
   # Blind panels are explicitly counted but never candidates for wall removal.
   p0=Vector((*l['p0'],0));p1=Vector((*l['p1'],0));S=(p1-p0).normalized();N=Vector((0,-1,0));a,b=l['s']-l['w']/2,l['s']+l['w']/2
   rise=f.f_globals['arch_rise'](l['w'],l.get('kind','pointed'),l.get('k',1.));spring=l['z_apex']-rise
   poly=[(a,l['z_sill']),(b,l['z_sill'])]+list(reversed(f.f_globals['arch_curve'](a,b,spring,l.get('kind','pointed'),l.get('k',1.))))
   rec=new('Cathedral','decorative_blind','tympanum' if abs(l['s']-(p1-p0).length/2)<.01 else 'blind_lancet','facade',p0,S,N,poly,1.,False,{'function':'relief_arch','line':f.f_back.f_lineno})
   current[id(f)]=(rec,l['bk']);return trace
  if file==wallfile and name=='extrude':
   l=f.f_locals;bk=l['bk'];parent=f.f_back;entry=current.get(id(parent))
   if entry and bk is entry[1]:
    extrudes[id(f)]=(entry[0],bk,len(bk.f),None);return trace
   if parent.f_code.co_filename==buildfile and bk.group=='Glass' and 'rz' in parent.f_locals and 'lostw' in parent.f_locals:
    a=parent.f_locals
    if rose is None:
     rr=a['rr'];rz=a['rz'];rose=new('Cathedral','rose','facade_rose','upper_facade',Vector((0,a['yF'],0)),Vector((1,0,0)),Vector((0,-1,0)),[(rr*math.cos(2*math.pi*k/96),rz+rr*math.sin(2*math.pi*k/96)) for k in range(96)],a['wt'],False,{'function':'rose_wedges','line':parent.f_lineno})
    part={'side':a['side'],'wedge':a['k'],'missing':False}
    rose['pane_parts'].append(part);extrudes[id(f)]=(rose,bk,len(bk.f),part);return trace
   return None
  return None
 if event=='line' and file==wallfile and name=='wall' and f.f_lineno==wall_glass_line:
  if f.f_locals['q'].get('glass') and f.f_locals['glass'] is not None:make_wall(f)
 if event=='return':
  if id(f) in extrudes:
   rec,bk,start,part=extrudes.pop(id(f));hs=[polyhash([bk.v[i] for i in face]) for face in bk.f[start:]];rec['generated_face_hashes'].extend(hs)
   if part is not None:part['face_hashes']=hs
  current.pop(id(f),None)
 return trace
sys.settrace(trace)
try: runpy.run_path(buildfile,run_name='__main__')
finally:sys.settrace(None)
if rose:
 found={(p['side'],p['wedge']) for p in rose['pane_parts']}
 for side in (-1,1):
  for wedge in range(12):
   if (side,wedge) not in found:rose['pane_parts'].append({'side':side,'wedge':wedge,'missing':True,'face_hashes':[]})
for rec in records:
 rec['generated_polygon_count']=len(rec['generated_face_hashes'])
json.dump({'source_sha256':hashlib.sha256(open(buildfile,'rb').read()).hexdigest(),'windows':records,'count':len(records)},open(dest,'w'),indent=2)
print('FULL_WINDOW_TRACE',len(records),dest)
