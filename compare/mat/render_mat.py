"""Material-comparison renders at the reference isometric angle (same camera as the beauty iso: az 22, el 50, ortho 118 m).
  blender -b building.blend -P compare/mat/render_mat.py -- OUTDIR [RX] [SAMPLES]
writes OUTDIR/neutral.png (Cycles, NEUTRAL light: pure white uniform sky 0.9 + white sun 3.2, AgX base look, no fog, exposure 0 -
fixed, never tuned; white so the fitted albedo hue is not biased by a tinted illuminant) and OUTDIR/matid.png (Workbench flat, no AA, one exact colour per material category; see CATS)."""
import bpy, sys, os, math
from mathutils import Vector
argv = sys.argv[sys.argv.index("--") + 1:]; OUT = argv[0]; RX = int(argv[1]) if len(argv) > 1 else 1000; SPP = int(argv[2]) if len(argv) > 2 else 48
os.makedirs(OUT, exist_ok=True); sc = bpy.context.scene
if os.environ.get("TEXDIR"):   # render the same blend with another texture set (before / after)
    for im in bpy.data.images:
        p = os.path.join(os.path.abspath(os.environ["TEXDIR"]), os.path.basename(im.filepath))
        if im.filepath and os.path.exists(p): im.filepath = p; im.reload()
CATS = {  # category -> (id colour, rule(group, material))
 "stone_cathedral": ((255, 0, 0), lambda g, m: g in ("Cathedral", "Tracery") and m.startswith("Stone")),
 "slate": ((0, 0, 255), lambda g, m: m == "Slate" and (g == "CathRoof" or g.startswith("House_"))),
 "plaster": ((255, 255, 0), lambda g, m: m.startswith("Plaster")),
 "brick": ((255, 0, 255), lambda g, m: m in ("Brick", "Brick_bare") and g.startswith("House_")),   # gap #12: + brick behind the plaster skin
 "timber": ((0, 255, 0), lambda g, m: m == "Timber" and (g.startswith("House_") or g == "?")),
 "stone_plinth": ((0, 255, 255), lambda g, m: g in ("Balustrade", "Plinth")),
 "plinth_rock": ((128, 64, 0), lambda g, m: g == "Base"),
 "cobble": ((128, 128, 128), lambda g, m: g == "Plaza" and m == "Cobble"),
 "stair": ((255, 128, 0), lambda g, m: g == "Stairs"),
 "chimney": ((128, 0, 0), lambda g, m: g == "Chimneys" and m.startswith("Brick")),
 "iron": ((0, 0, 128), lambda g, m: g in ("Iron", "?") and m == "Iron"),
}
for o in sc.objects:
    if o.type == "MESH" and o.get("role") == "approach": o.hide_render = False
AZ, EL = math.radians(22), math.radians(50); tgt = Vector((0.0, -2.0, 8.0))
d = Vector((math.sin(AZ)*math.cos(EL), -math.cos(AZ)*math.cos(EL), math.sin(EL)))
cam = bpy.data.objects.new("IsoCam", bpy.data.cameras.new("IsoCam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = "ORTHO"; cam.data.ortho_scale = 118.0; cam.data.clip_end = 3000
cam.location = tgt + d*400; cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
sc.render.resolution_x = RX; sc.render.resolution_y = int(RX*960/808); sc.render.resolution_percentage = 100
# 1) neutral Cycles render
sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = SPP; sc.cycles.use_denoising = True
sc.view_settings.view_transform = "AgX"; sc.view_settings.look = "None"; sc.view_settings.exposure = 0.0
w = bpy.data.worlds.new("Sky"); sc.world = w; w.use_nodes = True; bg = w.node_tree.nodes["Background"]
bg.inputs[0].default_value = (0.85, 0.85, 0.85, 1); bg.inputs[1].default_value = 0.9
sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN")); sc.collection.objects.link(sun)
sun.rotation_euler = (math.radians(50), 0, math.radians(-35)); sun.data.energy = 3.2; sun.data.angle = math.radians(3)
sc.render.filepath = os.path.join(OUT, "neutral.png"); bpy.ops.render.render(write_still=True)
# 2) material-category id render (flat colours, no anti-aliasing)
sc.render.engine = "BLENDER_WORKBENCH"; sc.display.render_aa = "OFF"; sh = sc.display.shading
sh.light = "FLAT"; sh.color_type = "OBJECT"; sh.show_shadows = False; sh.show_cavity = False; sh.show_object_outline = False
sh.background_type = "VIEWPORT"; sh.background_color = (1, 1, 1)
sc.view_settings.view_transform = "Standard"; sc.view_settings.look = "None"
lin = lambda c: ((c/255) ** 2.2)
for o in sc.objects:
    if o.type != "MESH": continue
    g = o.get("group", "?") if o.get("role") != "door_leaf_mesh" else "?"; m = o.data.materials[0].name if o.data.materials else ""
    c = (20, 20, 20)
    for k, (cc, rule) in CATS.items():
        if rule(g, m): c = cc; break
    o.color = (c[0]/255, c[1]/255, c[2]/255, 1.0)
sc.render.image_settings.color_management = "OVERRIDE" if hasattr(sc.render.image_settings, "color_management") else None
sc.render.filepath = os.path.join(OUT, "matid.png"); bpy.ops.render.render(write_still=True); print("MAT RENDERS OK", OUT)
