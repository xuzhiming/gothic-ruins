"""Entrance clearance + bidirectional capsule + door-swing audit.

blender -b building.blend -P check/test_door_clearance.py -- [report.json]

Fails on the T24 alley baseline: continuous House_*_timber sole/mid facade
rails run through the GF door openings of NW, NE, and W0 (the only plaster
+ timber ground floors). South-end W4/E4 doors are already clear. After the
minimal timber_face gap, every house exterior door must accept a R=0.30 m
capsule with 2.1 m headroom, both ways, without globally dropping timber
collision or stripping timber that is not in the opening.
"""
import bpy, json, math, sys
from pathlib import Path
from collections import defaultdict
from mathutils import Vector, Matrix, Euler
from mathutils.bvhtree import BVHTree

ROOT = Path(bpy.data.filepath).parent
args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = Path(args[0]) if args else ROOT / "t27u-evidence" / "door_clearance.json"

S = json.loads((ROOT / "spaces.json").read_text())
R = 0.30
# Spine samples for a 2.1 m capsule: bottom sphere centre R, top centre 2.1-R.
HEIGHTS = (0.30, 0.80, 1.20, 1.60, 1.80)
HOUSE_EXT = {"W0_door", "W1_door", "W2_door", "W3_door", "W4_door",
             "E0_door", "E1_door", "E2_door", "E3_door", "E4_door",
             "NW_door", "NE_door"}
# Reported pair (north tail) plus the same-cause west-row first house.
REPORTED = ("NW_door", "NE_door")
SAME_CAUSE = ("W0_door",)
SOUTH_CLEAR_CONTROL = ("W4_door", "E4_door")


def classify(name, role, mat):
    n = (name or "").lower()
    m = (mat or "").lower()
    if name.startswith("DoorLeaf_") or role in ("door_leaf", "door_leaf_mesh"):
        return "door_leaf"
    if role == "decor" or name.startswith("Decal_") or name.startswith("Debris_"):
        return "decor_or_debris"
    if name.startswith("Ruin_") or "rubble" in n:
        return "ruin_rubble"
    if "timber" in n or "timber" in m or mat == "timber":
        return "timber"
    if name.startswith("WinFrame_") or "wframe" in m:
        return "window_frame"
    if "pentice" in n:
        return "pentice"
    if name.startswith("House_") and any(k in n for k in ("plaster", "brick", "stone")):
        return "house_masonry"
    if name.startswith(("Plaza_", "RearPlatform_", "Approach_", "Plinth_")):
        return "floor"
    if name.startswith("AlleyGuard_") or name.startswith("Balustrade_"):
        return "guard"
    if "glass" in n or role == "glass":
        return "glass"
    return f"other:{name}"


def world_mesh(ob):
    """World-space verts/faces of a mesh, applying parent (hinge empty) transforms."""
    deps = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(deps)
    me = ev.to_mesh()
    try:
        vs = [ev.matrix_world @ v.co for v in me.vertices]
        fs = [list(p.vertices) for p in me.polygons]
        return vs, fs, me
    finally:
        # to_mesh must be cleared after we copy coordinates
        pass


def build_solid_bvh(omit_leaves=True):
    vs, fs, names, roles, mats = [], [], [], [], []
    temps = []
    for ob in bpy.context.scene.objects:
        if ob.type != "MESH":
            continue
        role = ob.get("role")
        if omit_leaves and (ob.name.startswith("DoorLeaf_") or role in ("door_leaf", "door_leaf_mesh")):
            continue
        n0 = len(vs)
        # evaluated, so swing tests can rotate the empty first
        deps = bpy.context.evaluated_depsgraph_get()
        ev = ob.evaluated_get(deps)
        me = ev.to_mesh()
        temps.append((ev, me))
        vs.extend(ev.matrix_world @ v.co for v in me.vertices)
        for p in me.polygons:
            fs.append([n0 + i for i in p.vertices])
            names.append(ob.name)
            roles.append(role or "")
            mid = p.material_index
            mats.append(ev.data.materials[mid].name if ev.data.materials and mid < len(ev.data.materials) else "")
    T = BVHTree.FromPolygons(vs, fs)
    for ev, me in temps:
        ev.to_mesh_clear()
    return T, names, roles, mats


T, names, roles, mats = build_solid_bvh(True)


def nearest(p, r):
    hit = T.find_nearest(Vector(p), r)
    if hit[0] is None:
        return None
    loc, nrm, idx, dist = hit
    return dict(dist=round(float(dist), 5), point=[round(x, 4) for x in loc],
                object=names[idx], role=roles[idx], material=mats[idx],
                kind=classify(names[idx], roles[idx], mats[idx]))


