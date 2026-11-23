"""Visual and collision checks for the integrated glass GLB.
Loads the preview WITH shadows (no ?test=1). Saves screenshots under walk/glass_views/.
usage: python3 walk/glass_visual_test.py [--url http://127.0.0.1:8766/index.html]
"""
import asyncio, json, math, os, sys
from playwright.async_api import async_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "glass_views")
URL = sys.argv[sys.argv.index("--url") + 1] if "--url" in sys.argv else "http://127.0.0.1:8766/index.html"


def sep(url):
    return "&" if "?" in url else "?"


async def main():
    os.makedirs(OUT, exist_ok=True)
    fails = []
    notes = {}

    def check(name, cond, detail=""):
        print(("OK" if cond else "FAIL"), name, detail)
        if not cond:
            fails.append(name if not detail else f"{name}: {detail}")

    async with async_playwright() as p:
        br = await p.chromium.launch(
            executable_path="/usr/bin/google-chrome",
            args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"],
        )
        pg = await br.new_page(viewport={"width": 1280, "height": 720})
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        await pg.goto(URL)
        await pg.wait_for_function("window.__walk && window.__walk.ready", timeout=300000)
        W = "window.__walk"

        async def ev(expr):
            return await pg.evaluate(expr)

        rows = await ev(f"{W}.surfaces()")
        glass = [r for r in rows if r.get("material") == "Glass"]
        blind = [r for r in rows if r.get("material") == "Glass_blind"]
        decals = [r for r in rows if str(r.get("material", "")).lower().startswith("decal")]
        check("Glass rows", len(glass) >= 1, str(len(glass)))
        check("Glass_blind rows", len(blind) >= 1, str(len(blind)))
        check("decals", len(decals) >= 1, str(len(decals)))
        for r in glass:
            check(
                "shadowed Glass flags",
                r.get("transparent") is True and r.get("depthWrite") is False and r.get("depthTest") is True
                and r.get("castShadow") is False and r.get("receiveShadow") is False and r.get("renderOrder") == 0
                and abs(r.get("opacity", 1) - 0.24) < 0.02 and r.get("side") == 2,
                str({k: r.get(k) for k in ("opacity", "castShadow", "receiveShadow", "depthWrite", "renderOrder", "side")}),
            )
        for r in blind:
            check(
                "shadowed blind stays solid",
                r.get("transparent") is False and r.get("depthWrite") is True and r.get("castShadow") is True
                and r.get("opacity", 0) >= 0.999 and r.get("realGlass") is False,
                str({k: r.get(k) for k in ("transparent", "depthWrite", "castShadow", "opacity", "mesh")}),
            )
        for r in decals:
            check("decal order", r.get("transparent") is True and r.get("depthWrite") is False and r.get("renderOrder") == 2 and r.get("realGlass") is False, r.get("material"))
            break

        sample = await ev(f"{W}.glassSample()")
        check("pane ray hits collider", sample.get("excluded") == 0 and sample.get("rayHit") is True and sample.get("meshes", 0) >= 1, json.dumps(sample))

        probes = await ev(f"{W}.viewProbes()")
        notes["probe_counts"] = {k: len(v) for k, v in probes.items()}
        check("glass probes", len(probes.get("glass") or []) >= 3, str(notes["probe_counts"]))

        async def shot(name, eye, target):
            ex, ey, ez = eye
            tx, ty, tz = target
            await ev(f"{W}.lookAt({ex},{ey},{ez},{tx},{ty},{tz})")
            await pg.wait_for_timeout(120)
            await ev(f"{W}.render()")
            path = os.path.join(OUT, name + ".png")
            await pg.screenshot(path=path)
            return path

        shots = []
        glass_probes = probes.get("glass") or []
        # Spread: lowest, a mid house pane, and the highest (rose / attic).
        glass_probes = sorted(glass_probes, key=lambda q: q["z"])
        picked = [glass_probes[0], glass_probes[len(glass_probes) // 2], glass_probes[-1]]
        for i, q in enumerate(picked):
            px, py, pz = q["x"], q["y"], q["z"]
            nx, ny, nz = q["nx"], q["ny"], q["nz"]
            # Stand on the clear side of the pane.
            sign = 1
            for s in (1, -1):
                blocked = await ev(f"{W}.blocked({px + s*nx*0.8},{py + s*ny*0.8},{pz - 1.05})")
                if not blocked:
                    sign = s
                    break
            far = (px + sign * nx * 4.5, py + sign * ny * 4.5, pz + 0.2)
            near = (px + sign * nx * 0.85, py + sign * ny * 0.85, pz)
            inside = (px - sign * nx * 0.85, py - sign * ny * 0.85, pz)
            shots.append(await shot(f"glass_{i}_far", far, (px, py, pz)))
            shots.append(await shot(f"glass_{i}_near", near, (px, py, pz)))
            shots.append(await shot(f"glass_{i}_other_side", inside, (px, py, pz)))
            # Walk into the pane from the clear side. Feet sit about 1.1 m below the sample.
            sx, sy, sz = px + sign * nx * 0.75, py + sign * ny * 0.75, pz - 1.1
            await ev(f"{W}.teleport({sx},{sy},{sz},0)")
            await pg.wait_for_timeout(200)
            await ev(f"{W}.setYaw({math.atan2(-(px - sx), py - sy)})")
            await pg.keyboard.down("w")
            await pg.wait_for_timeout(700)
            await pg.keyboard.up("w")
            st = await ev(f"{W}.state()")
            start_signed = (sx - px) * nx + (sy - py) * ny
            end_signed = (st["x"] - px) * nx + (st["y"] - py) * ny
            crossed = start_signed * end_signed < 0 and abs(end_signed) > 0.12
            check(f"walk blocked by pane {i}", not crossed and st.get("fly") is False, f"start={start_signed:.2f} end={end_signed:.2f} at={st['x']:.2f},{st['y']:.2f},{st['z']:.2f}")
            # Noclip fly can still cross; that is the approved fly mode, not a missing collider.
            await ev(f"{W}.setFly(true)")
            await ev(f"{W}.placeFly({px - sign*nx*1.2},{py - sign*ny*1.2},{pz})")
            flown = await ev(f"{W}.state()")
            check(f"fly still noclip past pane {i}", flown.get("fly") is True, str(flown.get("fly")))
            await ev(f"{W}.setFly(false)")

        if probes.get("blind"):
            b = probes["blind"][0]
            eye = (b["x"] + b["nx"] * 3.2, b["y"] + b["ny"] * 3.2, b["z"])
            shots.append(await shot("blind_facade", eye, (b["x"], b["y"], b["z"])))
        if probes.get("decal"):
            d = probes["decal"][0]
            eye = (d["x"] + d["nx"] * 2.4, d["y"] + d["ny"] * 2.4, d["z"])
            shots.append(await shot("decal_wall", eye, (d["x"], d["y"], d["z"])))

        check("no page errors", not errs, str(errs[:2]))
        await br.close()

    res = {"PASS": not fails and not errs, "fails": fails, "notes": notes, "shots": shots, "page_errors": errs}
    json.dump(res, open(os.path.join(HERE, "glass_visual_result.json"), "w"), indent=1)
    print("GLASS VISUAL", "PASS" if res["PASS"] else "FAIL", "shots", len(shots), "fails", fails)
    if fails or errs:
        sys.exit(1)


asyncio.run(main())
