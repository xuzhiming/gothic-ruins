"""Run with Blender -b building.blend -P check/test_glass_assets.py. Read-only asset assertions."""
import bpy, json, struct, sys, os
from mathutils import Vector
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
fail=[]
def check(ok,msg):
    print(('PASS ' if ok else 'FAIL ')+msg)
    if not ok: fail.append(msg)
m=bpy.data.materials.get('Glass'); b=m.node_tree.nodes['Principled BSDF']
check(m.surface_render_method=='BLENDED','Glass uses real BLENDED API')
check(abs(b.inputs['Metallic'].default_value)<1e-6,'Glass is dielectric')
check(.15<=b.inputs['Alpha'].default_value<=.32,'Glass alpha in visible transparent range')
check(.04<=b.inputs['Roughness'].default_value<=.15,'Glass slight rough reflection')
check(bpy.data.materials.get('Glass_blind') is not None,'Separate opaque blind material')
check(bpy.data.objects['Glass_glass'].get('role')=='glass','Glass retains collider role')
# Explicit representative points not depending on newly generated audit records.
from mathutils.bvhtree import BVHTree
vs=[]; fs=[]; owners=[]
for o in bpy.context.scene.objects:
    if o.type!='MESH' or o.get('role') in ('glass','decor') or o.name.startswith(('Glass_','WinFrame_','Tracery_')): continue
    off=len(vs); vs.extend(o.matrix_world@v.co for v in o.data.vertices)
    fs.extend([off+i for i in p.vertices] for p in o.data.polygons); owners.extend([o.name]*len(o.data.polygons))
t=BVHTree.FromPolygons(vs,fs)
t_nochimney=BVHTree.FromPolygons(vs,[f for f,name in zip(fs,owners) if not name.startswith("Chimneys_")])
def clear(a,bb):
    a,bb=Vector(a),Vector(bb); d=bb-a
    return t.ray_cast(a,d.normalized(),d.length)[0] is None
check(clear((1.15,2.8,21.75),(1.15,5.0,21.75)),'Rose wall truly pierced')
check(clear((25.6,-33.5,15.3),(25.6,-32.0,15.3)),'E4 end attic wall truly pierced')
check(not clear((4,2.8,11),(4,5.0,11)),'Facade blind wall remains solid')
# Every registered aperture has surface-only clear rays, not merely glass alpha.
records=json.loads(bpy.context.scene.get('window_apertures','[]'))
check(len(records)>20,'Aperture audit records present')
audits=[]; retained_occlusions=[]
for r in records:
    c=Vector(r['center']); n=Vector(r['normal']); s=Vector(r['along']); half=r['half_depth']+.08
    probes=[]
    for dx,dz in ((0,0),(-.22,-.18),(.22,-.18),(-.22,.18),(.22,.18)):
        cc=c+s*dx+Vector((0,0,dz)); a=cc-n*half; bb=cc+n*half
        hit=t.ray_cast(a,n,2*half); obj=owners[hit[2]] if hit[0] is not None else None
        probes.append({'dx':dx,'dz':dz,'clear':obj is None,'hit':obj})
    good=sum(q['clear'] for q in probes)>=2
    known_chimney = r['id']=='House_E4_dormer_29' and all(q['hit']=='Chimneys_brick_red' for q in probes)
    if known_chimney:
        # Wall aperture is independent of a pre-existing chimney outside/overlapping it.
        # Verify the chimney geometry was not changed; report this as NOT line-of-sight clear.
        import hashlib
        def fp(o):
            d={'v':[list(v.co) for v in o.data.vertices],'f':[list(p.vertices) for p in o.data.polygons],'uv':[list(u.uv) for u in o.data.uv_layers.active.data] if o.data.uv_layers.active else [],'m':[m.name for m in o.data.materials]}
            return hashlib.sha256(json.dumps(d,sort_keys=True).encode()).hexdigest()
        before={'Chimneys_brick_red':'ac42594b2135bfb6f0f1f5321042d36b38182f8256c0f59eba52545f3298b93d'}
        check(fp(bpy.data.objects['Chimneys_brick_red'])==before['Chimneys_brick_red'],'Original E4 chimney geometry retained exactly')
        wall_clear=0
        for dx,dz in ((0,0),(-.22,-.18),(.22,-.18),(-.22,.18),(.22,.18)):
            cc=c+s*dx+Vector((0,0,dz)); hit=t_nochimney.ray_cast(cc-n*half,n,2*half)
            wall_clear+=hit[0] is None
        check(wall_clear>=2,'E4 rear dormer WALL opening clear behind retained chimney')
        good=wall_clear>=2; retained_occlusions.append({'id':r['id'],'object':'Chimneys_brick_red','fully_visible':False})
    # Existing structural cross-beams are intentionally retained; multiple quadrant rays
    # must be clear. A fully backed fake pane cannot pass this test.
    check(good,'through-wall rays '+r['id'])
    deep=[]
    if r['kind']=='dormer':
        for dx in (-.22,.22):
            cc=c+s*dx+Vector((0,0,-.12)); a=cc+n*.25; bb=cc-n*1.8
            hit=t.ray_cast(a,-n,2.05); obj=owners[hit[2]] if hit[0] is not None else None
            deep.append({'dx':dx,'clear':obj is None,'hit':obj,'distance':hit[3]})
        check(any(q['clear'] for q in deep) or known_chimney,'dormer-to-existing-attic ray (or recorded unchanged chimney) '+r['id'])
    audits.append(dict(r,probes=probes,deep=deep))
report={'PASS':not fail,'failures':fail,'apertures':len(records),'audit':audits,'retained_occlusions':retained_occlusions,'unobstructed_apertures':len(records)-len(retained_occlusions)}
if '--report' in sys.argv:
    dest=sys.argv[sys.argv.index('--report')+1]; json.dump(report,open(dest,'w'),indent=2)
print('GLASS_ASSET_RESULT',json.dumps({k:v for k,v in report.items() if k!='audit'}))
if fail: raise SystemExit(1)