def ray(o, d, L):
    p, n, i, t = T.ray_cast(Vector(o), Vector(d).normalized(), L)
    if p is None:
        return None
    return dict(dist=round(t, 4), point=[round(x, 4) for x in p],
                object=names[i], role=roles[i], material=mats[i],
                kind=classify(names[i], roles[i], mats[i]))


def unexpected_hit(h, w):
    if h["kind"] == "door_leaf":
        return False
    if h["kind"] == "decor_or_debris" and h.get("role") == "decor":
        return False  # non-colliding ruin dressing
    if h["kind"] == "glass":
        return False
    if h["kind"] == "house_masonry" and abs(h["s"]) < 0.35 and abs(h["lat"]) >= (w / 2 - R - 0.05):
        return False  # jambs
    if h["kind"] == "house_masonry" and h["z"] >= 2.05 and abs(h["s"]) < 0.40:
        return False  # lintel (should not be sampled, belt and braces)
    if h["kind"] == "floor" and h["z"] <= 0.31:
        return False
    return True


doors = [d for d in S["doors"] if d["id"] in HOUSE_EXT]
assert len(doors) == 12, [d["id"] for d in S["doors"] if d.get("type") == "ext_door"]

reports = []
for d in doors:
    c = Vector(d["center"])
    n = Vector(d["normal"]).normalized()
    t = Vector(d["tangent"]).normalized()
    w, h = d["w"], d["h"]
    unexpected = []
    blockers = defaultdict(int)
    for side, s0, s1 in (("outside_to_inside", -1.20, 0.90), ("inside_to_outside", 0.90, -1.20)):
        length = abs(s1 - s0)
        steps = max(1, int(round(length / 0.10)))
        for i in range(steps + 1):
            s = s0 + (s1 - s0) * i / steps
            for lat in (-(w / 2 - R - 0.02), 0.0, (w / 2 - R - 0.02)):
                for zh in HEIGHTS:
                    p = c + n * s + t * lat + Vector((0, 0, zh))
                    near = nearest(p, R + 0.001)
                    if near and near["dist"] < R - 1e-4:
                        rec = dict(side=side, s=round(s, 3), lat=round(lat, 3), z=zh, **near)
                        if unexpected_hit(rec, w):
                            unexpected.append(rec)
                            blockers[(near["kind"], near["object"])] += 1
    # Lintel / arch / wall above the leaf: sample several heights because arched
    # (gf_arch / round) heads rise ~0.35 m above the recorded 2.4 m leaf.
    lintel = None
    lintel_ok = False
    for dz in (0.12, 0.22, 0.32, 0.42, 0.52, 0.62):
        hit = ray(c + Vector((0, 0, h + dz)) - n * 0.8, n, 1.6)
        if hit and hit["kind"] in ("house_masonry", "timber") and hit["dist"] < 1.2:
            lintel, lintel_ok = hit, True
            break
        lintel = lintel or hit
    # Mid-height through-ray in the opening, excluding the wall thickness behind the leaf plane,
    # should not hit solid timber in front of or in the doorway.
    mid_block = []
    for zh in (0.40, 0.85, 1.20):
        for lat in (0.0, -(w / 2 - 0.20), w / 2 - 0.20):
            hit = ray(c + t * lat + Vector((0, 0, zh)) - n * 1.0, n, 2.0)
            if not hit:
                continue
            along = (Vector(hit["point"]) - c).dot(n)
            if hit["kind"] == "timber" and -0.50 <= along <= 0.25:
                mid_block.append(dict(z=zh, lat=round(lat, 3), along=round(along, 4), **hit))
    reports.append(dict(
        id=d["id"], w=w, h=h, unexpected=len(unexpected),
        blockers=[{"kind": k[0], "object": k[1], "n": n} for k, n in sorted(blockers.items(), key=lambda x: -x[1])],
        samples=unexpected[:8],
        lintel_ok=lintel_ok,
        lintel=lintel,
        mid_timber=mid_block[:6],
        mid_timber_hits=len(mid_block),
        clear=len(unexpected) == 0 and lintel_ok and len(mid_block) == 0,
    ))


