"""M13: face-local material/UV overrides, after geometry generation and before both Blend and GLB export.
No global material edits and no geometry changes. Only the explicitly selected exterior planes can change.
"""
DEFAULT = {'house':'E4', 'eligible':['Brick','Plaster'], 'faces':{
 'south':{'axis':1,'plane':-32.901,'normal':[0,-1,0],'tolerance':0.003},
 'street':{'axis':0,'plane':20.35,'normal':[-1,0,0],'tolerance':0.018}}}
def select(obj_name, material, center, normal, config=None):
    c = config or DEFAULT
    if not obj_name.startswith('House_'+c['house']+'_') or material not in c['eligible']: return None
    for key, f in c['faces'].items():
        if abs(center[f['axis']]-f['plane']) <= f['tolerance'] and sum(a*b for a,b in zip(normal,f['normal'])) > .999:
            return key
    return None

def apply(config, root):
    if not config or not config.get('enabled'): return
    import bpy, json, os
    source=bpy.data.materials[config['source_material']]
    mats={}
    for key,f in config['faces'].items():
        m=source.copy(); m.name=f['material_name']; mats[key]=m
    counts={k:0 for k in mats}; changes=[]
    for obj in bpy.context.scene.objects:
        if obj.type!='MESH' or not obj.name.startswith('House_'+config['house']+'_'): continue
        me=obj.data; uv=me.uv_layers.active.data; idx={}
        for poly in me.polygons:
            old=me.materials[poly.material_index].name
            center=obj.matrix_world@poly.center
            n=(obj.matrix_world.to_3x3()@poly.normal).normalized()
            key=select(obj.name,old,center,n,config)
            if key is None: continue
            if key not in idx:
                idx[key]=len(me.materials); me.materials.append(mats[key])
            poly.material_index=idx[key]; f=config['faces'][key]; size=f['tile_m']; phase=f['phase']
            for li in poly.loop_indices:
                p=obj.matrix_world@me.vertices[me.loops[li].vertex_index].co
                u=p[f['u_axis']]*f['u_sign']/size+phase[0]
                v=p.z/size+phase[1]; uv[li].uv=(u,v)
            counts[key]+=1; changes.append({'object':obj.name,'polygon':poly.index,'face':key,'old':old,'new':mats[key].name})
        me.update()
    assert all(counts.values()), ('empty face override',counts)
    json.dump({'counts':counts,'changes':changes,'config':config},open(os.path.join(root,'check','m13_face_changes.json'),'w'),indent=1)
    print('M13 FACE OVERRIDES',counts)
