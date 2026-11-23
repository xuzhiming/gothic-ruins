"""Saved-scene full-width capsule/floor/guard audit plus real BVH negative fixtures.
blender -b building.blend -P check/test_alley_assets.py -- [report.json]
"""
import bpy,json,sys,math,os
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from alley_layout import alley_routes,guard_boxes
P=json.loads((ROOT/'params.json').read_text());routes=alley_routes(P);S=json.loads((ROOT/'spaces.json').read_text())
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
OUT=Path(args[0]) if args else ROOT/'check/alley_report.json'
def tree(omit=None,block=None):
 vs=[];fs=[];names=[]
 for ob in bpy.context.scene.objects:
  if ob.type!='MESH' or ob.name.startswith('DoorLeaf_') or ob.get('role') in ('decor','glass_never'):continue
  if omit and omit(ob):continue
  n=len(vs);vs.extend(ob.matrix_world@v.co for v in ob.data.vertices)
  for f in ob.data.polygons:fs.append([n+i for i in f.vertices]);names.append(ob.name)
 if block:
  x,y,z=block;n=len(vs)
  vs.extend(Vector((x+a*.35,y+b*.8,z+c*1.1)) for a,b,c in [(-1,-1,0),(-1,1,0),(1,1,0),(1,-1,0),(-1,-1,2),(-1,1,2),(1,1,2),(1,-1,2)])
  for ids in [(0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)]:fs.append([n+i for i in ids]);names.append('NEGATIVE_BLOCK')
 return BVHTree.FromPolygons(vs,fs),names

def ray(T,o,d,L):
 p,n,i,t=T[0].ray_cast(Vector(o),Vector(d),L)
 return (t,T[1][i]) if p is not None else (None,None)

