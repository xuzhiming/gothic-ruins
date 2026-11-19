"""Beauty render from the isometric reference angle (Cycles, CPU) + optional workbench preview.
   blender -b building.blend -P src/render_beauty.py -- OUT.png [samples] [res_x] [--workbench] [--az DEG --el DEG]"""
import bpy, math, os, sys
from mathutils import Vector
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0]; SAMPLES = int(argv[1]) if len(argv) > 1 else 96; RX = int(argv[2]) if len(argv) > 2 else 1200
def opt(k, d): return float(argv[argv.index(k) + 1]) if k in argv else d
AZ, EL = math.radians(opt("--az", -22.0)), math.radians(opt("--el", 42.0))
sc = bpy.context.scene
import json   # warm preset (gap #8) lives in compare/mat/warm_light.json so the beauty render and the three.js preview share it
WARM = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "compare", "mat", "warm_light.json")))
for o in sc.objects:
    if o.type == "MESH" and o.get("role") == "approach": o.hide_render = False
tgt = Vector((opt("--tx", 0.0), opt("--ty", -2.0), opt("--tz", 8.0)))
d = Vector((math.sin(AZ)*math.cos(EL), -math.cos(AZ)*math.cos(EL), math.sin(EL)))
cam = bpy.data.objects.new("IsoCam", bpy.data.cameras.new("IsoCam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = "ORTHO"; cam.data.ortho_scale = opt("--scale", 118.0); cam.data.clip_end = 3000; cam.data.clip_start = opt("--clip0", 0.1)
cam.location = tgt + d*400; cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
if "--cam" in argv:   # perspective street-level camera: --cam x,y,z --look x,y,z [--lens mm]
    cp = Vector([float(t) for t in argv[argv.index("--cam") + 1].split(",")]); lk = Vector([float(t) for t in argv[argv.index("--look") + 1].split(",")])
    cam.data.type = "PERSP"; cam.data.lens = opt("--lens", 24.0); cam.data.clip_start = 0.1
    cam.location = cp; cam.rotation_euler = (lk - cp).to_track_quat("-Z", "Y").to_euler()
sc.render.resolution_x = RX; sc.render.resolution_y = int(RX*opt("--aspect", 960/808)); sc.render.resolution_percentage = 100
if "--workbench" in argv:
    sc.render.engine = "BLENDER_WORKBENCH"; sh = sc.display.shading; sh.light = "STUDIO"; sh.color_type = "TEXTURE"; sc.display.shading.show_shadows = True; sh.show_cavity = True
else:
    sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = SAMPLES; sc.cycles.use_denoising = True
    sc.view_settings.view_transform = "AgX"; sc.view_settings.look = "AgX - Medium High Contrast" if False else "None"
    w = bpy.data.worlds.new("Sky"); sc.world = w; w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN")); sc.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(50), 0, math.radians(-35))
    def rgb(k, d): return tuple(float(t) for t in argv[argv.index(k) + 1].split(",")) + (1,) if k in argv else d
    if "--warm" in argv:   # gap #8: warm soft overcast matched to ref/isometric.png (compare/mat/beauty_compare.py, compare_log M8)
        bg.inputs[0].default_value = rgb("--skyrgb", WARM["sky"]); bg.inputs[1].default_value = opt("--sky", WARM["sky_strength"])
        sun.data.energy = opt("--sun", WARM["sun"]); sun.data.angle = math.radians(opt("--angle", WARM["angle"])); sun.data.color = rgb("--sunrgb", WARM["sun_rgb"])[:3]
        sc.view_settings.look = argv[argv.index("--agxlook") + 1] if "--agxlook" in argv else WARM["look"]; sc.view_settings.exposure = opt("--exposure", WARM["exposure"])
        if WARM.get("camera_bg"):   # what the camera sees directly = warm paper backdrop like the reference (does not light the scene)
            nt = w.node_tree; lp = nt.nodes.new("ShaderNodeLightPath"); b2 = nt.nodes.new("ShaderNodeBackground"); mx = nt.nodes.new("ShaderNodeMixShader")
            b2.inputs[0].default_value = tuple(WARM["camera_bg"]) + (1,); b2.inputs[1].default_value = 1.0; out = nt.nodes["World Output"]
            nt.links.new(lp.outputs["Is Camera Ray"], mx.inputs[0]); nt.links.new(bg.outputs[0], mx.inputs[1]); nt.links.new(b2.outputs[0], mx.inputs[2]); nt.links.new(mx.outputs[0], out.inputs["Surface"])
    elif "--mood" in argv:   # ruin atmosphere: overcast sky does most of the lighting, weak soft cool sun, contrasty AgX look
        bg.inputs[0].default_value = (0.47, 0.5, 0.55, 1); bg.inputs[1].default_value = opt("--sky", 1.5)
        sun.data.energy = opt("--sun", 1.0); sun.data.angle = math.radians(28); sun.data.color = (0.9, 0.94, 1.0)
        sc.view_settings.look = "AgX - Medium High Contrast"; sc.view_settings.exposure = opt("--exposure", 0.0)
    else:
        bg.inputs[0].default_value = (0.86, 0.85, 0.83, 1); bg.inputs[1].default_value = 0.9
        sun.data.energy = 3.2; sun.data.angle = math.radians(3)
    if opt("--fog", 0.0) > 0:   # light fog: a volume box around the site only (camera outside it for the ortho views)
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, 30)); fb = bpy.context.active_object; fb.name = "FogVolume"; fb.scale = (150, 150, 64)
        fm = bpy.data.materials.new("Fog"); fm.use_nodes = True; nt = fm.node_tree; nt.nodes.remove(nt.nodes["Principled BSDF"])
        pv = nt.nodes.new("ShaderNodeVolumePrincipled"); pv.inputs["Density"].default_value = opt("--fog", 0.0)
        pv.inputs["Color"].default_value = rgb("--fogrgb", WARM["fog_rgb"] if "--warm" in argv else (0.8, 0.82, 0.86, 1)); pv.inputs["Anisotropy"].default_value = 0.35
        nt.links.new(pv.outputs[0], nt.nodes["Material Output"].inputs["Volume"]); fb.data.materials.append(fm)
        sc.cycles.volume_step_rate = 4.0; sc.cycles.volume_max_steps = 256
    sc.render.film_transparent = False
sc.render.filepath = OUT; bpy.ops.render.render(write_still=True); print("BEAUTY OK", OUT)