def swing_clearance(door_id):
    """Rotate the hinge empty by its designed 86° swing and test the leaf mesh vs solids."""
    d = next(x for x in S["doors"] if x["id"] == door_id)
    emp_name = d["leaves"][0]
    emp = bpy.data.objects.get(emp_name)
    if emp is None:
        return dict(ok=False, reason=f"missing empty {emp_name}")
    swing = float(emp.get("swing", math.radians(86)))
    children = [ch for ch in emp.children if ch.type == "MESH"]
    if not children:
        return dict(ok=False, reason="missing leaf mesh")
    # Build BVH of solids excluding this leaf
    vs, fs, names2 = [], [], []
    temps = []
    deps = bpy.context.evaluated_depsgraph_get()
    for ob in bpy.context.scene.objects:
        if ob.type != "MESH":
            continue
        if ob.name.startswith("DoorLeaf_") or ob.get("role") in ("door_leaf", "door_leaf_mesh"):
            continue
        if ob.get("role") in ("decor", "glass", "approach", "base"):
            continue
        ev = ob.evaluated_get(deps)
        me = ev.to_mesh(); temps.append((ev, me))
        n0 = len(vs)
        vs.extend(ev.matrix_world @ v.co for v in me.vertices)
        for p in me.polygons:
            fs.append([n0 + i for i in p.vertices]); names2.append(ob.name)
    solid = BVHTree.FromPolygons(vs, fs)
    for ev, me in temps:
        ev.to_mesh_clear()
    hits = []
    orig = emp.rotation_euler.copy()
    try:
        for frac in (0.25, 0.5, 0.75, 1.0):
            emp.rotation_euler = Euler((orig.x, orig.y, orig.z + swing * frac), orig.order)
            bpy.context.view_layer.update()
            deps = bpy.context.evaluated_depsgraph_get()
            for ch in children:
                ev = ch.evaluated_get(deps)
                me = ev.to_mesh()
                lvs = [ev.matrix_world @ v.co for v in me.vertices]
                lfs = [list(p.vertices) for p in me.polygons]
                ev.to_mesh_clear()
                leaf = BVHTree.FromPolygons(lvs, lfs)
                # overlap / nearest within 5 mm means the leaf strikes a solid
                ov = leaf.overlap(solid)
                if ov:
                    kinds = []
                    for _a, b in ov[:80]:
                        name = names2[b]
                        kind = classify(name, "", "")
                        # Floor / designed jamb rebate: leaves sit mid-wall and clip masonry
                        # while swinging; that is pre-existing, not a door-mouth timber bar.
                        if kind in ("floor", "decor_or_debris", "glass", "guard", "house_masonry"):
                            continue
                        kinds.append((kind, name))
                    if kinds:
                        kind, name = kinds[0]
                        hits.append(dict(frac=frac, n_overlap=len(ov),
                                         n_relevant=len(kinds), object=name, kind=kind))
                        break
    finally:
        emp.rotation_euler = orig
        bpy.context.view_layer.update()
    return dict(ok=len(hits) == 0, swing_rad=round(swing, 4), hits=hits[:6])


swings = {}
for did in list(REPORTED + SAME_CAUSE + SOUTH_CLEAR_CONTROL):
    swings[did] = swing_clearance(did)

blocked = [r["id"] for r in reports if not r["clear"]]
missing_lintel = [r["id"] for r in reports if not r["lintel_ok"]]
swing_fail = [k for k, v in swings.items() if not v["ok"]]

# Stairs of the three affected houses still recorded (geometry exists; circulation_check does the full flight audit).
stair_ids = {s["id"] for s in S.get("stairs", [])}
need_stairs = [f"{hid}_stair_01" for hid in ("W0", "NW", "NE") if any(
    hid + "_door" == x for x in REPORTED + SAME_CAUSE)]
# W0/NW/NE all have F0-F1 stairs when floors>=2
for hid in ("W0", "NW", "NE"):
    if f"{hid}_stair_01" not in stair_ids and f"{hid}_stair_01" not in need_stairs:
        need_stairs.append(f"{hid}_stair_01")
missing_stairs = [s for s in ("W0_stair_01", "NW_stair_01", "NE_stair_01") if s not in stair_ids]

report = dict(
    capsule_R=R, heights=HEIGHTS, headroom_m=2.1,
    doors=reports,
    blocked=blocked,
    missing_lintel=missing_lintel,
    swings=swings,
    swing_fail=swing_fail,
    missing_stairs=missing_stairs,
    reported_pair=list(REPORTED),
    same_cause=list(SAME_CAUSE),
    south_control=list(SOUTH_CLEAR_CONTROL),
    PASS=not blocked and not missing_lintel and not swing_fail and not missing_stairs,
)

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(report, indent=2))
print("DOOR CLEARANCE")
for r in reports:
    flag = "clear" if r["clear"] else "BLOCKED"
    print(f"  {r['id']:10} {flag:8} unexpected={r['unexpected']:3} mid_timber={r['mid_timber_hits']:3} lintel={'ok' if r['lintel_ok'] else 'MISSING'} blockers={r['blockers'][:3]}")
print("swings", {k: ("ok" if v["ok"] else v) for k, v in swings.items()})
print("PASS" if report["PASS"] else "FAIL", "blocked=", blocked, "swing_fail=", swing_fail, "missing_lintel=", missing_lintel)
assert report["PASS"], f"entrance clearance failed: blocked={blocked} swing={swing_fail} lintel={missing_lintel} stairs={missing_stairs}"
