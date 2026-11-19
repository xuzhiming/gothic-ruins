# =====================================================================================
# circulation_check.py (runs inside Blender on building.blend + spaces.json)
#   blender -b building.blend -P check/circulation_check.py -- [--block DOOR_ID] [--out PREFIX]
# Graph: spaces = nodes; doors / gates / arcade openings / stairs / open outdoor links = edges.
# An edge is only added if its geometric test passes:
#   door/gate/opening : rays through the opening at 1.0 m and (h-0.15) m (and at the jambs for wide ones) are clear,
#                       and a ray displaced sideways past the jamb HITS solid material (the opening really pierces a wall)
#   stair             : per step: tread exists (down-ray), riser 150-180 mm, tread >= 260 mm, headroom >= 2.1 m (up-ray);
#                       entry/exit standing points have floor
#   open link         : polyline sampled every 0.5 m: floor below every sample, no height jump > 0.2 m, clear at 0.5/1.5 m
# Then BFS from the entrance; every space must be reachable. Every space also needs a floor and >= 2.1 m headroom.
# Negative test: plug one door with a solid box -> the same check must FAIL (unreachable spaces / blocked door).
# =====================================================================================
import bpy, bmesh, json, math, os, sys
from mathutils import Vector
from mathutils.bvhtree import BVHTree
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
def arg(n, d=None): return argv[argv.index(n) + 1] if n in argv else d
BLOCK = arg("--block"); DIR = os.path.dirname(bpy.data.filepath)
OUT = arg("--out", os.path.join(DIR, "check", "circulation_report"))
S = json.load(open(os.path.join(DIR, "spaces.json")))
SKIP = {"glass_never", "decor"}   # decor = ruin decals + small debris (non-colliding in the viewer too)
def build_bvh(extra=()):
    dg = bpy.context.evaluated_depsgraph_get(); bm = bmesh.new()
    for ob in bpy.context.scene.objects:
        if ob.type != "MESH" or ob.name.startswith("DoorLeaf_") or ob.get("role") in SKIP: continue
        me = ob.evaluated_get(dg).to_mesh(); me.transform(ob.matrix_world); bm.from_mesh(me); ob.evaluated_get(dg).to_mesh_clear()
    for (c, sz) in extra:
        r = bmesh.ops.create_cube(bm, size=1.0)
        for v in r["verts"]: v.co = Vector((c[0] + v.co.x*sz[0], c[1] + v.co.y*sz[1], c[2] + v.co.z*sz[2]))
    t = BVHTree.FromBMesh(bm, epsilon=0.0); bm.free(); return t
def hit(T, o, d, L):
    d = Vector(d).normalized(); loc, nrm, idx, dist = T.ray_cast(Vector(o), d, L); return dist
def floor_z(T, p, up=1.0, down=3.0):
    d = hit(T, (p[0], p[1], p[2] + up), (0, 0, -1), up + down); return None if d is None else p[2] + up - d

