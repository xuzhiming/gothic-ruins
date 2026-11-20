"""Gap #10: Cycles elevations (warm preset colours, soft frontal light like the flat-lit reference sheets) for wall-texture comparison.
  blender -b building.blend -P src/render_elev.py -- OUTDIR [spp] [mpp]   -> OUTDIR/elev_{south,west,east,north}.png"""
import bpy, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import final_scene as F
argv = sys.argv[sys.argv.index("--") + 1:]; OUT = argv[0]; SPP = int(argv[1]) if len(argv) > 1 else 24; MPP = float(argv[2]) if len(argv) > 2 else 0.08
os.makedirs(OUT, exist_ok=True); sc = bpy.context.scene
for o in sc.objects:
    if o.type == "MESH" and o.get("role") in ("approach", "base"): o.hide_render = True
sun = F.light(sc, engine="CYCLES", fog=False, cam_bg=True); sc.cycles.samples = SPP
cam = bpy.data.objects.new("ElevCam", bpy.data.cameras.new("ElevCam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = "ORTHO"; cam.data.clip_end = 3000; FH = 50.0; D = 600.0
V = {"south": ((0, -D, FH/2 - 2), (math.pi/2, 0, 0), 70.0, 0), "north": ((0, D, FH/2 - 2), (math.pi/2, 0, math.pi), 70.0, 180),
     "west": ((-D, 0, FH/2 - 2), (math.pi/2, 0, -math.pi/2), 110.0, -90), "east": ((D, 0, FH/2 - 2), (math.pi/2, 0, math.pi/2), 110.0, 90)}
for nm, (loc, rot, fw, az) in V.items():
    sc.render.resolution_x = int(round(fw/MPP)); sc.render.resolution_y = int(round(FH/MPP)); cam.location = loc; cam.rotation_euler = rot; cam.data.ortho_scale = max(fw, FH)
    sun.rotation_euler = (math.radians(55), 0, math.radians(az + 25))   # light from the viewer's side, 35 deg up, 25 deg off-axis
    sc.render.filepath = os.path.join(OUT, f"elev_{nm}.png"); bpy.ops.render.render(write_still=True)
print("ELEV OK", OUT)