def inspect(T,quick=False):
 failures=[];count=0;min_gap=999.;min_rear=999.;min_head=3.
 for r in [dict(rt,path=[a,b],net_width=rt.get('segment_widths',[rt['net_width']]*(len(rt['path'])-1))[j]) for rt in routes for j,(a,b) in enumerate(zip(rt['path'],rt['path'][1:]))]:
  a,b=map(Vector,(r['path'][0],r['path'][-1]));delta=b-a;length=delta.length;dire=delta.normalized();lat=Vector((-dire.y,dire.x,0));steps=math.ceil(length/.20)
  for i in range(steps+1):
   p=a+delta*i/steps;count+=1
   for off in (-(r['net_width']/2-.005),0.,r['net_width']/2-.005):
    q=p+lat*off;dist,_=ray(T,q+Vector((0,0,.12)),(0,0,-1),.18)
    if dist is None or abs(dist-.12)>.02:failures.append([r['id'],'missing_floor',i,off])
   for off in (-(r['net_width']/2-.30),0.,r['net_width']/2-.30):
    q=p+lat*off
    hd,_=ray(T,q+Vector((0,0,.01)),(0,0,1),3.)
    min_head=min(min_head,hd if hd is not None else 999)
    if hd is not None and hd<2.09:failures.append([r['id'],'headroom',i,off,hd])
    # Capsule is a swept .30m sphere with centerline z=.30..1.30.
    # Nearest-surface checks catch oblique obstacles between radial rays.
    for j in range(11):
     center=q+Vector((0,0,.30+j*.10));near=T[0].find_nearest(center,.301)
     if near[0] is not None and near[3]<.299:
      failures.append([r['id'],'capsule_nearest',i,off,j,T[1][near[2]],round(near[3],5)])
    for h in (.05,.30,.80,1.30,1.60):
     for angle in range(0,360,45):
      d=(math.cos(math.radians(angle)),math.sin(math.radians(angle)),0)
      dist,name=ray(T,q+Vector((0,0,h)),d,.30)
      if dist is not None:failures.append([r['id'],'capsule',i,off,h,name,round(dist,4)])
   if r['kind']=='rear' and -31.5<p.y<29.5:
    for h in (.1,.8,1.6,2.05):
     d1,_=ray(T,p+Vector((0,0,h)),(1,0,0),3.);d2,_=ray(T,p+Vector((0,0,h)),(-1,0,0),3.)
     if d1 is not None and d2 is not None:min_rear=min(min_rear,d1+d2)
   if r['kind']=='alley' and 21<abs(p.x)<30.7:
    for h in (.1,.8,1.6,2.05):
     d1,_=ray(T,p+Vector((0,0,h)),lat,3.);d2,_=ray(T,p+Vector((0,0,h)),-lat,3.)
     if d1 is not None and d2 is not None:
      g=d1+d2;min_gap=min(min_gap,g)
      if g<1.4-1e-4:failures.append([r['id'],'net_width',i,h,g])
   if quick and failures:return dict(PASS=False,fail=failures[:30],samples=count)
 for g in guard_boxes(P):
  name='AlleyGuard_'+g['id'];x0,x1,y0,y1=g['bounds'];long_y=y1-y0>x1-x0;length=(y1-y0 if long_y else x1-x0)
  for i in range(math.ceil(length/.25)+1):
   t=i/math.ceil(length/.25);x=(x0+x1)/2 if long_y else x0+(x1-x0)*t;y=y0+(y1-y0)*t if long_y else (y0+y1)/2
   # Avoid exact mesh corners while preserving end coverage.
   x=min(x1-.002,max(x0+.002,x));y=min(y1-.002,max(y0+.002,y))
   for h in (.15,.55,1.0):
    origin=(x-.5,y,P['site']['plaza_z']+h) if long_y else (x,y-.5,P['site']['plaza_z']+h)
    direction=Vector((1,0,0) if long_y else (0,1,0));travel=0.;found=False;hitname=None
    # At sealed wall/guard overlaps the house face can be the nearest hit.
    # Search all intersections; require the named solid guard itself, not a proxy wall.
    for _ in range(12):
     dist,hitname=ray(T,Vector(origin)+direction*travel,direction,1.-travel)
     if dist is None:break
     if hitname.startswith(name+'_'):found=True;break
     travel+=dist+.0001
     if travel>=1.:break
    if not found:failures.append([g['id'],'missing_guard',i,h,hitname])
 return dict(PASS=not failures,fail=failures[:100],failure_count=len(failures),samples=count,min_alley_structural_width_m=round(min_gap,6),min_rear_structural_width_m=round(min_rear,6),min_headroom_lower_bound_m=round(min_head,4),routes=[r['id'] for r in routes],existing_north_join_test_width_m=.6,new_platform_and_alley_test_width_m=1.4)

T=tree();main=inspect(T)
ids=set(S['spaces']);missing=[r['id'] for r in routes if r['id'] not in ids]
if missing:main['PASS']=False;main['fail'].append(['missing_route_spaces',missing])
wrong=[o.name for o in bpy.context.scene.objects if o.name.startswith('AlleyGuard_') and o.get('role')!='solid']
if wrong:main['PASS']=False;main['fail'].append(['noncolliding_guard',wrong])
negative={}
if main['PASS']:
 del T
 r=routes[0];a,b=map(Vector,(r['path'][0],r['path'][-1]));T=tree(block=(a+b)/2);v=inspect(T,True);negative['blocked_alley']={'caught':not v['PASS'],'evidence':v['fail'][:2]};del T
 T=tree(omit=lambda o:o.name=='Plaza_cobble');v=inspect(T,True);negative['missing_floor']={'caught':not v['PASS'],'evidence':v['fail'][:2]};del T
 T=tree(omit=lambda o:o.name.startswith('AlleyGuard_W_outer'));v=inspect(T);negative['missing_guard']={'caught':not v['PASS'],'evidence':v['fail'][:2]};del T
report=dict(main=main,negative=negative,PASS=main['PASS'] and len(negative)==3 and all(v['caught'] for v in negative.values()))
OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2));assert report['PASS'],'t24u saved-asset audit failed'