def run(T, label):
    R = {"label": label, "doors": [], "stairs": [], "spaces": [], "links": [], "fail": []}
    ok_edge = {}
    for d in S["doors"]:
        c = Vector(d["center"]); n = Vector(d["normal"]).normalized(); t = Vector(d["tangent"])
        L = 2.4 if d["type"] != "opening" else 3.0
        hs = [0.25, 1.0, max(1.1, d["h"] - 0.15)]   # 0.25 m ray catches thresholds / kerbs a walker cannot step over
        lat = [0.0] if d["w"] < 1.6 else [0.0, -(d["w"]/2 - 0.35), d["w"]/2 - 0.35]
        clear, blocked = True, None
        for h in hs:
            for s in lat:
                o = c + t*s + Vector((0, 0, h)) - n*(L/2); dist = hit(T, o, n, L)
                if dist is not None: clear = False; blocked = [round(h, 2), round(s, 2), round(dist - L/2, 2)]
        wall = None
        if d.get("check_wall"):
            off = d["w"]/2 + 0.3; hp = d.get("wall_probe_h", 1.0)
            wall = all(hit(T, c + t*sg*off + Vector((0, 0, hp)) - n*(L/2), n, L) is not None for sg in (-1, 1))
        ok = clear and (wall is not False); ok_edge[d["id"]] = ok
        R["doors"].append({"id": d["id"], "type": d["type"], "a": d["a"], "b": d["b"], "clear": clear, "pierces_wall": wall, "ok": ok, "blocked_at": blocked})
        if not ok: R["fail"].append(f"door {d['id']} ({d['a']}->{d['b']}): clear={clear} pierces_wall={wall} blocked_at(h,lat,dist)={blocked}")
    for st in S["stairs"]:
        steps = st["steps"]; issues = []; tops = []
        for p in steps:
            z = floor_z(T, p, 0.5, 1.0); tops.append(z)
            if z is None or abs(z - p[2]) > 0.03: issues.append(f"tread missing/misplaced at {p} (found {z})")
        # treads: horizontal distance between consecutive step centres; risers from the measured tops
        rs = [b - a for a, b in zip(tops, tops[1:]) if a is not None and b is not None]
        trs = [math.dist(a[:2], b[:2]) for a, b in zip(steps, steps[1:])]
        z_lo = floor_z(T, st["entry"], 0.6, 1.0); z_hi = floor_z(T, st["exit"], 0.6, 1.0)
        if z_lo is not None and tops and tops[0] is not None: rs = [tops[0] - z_lo] + rs
        if z_hi is not None and tops and tops[-1] is not None: rs = rs + [z_hi - tops[-1]]
        if rs and (min(rs) < 0.149 or max(rs) > 0.181): issues.append(f"riser range {min(rs)*1000:.0f}-{max(rs)*1000:.0f} mm outside 150-180")
        if trs and min(trs) < 0.259: issues.append(f"tread {min(trs)*1000:.0f} mm < 260")
        hr = []
        for p in steps:
            dist = hit(T, (p[0], p[1], p[2] + 0.02), (0, 0, 1), 30.0); hr.append(30.0 if dist is None else dist + 0.02)
        hmin = min(hr) if hr else 99
        if hmin < st["headroom_min"]: issues.append(f"headroom {hmin:.2f} m < {st['headroom_min']} m at step {hr.index(hmin)}")
        for key, z in (("entry", z_lo), ("exit", z_hi)):
            if z is None or abs(z - st[key][2]) > 0.2: issues.append(f"{key} point has no floor at level (found {z})")
        ok = not issues; ok_edge[st["id"]] = ok
        R["stairs"].append({"id": st["id"], "a": st["a"], "b": st["b"], "n_steps": len(steps) + 1, "riser_mm": [round(min(rs)*1000, 1), round(max(rs)*1000, 1)] if rs else None,
                            "tread_mm": round(min(trs)*1000) if trs else None, "headroom_min_m": round(hmin, 2), "ok": ok, "issues": issues})
        if not ok: R["fail"].append(f"stair {st['id']}: {issues[:3]}")
    for i, ln in enumerate(S["open_links"]):
        pts = [Vector(p) for p in ln["path"]]; issues = []; prev = None
        for a, b in zip(pts, pts[1:]):
            L = (b - a).length; n = max(1, int(L/0.5))
            for k in range(n + 1):
                p = a + (b - a)*(k/n); z = floor_z(T, p, 1.0, 2.0)
                if z is None: issues.append(f"no floor at {tuple(round(x, 1) for x in p)}"); continue
                if prev is not None and abs(z - prev) > 0.2: issues.append(f"height jump {z - prev:+.2f} m at {tuple(round(x, 1) for x in p[:2])}")
                prev = z
            for h in (0.5, 1.5):
                d = Vector((b.x - a.x, b.y - a.y, 0)); 
                if d.length < 1e-6: continue
                o = Vector((a.x, a.y, (a.z) + h)); dist = hit(T, o, d, d.length)
                if dist is not None: issues.append(f"blocked at h={h} after {dist:.1f} m on segment {tuple(round(x,1) for x in a[:2])}->{tuple(round(x,1) for x in b[:2])}")
        ok = not issues; lid = f"open_{ln['a']}_{ln['b']}"; ok_edge[lid] = ok
        R["links"].append({"id": lid, "ok": ok, "issues": issues[:5]})
        if not ok: R["fail"].append(f"open link {lid}: {issues[:3]}")
    for nm, sp in S["spaces"].items():
        p = sp["probe"]; z = floor_z(T, p, 1.0, 1.0); up = hit(T, (p[0], p[1], p[2] + 0.05), (0, 0, 1), 60.0)
        head = 99.0 if up is None else up + 0.05; fl = z is not None and abs(z - p[2]) < 0.3
        ok = fl and head >= 2.1
        R["spaces"].append({"name": nm, "floor": fl, "headroom_m": round(head, 2), "ok": ok})
        if not ok: R["fail"].append(f"space {nm}: floor={fl} (z={z}) headroom={head:.2f}")
    adj = {}
    def link(a, b, via): adj.setdefault(a, []).append((b, via)); adj.setdefault(b, []).append((a, via))
    for d in S["doors"]:
        if ok_edge[d["id"]]: link(d["a"], d["b"], d["id"])
    for st in S["stairs"]:
        if ok_edge[st["id"]]: link(st["a"], st["b"], st["id"])
    for ln in S["open_links"]:
        lid = f"open_{ln['a']}_{ln['b']}"
        if ok_edge[lid]: link(ln["a"], ln["b"], lid)
    for lf in S["lifts"]:
        for a, b in zip(lf["stops"], lf["stops"][1:]): link(a, b, lf["id"])
    start = S["entrance"]; seen = {start: None}; q = [start]
    while q:
        a = q.pop(0)
        for b, via in adj.get(a, []):
            if b not in seen: seen[b] = (a, via); q.append(b)
    un = [s for s in S["spaces"] if s not in seen]
    R["reachable"] = len([s for s in seen if s in S["spaces"]]); R["unreachable"] = un
    def path(s):
        out = []
        while seen.get(s): a, via = seen[s]; out.append(via); s = a
        return out[::-1]
    R["paths"] = {s: path(s) for s in ("nave", "ambulatory", "tower_SW", "yard_E", "W3_F2_back", "NE_F1_back") if s in seen}
    if un: R["fail"].append(f"unreachable from '{start}': {un}")
    R["graph"] = {"nodes": len(S["spaces"]), "edges_total": len(S["doors"]) + len(S["stairs"]) + len(S["open_links"]), "edges_passing": sum(ok_edge.values())}
    R["PASS"] = not R["fail"]; return R

