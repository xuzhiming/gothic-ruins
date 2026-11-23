import bpy,sys,json
from pathlib import Path
from mathutils import Vector
root=Path('/workspace/gothic');sys.path.insert(0,str(root/'src'));import final_scene as F
args=sys.argv[sys.argv.index('--')+1:];phase=args[0];x=json.load(open(root/'window-audit/before/windows_full.json'));W={r['id']:r for r in x['windows']}
shots={}
for name,key in [('nw_dormer','NW/dormer/dormer/attic/S/1'),('e2_chimney','E2/dormer/dormer/attic/E/1'),('w1_sagged_eave','W1/main/rear/F2/W/2'),('ne_rubble','NE/main/end/F0/E/1'),('tower_shared_wall','Cathedral/lancet/tower_SE_stage/tier_1/W/1')]:
 r=W[key];c=Vector(r['view_center']);n=Vector(r['normal']);s=Vector(r['along']);shots[name+'_out']=(c+n*2.3+s*.08,c-n*.7)
 if name=='nw_dormer':shots[name+'_in']=(c-n*1.2+s*.08,c+n*1.5)
shots['rose_out']=((1.1,-3.3,21.6),(0,7,21.1));shots['rose_in']=((1.1,11.3,21.6),(0,1,21.1))
sc=bpy.context.scene;F.light(sc,'warm','CYCLES',fog=False);sc.cycles.samples=16;sc.cycles.use_denoising=True;sc.cycles.transparent_max_bounces=24;sc.render.resolution_x=640;sc.render.resolution_y=480;sc.render.resolution_percentage=100;sc.render.image_settings.file_format='PNG'
for name,(loc,tgt) in shots.items():
 if phase=='after' and not name.startswith(('nw_dormer','rose')):continue
 cam=F.camera(sc,loc,tgt,lens=35);sc.render.filepath=str(root/'window-audit'/f'{phase}_{name}.png');bpy.ops.render.render(write_still=True);bpy.data.objects.remove(cam,do_unlink=True);print('WINDOW_RENDER',phase,name,flush=True)
