"""Shared scene setup for the final stills / videos (render_final.py): warm light preset (compare/mat/warm_light.json, same as the
approved beauty render), optional golden-hour variant, Cycles (stills) or Eevee (video) settings tuned to look alike."""
import bpy, math, os, json
from mathutils import Vector
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WARM = json.load(open(os.path.join(ROOT, "compare", "mat", "warm_light.json")))
DUSK = {"sky": [0.36, 0.33, 0.36, 1], "sky_strength": 0.75, "sun": 4.2, "sun_rgb": [1.0, 0.62, 0.34], "angle": 6, "elev": 9, "az": -62,
        "exposure": 0.35, "fog": 0.0012, "fog_rgb": [1.0, 0.78, 0.6, 1], "camera_bg": [1.5, 1.0, 0.72]}
def show_all(sc):
    for o in sc.objects:
        if o.type == "MESH" and o.get("role") == "approach": o.hide_render = False
def light(sc, preset="warm", engine="CYCLES", fog=True, cam_bg=True):
    L = dict(WARM); L.update({"elev": 40, "az": -35})   # same sun direction as render_beauty (rotation 50 deg from zenith, -35 deg)
    if preset == "dusk": L.update(DUSK)
    w = bpy.data.worlds.new("FinalSky"); sc.world = w; w.use_nodes = True; nt = w.node_tree; bg = nt.nodes["Background"]
    bg.inputs[0].default_value = tuple(L["sky"][:3]) + (1,); bg.inputs[1].default_value = L["sky_strength"]
    if cam_bg and L.get("camera_bg"):
        lp = nt.nodes.new("ShaderNodeLightPath"); b2 = nt.nodes.new("ShaderNodeBackground"); mx = nt.nodes.new("ShaderNodeMixShader")
        b2.inputs[0].default_value = tuple(L["camera_bg"]) + (1,); out = nt.nodes["World Output"]
        nt.links.new(lp.outputs["Is Camera Ray"], mx.inputs[0]); nt.links.new(bg.outputs[0], mx.inputs[1]); nt.links.new(b2.outputs[0], mx.inputs[2])
        nt.links.new(mx.outputs[0], out.inputs["Surface"])
    sun = bpy.data.objects.new("FinalSun", bpy.data.lights.new("FinalSun", "SUN")); sc.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(90 - L["elev"]), 0, math.radians(L["az"]))
    sun.data.energy = L["sun"]; sun.data.angle = math.radians(L["angle"]); sun.data.color = tuple(L["sun_rgb"][:3])
    sc.view_settings.view_transform = "AgX"; sc.view_settings.look = L["look"]; sc.view_settings.exposure = L["exposure"]
    if fog and L.get("fog", 0) > 0:
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, 30)); fb = bpy.context.active_object; fb.name = "FogVolume"; fb.scale = (150, 150, 64)
        fm = bpy.data.materials.new("Fog"); fm.use_nodes = True; t = fm.node_tree; t.nodes.remove(t.nodes["Principled BSDF"])
        pv = t.nodes.new("ShaderNodeVolumePrincipled"); pv.inputs["Density"].default_value = L["fog"]
        pv.inputs["Color"].default_value = tuple(L["fog_rgb"][:3]) + (1,); pv.inputs["Anisotropy"].default_value = 0.35
        t.links.new(pv.outputs[0], t.nodes["Material Output"].inputs["Volume"]); fb.data.materials.append(fm)
    if engine == "CYCLES":
        sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.use_denoising = True; sc.cycles.denoiser = "OPENIMAGEDENOISE"
        sc.cycles.volume_step_rate = 4.0; sc.cycles.volume_max_steps = 256
    else:
        sc.render.engine = "BLENDER_EEVEE"; e = sc.eevee
        e.taa_render_samples = 24; e.use_shadows = True; e.shadow_ray_count = 2; e.shadow_step_count = 6; e.shadow_resolution_scale = 1.0
        e.use_raytracing = True; e.ray_tracing_method = "SCREEN"; e.use_fast_gi = True; e.fast_gi_distance = 6.0; e.fast_gi_quality = 0.5
        e.volumetric_tile_size = "8"; e.volumetric_samples = 32; e.use_volumetric_shadows = False; e.volumetric_end = 250
    sc.render.film_transparent = False
    return sun
def camera(sc, loc, look, lens=24.0, ortho=None):
    cam = bpy.data.objects.new("FinalCam", bpy.data.cameras.new("FinalCam")); sc.collection.objects.link(cam); sc.camera = cam
    cam.data.clip_start = 0.1; cam.data.clip_end = 3000; cam.data.sensor_width = 36
    if ortho: cam.data.type = "ORTHO"; cam.data.ortho_scale = ortho
    else: cam.data.lens = lens
    cam.location = Vector(loc); cam.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat("-Z", "Y").to_euler(); return cam