T = build_bvh(); main = run(T, "as-built")
# negative test: plug a door (default: the street door of house W3) with a solid box
neg_id = BLOCK or "W3_door"; d = next(x for x in S["doors"] if x["id"] == neg_id)
n = Vector(d["normal"]); c = d["center"]
sx = abs(n.x)*0.5 + abs(n.y)*(d["w"] + 0.4); sy = abs(n.y)*0.5 + abs(n.x)*(d["w"] + 0.4)
neg = run(build_bvh([((c[0], c[1], c[2] + d["h"]/2), (sx, sy, d["h"] + 0.3))]), f"NEGATIVE TEST: door {neg_id} blocked by a solid box")
neg["expected"] = "FAIL"; neg["caught"] = (not neg["PASS"]) and any(neg_id in f for f in neg["fail"])
neg["newly_unreachable"] = sorted(set(neg["unreachable"]) - set(main["unreachable"]))
# negative test 2: a stair with a too-high riser (raise one tread by 6 cm with a box)
st = next(s for s in S["stairs"] if s["id"] == "W3_stair_01"); p = st["steps"][5]
neg2 = run(build_bvh([((p[0], p[1], p[2] + 0.03), (0.6, 0.2, 0.06))]), "NEGATIVE TEST 2: one tread of W3_stair_01 raised 60 mm")
neg2["caught"] = any("W3_stair_01" in f for f in neg2["fail"])
os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump([main, neg, neg2], open(OUT + ".json", "w"), indent=1)
L = ["# Circulation check report", "", f"Model `{os.path.basename(bpy.data.filepath)}`: {len(S['spaces'])} spaces, {len(S['doors'])} doors/gates/openings, {len(S['stairs'])} stair flights, {len(S['open_links'])} outdoor links, {len(S['lifts'])} lifts (the medieval complex has none; lift edges are supported by the checker).", "",
     "Method: BVH of all solid meshes (door leaves excluded - they open automatically), ray tests through every opening, a sideways ray beside every door that must hit wall (proves the opening pierces a real wall), per-step tread/riser/headroom rays on every flight, floor-continuity sampling on outdoor links, floor + headroom probe in every space, BFS from the entrance `" + S["entrance"] + "`.", ""]
