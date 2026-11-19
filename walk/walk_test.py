"""Headless-Chrome walk test of web/index.html.
Drives the preview with real WASD key events (W held; yaw steering via the test hook stands in for mouse-look) along the full route:
approach -> south monumental stairs -> plaza (around the bollard chain) -> cathedral steps -> portal (auto doors) -> nave -> apse ->
ambulatory -> aisle E -> SE tower -> back through the arcade -> out -> iron gate (auto) into the E yard -> west street ->
townhouse W3 (auto door) -> stair to F1 -> second flight to F2 -> partition door -> back room.
Records the trajectory, checks every movement segment for wall penetration (BVH ray between consecutive samples at knee and chest
height), detects getting stuck, checks auto-doors were open when passed, takes checkpoint screenshots.
usage: python3 walk/walk_test.py [--url http://localhost:8766/index.html]"""
import asyncio, json, math, os, sys, time
from playwright.async_api import async_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
URL = sys.argv[sys.argv.index("--url") + 1] if "--url" in sys.argv else "http://localhost:8766/index.html"
S = json.load(open(os.path.join(ROOT, "web", "spaces.json")))
D = {d["id"]: d for d in S["doors"]}; ST = {s["id"]: s for s in S["stairs"]}; SPC = S["spaces"]
def pr(s): return tuple(SPC[s]["probe"])
def through(did, k=1.4, frm=None):
    """two points either side of an opening, ordered from space `frm` (default: door's a) to the other side"""
    d = D[did]; c, n = d["center"], d["normal"]; frm = frm or d["a"]
    pa = SPC[frm]["probe"]; s = -1 if ((c[0] - pa[0])*n[0] + (c[1] - pa[1])*n[1]) < 0 else 1
    za = c[2]; zb = c[2]
    return [(c[0] - s*n[0]*k, c[1] - s*n[1]*k, za), (c[0] + s*n[0]*k, c[1] + s*n[1]*k, zb)]
def stairpts(sid, every=4):
    s = ST[sid]; st = s["steps"]; return [tuple(s["entry"])] + [tuple(p) for p in st[::every]] + [tuple(st[-1]), tuple(s["exit"])]
