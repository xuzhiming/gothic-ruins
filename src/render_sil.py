"""Orthographic renders at a known metric scale (run on building.blend).
   blender -b building.blend -P src/render_sil.py -- OUTDIR [MPP] [--shaded]
Writes sil_<view>.png (alpha = silhouette) for south/north/west/east/top, plus shaded_<view>.png (workbench, textured) and
sil_meta.json describing the exact metric frame of every view (centre u/z, metres per pixel)."""
import bpy, math, os, sys, json
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0] if argv else "sil"; MPP = float(argv[1]) if len(argv) > 1 else 0.1
os.makedirs(OUT, exist_ok=True)
sc = bpy.context.scene
HIDE = ("approach", "base")
for o in sc.objects:
    if o.type == "MESH" and o.get("role") in HIDE: o.hide_render = True
sc.render.engine = "BLENDER_WORKBENCH"; sc.render.film_transparent = True
sh = sc.display.shading
cam = bpy.data.objects.new("OrthoCam", bpy.data.cameras.new("OrthoCam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = "ORTHO"; cam.data.clip_end = 3000; cam.data.clip_start = 0.1
# frames (metres): elevations W x H with ground (z=0) at 2 m above the bottom edge; top view centred at the origin
FW_EW, FW_NS, FH, FT = 70.0, 110.0, 50.0, 112.0
D = 600.0
views = {  # name: (location, rotation, frame_w, frame_h, u-axis description)
    "south": ((0, -D, FH/2 - 2), (math.pi/2, 0, 0), FW_EW, FH),           # u = +X
    "north": ((0, D, FH/2 - 2), (math.pi/2, 0, math.pi), FW_EW, FH),      # u = -X
    "west": ((-D, 0, FH/2 - 2), (math.pi/2, 0, -math.pi/2), FW_NS, FH),   # u = -Y (north on the left)
    "east": ((D, 0, FH/2 - 2), (math.pi/2, 0, math.pi/2), FW_NS, FH),     # u = +Y (south on the left)
    "top": ((0, 0, 400), (0, 0, 0), FT*0.75, FT)}
meta = {"mpp": MPP, "ground_from_bottom_m": 2.0, "views": {}}
shaded = "--shaded" in argv
for nm, (loc, rot, fw, fh) in views.items():
    sc.render.resolution_x = int(round(fw/MPP)); sc.render.resolution_y = int(round(fh/MPP)); sc.render.resolution_percentage = 100
    cam.location = loc; cam.rotation_euler = rot; cam.data.ortho_scale = max(fw, fh)
    sh.light = "FLAT"; sh.color_type = "SINGLE"; sh.single_color = (0, 0, 0); sc.display.shading.show_shadows = False
    sc.render.filepath = os.path.join(OUT, f"sil_{nm}.png"); bpy.ops.render.render(write_still=True)
    if shaded:
        sh.light = "STUDIO"; sh.color_type = "TEXTURE"; sc.display.shading.show_shadows = True; sh.show_cavity = True
        sc.render.filepath = os.path.join(OUT, f"shaded_{nm}.png"); bpy.ops.render.render(write_still=True)
    meta["views"][nm] = {"frame_w": fw, "frame_h": fh, "res": [sc.render.resolution_x, sc.render.resolution_y]}
# building footprint (plan view, buildings only: cathedral + houses) for the plan footprint score
BUILD = ("Cathedral", "CathRoof", "Tracery", "Finials", "CathInterior", "House_")
for o in sc.objects:
    if o.type == "MESH" and not any(o.get("group", "").startswith(b) for b in BUILD) and not o.name.startswith("DoorLeaf_House"): o.hide_render = True
loc, rot, fw, fh = views["top"]
sc.render.resolution_x = int(round(fw/MPP)); sc.render.resolution_y = int(round(fh/MPP)); cam.location = loc; cam.rotation_euler = rot; cam.data.ortho_scale = max(fw, fh)
sh.light = "FLAT"; sh.color_type = "SINGLE"; sh.single_color = (0, 0, 0); sc.display.shading.show_shadows = False
sc.render.filepath = os.path.join(OUT, "sil_foot.png"); bpy.ops.render.render(write_still=True)
json.dump(meta, open(os.path.join(OUT, "sil_meta.json"), "w"), indent=1)
print("SIL OK", OUT)