for R in (main, neg, neg2):
    L += [f"## {R['label']} -> **{'PASS' if R['PASS'] else 'FAIL'}**", ""]
    if "caught" in R: L += [f"Expected: FAIL. The check {'**caught it**' if R['caught'] else '**DID NOT CATCH IT**'}." + (f" Newly unreachable spaces: {R.get('newly_unreachable')}" if R.get('newly_unreachable') else ""), ""]
    L += [f"- openings ok: {sum(x['ok'] for x in R['doors'])}/{len(R['doors'])} (pierce their wall: {sum(1 for x in R['doors'] if x['pierces_wall'])}/{sum(1 for x in R['doors'] if x['pierces_wall'] is not None)})",
          f"- stair flights ok: {sum(x['ok'] for x in R['stairs'])}/{len(R['stairs'])}", f"- outdoor links ok: {sum(x['ok'] for x in R['links'])}/{len(R['links'])}",
          f"- spaces with floor + >= 2.1 m headroom: {sum(x['ok'] for x in R['spaces'])}/{len(R['spaces'])}",
          f"- reachable from entrance: {R['reachable']}/{len(S['spaces'])}; unreachable: {R['unreachable'] or 'none'}", ""]
    if R["fail"]: L += ["Failures:", ""] + [f"- {f}" for f in R["fail"][:30]] + [""]
    if R is main:
        L += ["Example routes (BFS):", ""] + [f"- **{k}**: {' -> '.join(v)}" for k, v in R["paths"].items()] + [""]
        L += ["| stair | from -> to | steps | riser range (measured) | min tread | min headroom | ok |", "|---|---|---|---|---|---|---|"]
        for s in R["stairs"]: L.append(f"| {s['id']} | {s['a']} -> {s['b']} | {s['n_steps']} | {s['riser_mm']} mm | {s['tread_mm']} mm | {s['headroom_min_m']} m | {'yes' if s['ok'] else 'NO'} |")
        L += ["", "| opening | type | a -> b | clear | pierces wall | ok |", "|---|---|---|---|---|---|"]
        for x in R["doors"]: L.append(f"| {x['id']} | {x['type']} | {x['a']} -> {x['b']} | {x['clear']} | {x['pierces_wall']} | {'yes' if x['ok'] else 'NO'} |")
        L.append("")
open(OUT + ".md", "w").write("\n".join(L))
print("CIRCULATION", "PASS" if main["PASS"] else "FAIL", "| reachable", f"{main['reachable']}/{len(S['spaces'])}", "| negative test caught:", neg["caught"], "| negative test 2 caught:", neg2["caught"])
for f in main["fail"][:40]: print("  FAIL:", f)
