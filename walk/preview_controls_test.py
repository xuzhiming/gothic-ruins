"""Browser checks for jump, fly, focus/blur, mode buttons, and glass runtime policy.
Loads web/index.html?test=1. Does not require the upcoming transparent GLB.
usage: python3 walk/preview_controls_test.py [--url http://localhost:8766/index.html]
"""
import asyncio, json, math, os, sys, time
from playwright.async_api import async_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
URL = sys.argv[sys.argv.index("--url") + 1] if "--url" in sys.argv else "http://localhost:8766/index.html"
S = json.load(open(os.path.join(ROOT, "web", "spaces.json")))
SHOT = os.path.join(HERE, "cp_fly_mode.png")


def sep(url):
    return "&" if "?" in url else "?"


async def main():
    fails = []
    notes = {}

    def check(name, cond, detail=""):
        if cond:
            print("OK", name, detail)
        else:
            fails.append(name if not detail else f"{name}: {detail}")
            print("FAIL", name, detail)

    async with async_playwright() as p:
        br = await p.chromium.launch(
            executable_path="/usr/bin/google-chrome",
            args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"],
        )
        pg = await br.new_page(viewport={"width": 1100, "height": 720})
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        await pg.goto(URL + sep(URL) + "test=1")
        await pg.wait_for_function("window.__walk && window.__walk.ready", timeout=300000)
        W = "window.__walk"

        async def ev(expr):
            return await pg.evaluate(expr)

        async def st():
            return await ev(f"{W}.state()")

        # --- glass policy fixtures (no GLB dependency) ---
        fixtures = await ev(f"""() => {{
          const C = {W}.classifySurface, P = {W}.applyPolicy;
          if (!C || !P) return null;
          const cases = [
            {{ meshName:'Blind_lancet', role:'solid', materialName:'Stone', transparent:false, opacity:1, depthWrite:true, alphaMode:'OPAQUE' }},
            {{ meshName:'Glass_blind', role:'solid', materialName:'Glass_blind', transparent:false, opacity:1, depthWrite:true, alphaMode:'OPAQUE' }},
            {{ meshName:'Glass_glass', role:'glass', materialName:'Glass', transparent:false, opacity:1, depthWrite:true, alphaMode:'OPAQUE' }},
            {{ meshName:'Glass_glass', role:'glass', materialName:'Glass', transparent:true, opacity:0.35, depthWrite:false, alphaMode:'BLEND' }},
            {{ meshName:'Pane', role:'glass', materialName:'Window', transparent:false, opacity:0.4, depthWrite:true, alphaMode:'' }},
            {{ meshName:'Cutout', role:'glass', materialName:'GlassMask', transparent:false, opacity:1, depthWrite:true, alphaMode:'MASK' }}
          ];
          return cases.map(c => ({{ input:c, cls:C(c), pol:P(c) }}));
        }}""")
        check("policy hooks", fixtures is not None, "" if fixtures is not None else "classifySurface/applyPolicy missing")
        if fixtures:
            by = {(c["input"]["meshName"], c["input"]["alphaMode"], round(c["input"]["opacity"], 2)): c for c in fixtures}
            blind = by[("Blind_lancet", "OPAQUE", 1)]
            name_only = by[("Glass_blind", "OPAQUE", 1)]
            opaque_role = by[("Glass_glass", "OPAQUE", 1)]
            blend = by[("Glass_glass", "BLEND", 0.35)]
            opacity = by[("Pane", "", 0.4)]
            mask = by[("Cutout", "MASK", 1)]
            check("blind stays opaque", (not blind["cls"]["realGlass"]) and blind["pol"]["transparent"] is False and blind["pol"]["castShadow"] is True and blind["pol"]["depthWrite"] is True)
            check("Glass_blind name is not clear glass", (not name_only["cls"]["realGlass"]) and name_only["pol"]["transparent"] is False and name_only["pol"]["opacity"] == 1 and name_only["pol"]["renderOrder"] == 0)
            check("opaque material named Glass stays opaque", (not opaque_role["cls"]["realGlass"]) and opaque_role["pol"]["transparent"] is False and opaque_role["pol"]["castShadow"] is True)
            check("exact blended Glass flags", blend["cls"]["realGlass"] and blend["pol"]["transparent"] is True and blend["pol"]["depthWrite"] is False and blend["pol"]["depthTest"] is True and blend["pol"]["castShadow"] is False and blend["pol"]["receiveShadow"] is False and blend["pol"]["renderOrder"] == 0 and abs(blend["pol"]["opacity"] - 0.35) < 1e-6)
            check("other blended names stay put", (not opacity["cls"]["realGlass"]) and opacity["pol"]["castShadow"] is True and abs(opacity["pol"]["opacity"] - 0.4) < 1e-6 and opacity["pol"]["depthWrite"] is True)
            check("mask name is not clear glass", (not mask["cls"]["realGlass"]) and mask["pol"]["transparent"] is False and mask["pol"]["castShadow"] is True)

        surfaces = await ev(f"{W}.surfaces ? {W}.surfaces() : null")
        check("surface report", isinstance(surfaces, list) and len(surfaces) > 0)
        if isinstance(surfaces, list):
            bad_opaque = [r for r in surfaces if (not r.get("blended")) and r.get("transparent") and not str(r.get("material", "")).lower().startswith("decal") and r.get("role") != "decor"]
            check("live opaque not forced transparent", not bad_opaque, str(bad_opaque[:3]))
            real = [r for r in surfaces if r.get("material") == "Glass"]
            blind_rows = [r for r in surfaces if r.get("material") == "Glass_blind"]
            notes["real_glass"] = len(real)
            notes["glass_blind"] = len(blind_rows)
            notes["e2e_glass"] = "loaded_glb_flags_visual_separate"
            check("loaded Glass panes", len(real) >= 1, str(len(real)))
            for r in real:
                check("loaded Glass contract", r.get("realGlass") and r.get("transparent") is True and r.get("depthWrite") is False and r.get("depthTest") is True and r.get("renderOrder") == 0 and abs(r.get("opacity", 1) - 0.24) < 0.02 and abs(r.get("roughness", 1) - 0.09) < 0.02 and abs(r.get("metalness", 1)) < 0.01 and r.get("side") == 2, str({k: r.get(k) for k in ("mesh", "opacity", "roughness", "metalness", "side", "depthWrite", "renderOrder")}))
            check("loaded Glass_blind", len(blind_rows) >= 1, str(len(blind_rows)))
            for r in blind_rows:
                check("loaded Glass_blind opaque", (not r.get("realGlass")) and r.get("transparent") is False and r.get("depthWrite") is True and r.get("opacity", 0) >= 0.999, str(r.get("mesh")))
            decals = [r for r in surfaces if str(r.get("material", "")).lower().startswith("decal")]
            check("decals present", len(decals) > 0, str(len(decals)))
            if decals:
                d0 = decals[0]
                check("decal blend unchanged", d0.get("transparent") is True and d0.get("depthWrite") is False and d0.get("castShadow") is False and d0.get("renderOrder") == 2, d0.get("material"))
        glass = await ev(f"{W}.glassSample ? {W}.glassSample() : null")
        check("glass sample", isinstance(glass, dict), str(glass))
        if isinstance(glass, dict):
            notes["glass_meshes"] = glass.get("meshes")
            check("glass meshes exist", glass.get("meshes", 0) > 0, str(glass.get("meshes")))
            check("glass stays in collider", glass.get("excluded") == 0 and glass.get("rayHit") is True, json.dumps(glass.get("sample")))

        # settle on the west street, which the walk route already treats as open
        await ev(f"{W}.teleport(-17.7, 0.867, 4.2, 0)")
        for _ in range(40):
            s = await st()
            if s.get("onGround"):
                break
            await pg.wait_for_timeout(50)
        check("street grounds", (await st()).get("onGround") is True, str(await st()))
        base = await st()

        # single jump, Space held
        await pg.keyboard.down("Space")
        zs = []
        t0 = time.time()
        while time.time() - t0 < 0.9:
            zs.append((await st())["z"])
            await pg.wait_for_timeout(30)
        await pg.keyboard.up("Space")
        z0 = base["z"]
        rise = [z - z0 for z in zs]
        peaks = 0
        for i in range(1, len(rise) - 1):
            if rise[i] > rise[i - 1] + 0.01 and rise[i] >= rise[i + 1] and rise[i] > 0.08:
                peaks += 1
        check("single jump peak", peaks == 1, f"peaks={peaks} max={max(rise):.3f}")
        check("jump height", 0.15 < max(rise) < 0.55, f"max={max(rise):.3f}")
        await pg.wait_for_timeout(400)
        check("landed after jump", (await st()).get("onGround") is True and abs((await st())["z"] - z0) < 0.2)

        # House floors are about 3 m apart, so a 0.42 m jump never meets them.
        # sealOverhead inserts a real BVH quad into the same raycast and capsule push.
        await ev(f"{W}.teleport(-17.7, 0.867, {z0}, 0)")
        for _ in range(30):
            if (await st()).get("onGround"):
                break
            await pg.wait_for_timeout(40)
        lid = await ev(f"{W}.sealOverhead ? {W}.sealOverhead(0.22) : null")
        check("seal overhead", isinstance(lid, (int, float)), str(lid))
        z_before = (await st())["z"]
        await pg.keyboard.down("Space")
        capped = []
        t0 = time.time()
        while time.time() - t0 < 0.7:
            capped.append((await st())["z"])
            await pg.wait_for_timeout(30)
        await pg.keyboard.up("Space")
        cap_rise = max(capped) - z_before if capped else 99
        check("ceiling blocks jump", 0.02 < cap_rise < 0.30, f"rise={cap_rise:.3f} lid={lid}")
        await ev(f"{W}.clearLid && {W}.clearLid()")
        await pg.wait_for_timeout(500)

        # button focus: Space must jump, not activate Orbit
        await ev(f"{W}.teleport(-17.7, 0.867, {z0}, 0)")
        for _ in range(30):
            if (await st()).get("onGround"):
                break
            await pg.wait_for_timeout(40)
        await pg.focus("#bOrbit")
        z_focus = (await st())["z"]
        await pg.keyboard.press("Space")
        await pg.wait_for_timeout(180)
        s = await st()
        check("focused Orbit ignores Space click", s.get("mode") == "walk" and s.get("fly") is False, str(s))
        check("focused Space still jumps", s["z"] > z_focus + 0.08, f"{z_focus:.3f} -> {s['z']:.3f}")
        await pg.wait_for_timeout(400)

        # blur clears held W
        await ev(f"{W}.teleport(-17.7, 2.0, {z0}, 0)")
        for _ in range(20):
            if (await st()).get("onGround"):
                break
            await pg.wait_for_timeout(40)
        s0 = await st()
        await pg.click("canvas")
        await pg.keyboard.down("w")
        await pg.wait_for_timeout(350)
        s1 = await st()
        await pg.evaluate("window.dispatchEvent(new Event('blur'))")
        await pg.wait_for_timeout(40)
        s2 = await st()
        await pg.wait_for_timeout(300)
        s3 = await st()
        await pg.keyboard.up("w")
        moved = math.hypot(s1["x"] - s0["x"], s1["y"] - s0["y"])
        stuck = math.hypot(s3["x"] - s2["x"], s3["y"] - s2["y"])
        check("moves before blur", moved > 0.4, f"moved={moved:.3f}")
        check("stops after blur", stuck < 0.15, f"stuck={stuck:.3f}")

        # fly controls
        await pg.click("canvas")
        await ev(f"{W}.setFly(true)")
        s = await st()
        check("enter fly", s.get("fly") is True and s.get("mode") == "walk", str(s))
        hud = await ev("document.getElementById('hud').innerText")
        fly_on = await ev("document.getElementById('bFly').classList.contains('on')")
        walk_on = await ev("document.getElementById('bWalk').classList.contains('on')")
        check("fly hud", "飞行" in hud and "C" in hud and fly_on and not walk_on, hud.split("\\n")[0][:80])
        await ev(f"{W}.render()")
        await pg.screenshot(path=SHOT)
        origin = await st()
        await pg.keyboard.down("w")
        await pg.wait_for_timeout(400)
        await pg.keyboard.up("w")
        plain = await st()
        plain_d = math.hypot(plain["x"] - origin["x"], plain["y"] - origin["y"])
        await pg.keyboard.down("Shift")
        await pg.keyboard.down("w")
        await pg.wait_for_timeout(400)
        await pg.keyboard.up("w")
        await pg.keyboard.up("Shift")
        fast = await st()
        fast_d = math.hypot(fast["x"] - plain["x"], fast["y"] - plain["y"])
        check("fly forward", plain_d > 1.5, f"{plain_d:.2f} m")
        check("fly shift boost", fast_d > plain_d * 1.6, f"plain={plain_d:.2f} fast={fast_d:.2f}")
        z_fly = (await st())["z"]
        await pg.keyboard.down("Space")
        await pg.wait_for_timeout(300)
        await pg.keyboard.up("Space")
        z_up = (await st())["z"]
        await pg.keyboard.down("c")
        await pg.wait_for_timeout(300)
        await pg.keyboard.up("c")
        z_down = (await st())["z"]
        check("fly space up", z_up > z_fly + 1.2, f"{z_fly:.2f}->{z_up:.2f}")
        check("fly c down", z_down < z_up - 1.2, f"{z_up:.2f}->{z_down:.2f}")
        await ev(f"{W}.placeFly(400, 0, 10)")
        await pg.wait_for_timeout(80)
        far = await st()
        check("fly horizontal bound", math.hypot(far["x"], far["y"]) <= 151, f"{far['x']:.1f},{far['y']:.1f}")
        await ev(f"{W}.placeFly(0, 0, 400)")
        await pg.wait_for_timeout(80)
        hi = await st()
        await ev(f"{W}.placeFly(0, 0, -80)")
        await pg.wait_for_timeout(80)
        lo = await st()
        check("fly vertical bound", -15.1 <= lo["z"] and hi["z"] <= 160.1, f"hi={hi['z']:.2f} lo={lo['z']:.2f}")

        # doors stay shut while flying, open when walking
        portal = next(d for d in S["doors"] if d["id"] == "portal")
        pc = portal["center"]
        await ev(f"{W}.placeFly({pc[0]}, {pc[1] - 1.2}, {pc[2]})")
        await pg.wait_for_timeout(700)
        fly_doors = await ev(f"{W}.doorsNear(2.5)")
        fly_open = [d for d in fly_doors if d.get("id") == "portal" and d.get("open", 0) > 0.2]
        check("fly does not open portal", not fly_open, str(fly_doors))
        await ev(f"{W}.setFly(false)")
        await pg.wait_for_timeout(900)
        walk_doors = await ev(f"{W}.doorsNear(3.0)")
        # landing may move us; if we are still near the portal the door should open
        near_after = await st()
        dist = math.hypot(near_after["x"] - pc[0], near_after["y"] - pc[1])
        notes["portal_land_dist"] = round(dist, 2)
        if dist < 3.0 and abs(near_after["z"] - pc[2]) < 2.0:
            opened = [d for d in walk_doors if d.get("id") == "portal"]
            check("walk opens portal", opened and opened[0].get("open", 0) > 0.5, str(walk_doors))
        else:
            notes["portal_walk_open"] = "skipped_landed_away"

        # inside a wall: scan the street-to-W2 segment for a blocked capsule
        # Door center is y=0.867, so that line is the opening. Step aside onto the wall.
        blocked_at = None
        for yoff in (1.3, -1.3, 1.8, -1.8):
            for i in range(1, 28):
                x = -17.7 + (-21.85 + 17.7) * i / 28
                y = 0.867 + yoff
                if await ev(f"{W}.blocked({x}, {y}, 4.2)"):
                    blocked_at = (x, y)
                    break
            if blocked_at:
                break
        check("found solid between street and W2", blocked_at is not None, str(blocked_at))
        if blocked_at is not None:
            bx, by = blocked_at
            await ev(f"{W}.teleport(-17.7, 0.867, 4.2, 0)")
            await ev(f"{W}.setFly(false)")
            for _ in range(30):
                if (await st()).get("onGround") and (await st()).get("fly") is False:
                    break
                await pg.wait_for_timeout(40)
            safe = await st()
            await ev(f"{W}.setFly(true)")
            await ev(f"{W}.placeFly({bx}, {by}, 4.2)")
            inside = await st()
            check("placed inside solid", math.hypot(inside["x"] - bx, inside["y"] - by) < 0.4, str(inside))
            await ev(f"{W}.setFly(false)")
            await pg.wait_for_timeout(120)
            out = await st()
            still = await ev(f"{W}.blocked({out['x']}, {out['y']}, {out['z']})")
            away = math.hypot(out["x"] - bx, out["y"] - by)
            back = math.hypot(out["x"] - safe["x"], out["y"] - safe["y"])
            check("exit fly not inside solid", still is False and out.get("fly") is False and out["z"] > -5, str(out))
            check("exit fly safe pose", back < 1.5 or away > 0.4, f"away={away:.2f} back={back:.2f} out={out['x']:.2f},{out['y']:.2f},{out['z']:.2f}")

        # mode buttons and Tab
        await pg.click("#bFly")
        s = await st()
        hud = await ev("document.getElementById('hud').innerText")
        check("fly button", s.get("fly") is True and "飞行" in hud)
        await pg.keyboard.press("f")
        s = await st()
        check("f leaves fly", s.get("fly") is False and s.get("mode") == "walk")
        await pg.keyboard.press("Tab")
        s = await st()
        hud = await ev("document.getElementById('hud').innerText")
        orbit_on = await ev("document.getElementById('bOrbit').classList.contains('on')")
        check("tab orbit", s.get("mode") == "orbit" and s.get("fly") is False and orbit_on and "环绕" in hud, f"on={orbit_on} hud={hud.split(chr(10))[0]} state={s}")
        await pg.click("#bWalk")
        s = await st()
        check("walk button", s.get("mode") == "walk" and s.get("fly") is False)
        await pg.click("#bStart")
        await pg.wait_for_timeout(200)
        s = await st()
        check("start entrance", s.get("mode") == "walk" and s.get("fly") is False and s["y"] < -40, str(s))

        # touch cluster visibility
        await pg.set_viewport_size({"width": 390, "height": 700})
        await pg.click("#bWalk")
        touch = await ev("""() => {
          const t = document.getElementById('touch');
          const cs = getComputedStyle(t);
          return { display: cs.display, jump: !document.getElementById('tJump').hidden, up: !document.getElementById('tUp').hidden };
        }""")
        check("touch jump on narrow walk", touch and touch.get("display") != "none" and touch.get("jump") and not touch.get("up"), str(touch))
        await pg.click("#bFly")
        touch = await ev("""() => ({
          jump: !document.getElementById('tJump').hidden,
          up: !document.getElementById('tUp').hidden,
          down: !document.getElementById('tDown').hidden
        })""")
        check("touch fly vertical", touch.get("up") and touch.get("down") and not touch.get("jump"), str(touch))
        await pg.set_viewport_size({"width": 1100, "height": 720})
        wide = await ev("getComputedStyle(document.getElementById('touch')).display")
        check("touch hidden on desktop", wide == "none", wide)

        check("no page errors", not errs, str(errs[:2]))
        await br.close()

    res = {"PASS": not fails and not errs, "fails": fails, "page_errors": errs, "notes": notes, "shot": SHOT}
    json.dump(res, open(os.path.join(HERE, "preview_controls_result.json"), "w"), indent=1)
    print("PREVIEW", "PASS" if res["PASS"] else "FAIL", "fails", fails, "notes", notes, "errs", errs[:2])
    if fails or errs:
        sys.exit(1)


asyncio.run(main())