def off(p, n, k): return (p[0] + n[0]*k, p[1] + n[1]*k, p[2])
PZ = S["meta"]["plaza_z"]; ZC = S["meta"]["cathedral_floor_z"]
cy = SPC["ambulatory"]["probe"][1] - 6.9
amb = [(6.9*math.cos(math.radians(a)), cy + 6.9*math.sin(math.radians(a)), ZC) for a in (30, 5)]
w3 = D["W3_door"]; nW3 = w3["normal"]; s01, s12 = ST["W3_stair_01"], ST["W3_stair_12"]; p2 = D["W3_F2_part"]
ROUTE = [("start", pr("approach")), ("shot", "01_approach_stairs"),
         *stairpts("stairs_south_lower"), *stairpts("stairs_south_upper"), (0, -33.0, PZ), ("shot", "02_plaza"),
         (-16.5, -30.0, PZ), (-16.5, -4.5, PZ), (0, -4.5, PZ), ("shot", "03_cathedral_steps"),
         *stairpts("cathedral_steps"), ("shot", "04_portal"),
         *through("portal", 1.6), ("shot", "05_nave"), (0, 20, ZC), (0, cy - 4.5, ZC), ("shot", "06_apse"),
         (3.2, cy - 1.0, ZC), *through("apse_arcade_1", 1.2, "nave"), *amb, *through("aisle_E_ambulatory", 1.2, "ambulatory"), ("shot", "07_ambulatory_to_aisle"),
         (9.25, 30.0, ZC), (9.25, 12.2, ZC), *through("tower_SE_aisle_E", 1.3, "aisle_E"), ("shot", "08_tower_SE"),
         *through("tower_SE_aisle_E", 1.3, "tower_SE"), *through("arcade_aisle_E_1", 1.6, "aisle_E"), (0, 8.0, ZC),
         *through("portal", 1.6, "nave"), ("shot", "09_leaving"), *stairpts("cathedral_steps")[::-1], (0, -4.5, PZ),
         *through("gate_yard_E", 1.6, "plaza"), ("shot", "10_gate_yard_E", (6.0, -20.0)), *through("gate_yard_E", 1.6, "yard_E"),
         (-17.7, -4.5, PZ), (-17.7, w3["center"][1], PZ), ("shot", "11_street_W", (-17.7, 30.0)),
         *through("W3_door", 1.3, "street_W"), ("shot", "12_house_W3_GF", s01["steps"][len(s01["steps"])//2]),
         off(s01["entry"], nW3, -1.2), *stairpts("W3_stair_01", 3), ("shot", "13_W3_F1", s12["steps"][len(s12["steps"])//2]),
         *stairpts("W3_stair_12", 3), off(s12["exit"], nW3, -2.0), ("shot", "14_W3_F2", p2["center"]),
         off(p2["center"], nW3, -4.0), *through("W3_F2_part", 1.2, "W3_F2_front"), pr("W3_F2_back"), ("shot", "15_W3_F2_back")]

async def main():
    async with async_playwright() as p:
        br = await p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
        pg = await br.new_page(viewport={"width": 960, "height": 600})
        errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
        t_load = time.time(); await pg.goto(URL + "?test=1")
        await pg.wait_for_function("window.__walk && window.__walk.ready", timeout=300000); t_load = time.time() - t_load
        W = "window.__walk"
        # sanity: the penetration detector must see the wall between the street and the closed house interior
        pb = SPC["W2_F0_back"]["probe"]
        sanity = await pg.evaluate(f"{W}.raySegment([-17.7,{pb[1]},{PZ + 1.2}],[{pb[0]},{pb[1]},{PZ + 1.2}])")
        traj, events, pen, stuck, doorpass = [], [], [], [], []
        t0 = time.time(); prev = None
        async def st(): return await pg.evaluate(f"{W}.state()")
        async def shot(name):
            await pg.evaluate(f"{W}.render()"); path = os.path.join(HERE, f"cp_{name}.png")
            await pg.screenshot(path=path); s = await st(); events.append({"shot": name, "at": [round(s['x'], 2), round(s['y'], 2), round(s['z'], 2)], "near": s["near"]})
        async def sample():
            nonlocal prev
            s = await st(); s["t"] = round(time.time() - t0, 2); traj.append(s)
            if prev is not None:
                for h in (0.5, 1.3):
                    a = [prev["x"], prev["y"], prev["z"] + h]; b = [s["x"], s["y"], s["z"] + h]
                    hit = await pg.evaluate(f"{W}.raySegment({json.dumps(a)},{json.dumps(b)})")
                    if hit is not None: pen.append({"t": s["t"], "from": a, "to": b, "hit_at": hit})
            for d in await pg.evaluate(f"{W}.doorsNear(0.8)"): doorpass.append({"door": d["id"], "open": round(d["open"], 2), "t": s["t"]})
            prev = s; return s
        ok_route = True; n_wp = 0
        for item in ROUTE:
            if item[0] == "start":
                x, y, z = item[1]; await pg.evaluate(f"{W}.teleport({x},{y - 1.5},{z},0)"); await pg.wait_for_timeout(700); await sample(); continue
            if item[0] == "shot":
                if len(item) > 2:   # optional look-at point for the screenshot (heading only, the walk resumes its own steering)
                    s = await st(); await pg.evaluate(f"{W}.setYaw({math.atan2(-(item[2][0] - s['x']), item[2][1] - s['y'])})"); await pg.wait_for_timeout(150)
                await shot(item[1]); continue
            tx, ty, tz = item; n_wp += 1
            await pg.keyboard.down("w"); best, best_t, arrived = 1e9, time.time(), False
            while True:
                s = await sample(); dx, dy = tx - s["x"], ty - s["y"]; dist = math.hypot(dx, dy)
                if dist < 0.35: arrived = True; break
                await pg.evaluate(f"{W}.setYaw({math.atan2(-dx, dy)})")
                if dist < best - 0.08: best, best_t = dist, time.time()
                if time.time() - best_t > 5.0: stuck.append({"target": item, "at": [round(s["x"], 2), round(s["y"], 2), round(s["z"], 2)], "dist": round(dist, 2)}); break
                await pg.wait_for_timeout(30 if dist < 1.0 else 70)
            await pg.keyboard.up("w"); await pg.wait_for_timeout(100); s = await sample()
            if not arrived: ok_route = False; events.append({"stuck_before": item}); break
            if abs(s["z"] - tz) > 0.5: events.append({"warn_level": item, "z": round(s["z"], 2)})
        await shot("99_end"); final = await st()
        await br.close()
    dmin = {}
    for d in doorpass: dmin[d["door"]] = min(dmin.get(d["door"], 1.0), d["open"])
    lvl_warn = [e for e in events if "warn_level" in e]
    res = {"route_completed": ok_route, "waypoints": n_wp, "final_state": final, "final_space_guess": final.get("near"), "load_s": round(t_load, 1),
           "samples": len(traj), "duration_s": round(time.time() - t0, 1),
           "path_length_m": round(sum(math.dist((a['x'], a['y'], a['z']), (b['x'], b['y'], b['z'])) for a, b in zip(traj, traj[1:])), 1),
           "climb_m": round(sum(max(0, b['z'] - a['z']) for a, b in zip(traj, traj[1:])), 2),
           "penetrations": pen, "stuck": stuck, "level_warnings": lvl_warn, "doors_passed_min_open": dmin, "events": events, "page_errors": errs,
           "sanity_ray_hits_wall": sanity is not None,
           "PASS": ok_route and not pen and not stuck and not lvl_warn and all(v >= 0.9 for v in dmin.values()) and len(dmin) >= 4 and not errs and sanity is not None}
    json.dump(res, open(os.path.join(HERE, "walk_result.json"), "w"), indent=1)
    with open(os.path.join(HERE, "trajectory.csv"), "w") as f:
        f.write("t,x,y,z,yaw,onGround,near\n")
        for s in traj: f.write(f"{s['t']},{s['x']:.3f},{s['y']:.3f},{s['z']:.3f},{s['yaw']:.3f},{int(s['onGround'])},{s['near']}\n")
    plot(traj, events)
    print("WALK", "PASS" if res["PASS"] else "FAIL", {k: res[k] for k in ("route_completed", "waypoints", "samples", "path_length_m", "climb_m", "duration_s")},
          "penetrations", len(pen), "stuck", len(stuck), "level_warn", len(lvl_warn), "doors", dmin, "errs", errs[:3], "sanity_wall_ray", sanity)

def plot(traj, events):
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    from PIL import Image
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(15, 9), gridspec_kw={"width_ratios": [1.0, 1.1]})
    top = os.path.join(ROOT, "renders", "shaded_top.png"); meta = os.path.join(ROOT, "renders", "sil_meta.json")
    if os.path.exists(top) and os.path.exists(meta):
        m = json.load(open(meta)); v = m["views"]["top"]; a1.imshow(Image.open(top), extent=(-v["frame_w"]/2, v["frame_w"]/2, -v["frame_h"]/2, v["frame_h"]/2), alpha=0.75)
    xs = [s["x"] for s in traj]; ys = [s["y"] for s in traj]; zs = [s["z"] for s in traj]
    sc = a1.scatter(xs, ys, c=zs, s=3, cmap="plasma"); plt.colorbar(sc, ax=a1, label="feet z (m)", shrink=0.7)
    for e in events:
        if "shot" in e: a1.annotate(e["shot"][:2], e["at"][:2], fontsize=8, color="black", weight="bold")
    a1.set_aspect("equal"); a1.set_title("walk trajectory over the plan (Blender XY, m)"); a1.set_xlim(-36, 36); a1.set_ylim(-58, 52)
    a2.plot([s["t"] for s in traj], zs); a2.set_xlabel("time (s)"); a2.set_ylabel("feet z (m)"); a2.grid(alpha=.3)
    a2.set_title("height over time: ground 0 -> plaza -> cathedral floor -> plaza -> house F1/F2")
    fig.tight_layout(); fig.savefig(os.path.join(HERE, "trajectory.png"), dpi=100)

asyncio.run(main())
