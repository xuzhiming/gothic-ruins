"""Final beauty stills (Cycles CPU + OpenImageDenoise, warm preset = compare/mat/warm_light.json; 'dusk' = golden-hour variant).
  blender -b building.blend -P src/render_still.py -- SHOT OUT.png [samples] [res_x]      (shots below; one Blender per shot)"""
import bpy, sys, os, time, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import final_scene as F
from mathutils import Vector
argv = sys.argv[sys.argv.index("--") + 1:]; SHOT, OUT = argv[0], argv[1]
SPP = int(argv[2]) if len(argv) > 2 else 64; RX = int(argv[3]) if len(argv) > 3 else 2560
def iso_cam(sc, az=22.0, el=50.0, tgt=(0.0, -2.0, 8.0), scale=118.0):
    A, E = math.radians(az), math.radians(el); d = Vector((math.sin(A)*math.cos(E), -math.cos(A)*math.cos(E), math.sin(E)))
    return F.camera(sc, Vector(tgt) + d*400, tgt, ortho=scale)
# name: (camera, light preset, aspect h/w, extra)
SHOTS = {
    "01_hero_iso":       ("iso", "warm", 960/808, {}),
    "02_aerial_south":   (((0.0, -98.0, 40.0), (0.0, -18.0, 5.0), 32), "warm", 9/16, {}),
    "03_plaza_facade":   (((-3.0, -27.0, 5.85), (0.0, 3.9, 15.5), 20), "warm", 9/16, {}),
    "04_portal":         (((-3.2, -12.5, 5.85), (0.0, 3.9, 10.0), 30), "warm", 9/16, {}),
    "05_nave_interior":  (((0.0, 7.0, 8.25), (0.0, 38.0, 11.5), 18), "warm", 9/16, {"fog": 0.004, "sun": 7.0, "exposure": 1.5}),
    "06_street_west":    (((-17.7, -3.0, 5.85), (-17.2, 25.0, 7.5), 24), "warm", 9/16, {}),
    "07_apse_NE":        (((26.0, 84.0, 36.0), (0.0, 36.0, 12.0), 32), "warm", 9/16, {}),
    "08_hero_iso_dusk":  ("iso", "dusk", 960/808, {"exposure": 0.9, "sun": 6.0}),
}
cam, preset, asp, ex = SHOTS[SHOT]; sc = bpy.context.scene; F.show_all(sc)
if "fog" in ex: F.WARM = dict(F.WARM, fog=ex["fog"])
for k in ("sun", "exposure"):
    if k in ex: F.WARM = dict(F.WARM, **{k: ex[k]}); F.DUSK = dict(F.DUSK, **{k: ex[k]})
sun = F.light(sc, preset=preset, engine="CYCLES")
if cam == "iso": iso_cam(sc)
else: F.camera(sc, cam[0], cam[1], lens=cam[2])
sc.cycles.samples = SPP; sc.cycles.use_adaptive_sampling = True; sc.cycles.adaptive_threshold = 0.02
sc.render.resolution_x = RX; sc.render.resolution_y = int(round(RX*asp)); sc.render.resolution_percentage = 100
sc.render.image_settings.file_format = "PNG"; sc.render.image_settings.color_depth = "8"
t = time.time(); sc.render.filepath = OUT; bpy.ops.render.render(write_still=True)
print(f"STILL OK {SHOT} {sc.render.resolution_x}x{sc.render.resolution_y} spp {SPP} {time.time() - t:.0f}s")
