"""Walk both ways through NW, NE and W0 street doors after they swing open.
usage: python3 walk/door_timber_test.py --url http://127.0.0.1:8774/index.html
"""
import asyncio, json, math, os, sys
from playwright.async_api import async_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
URL = sys.argv[sys.argv.index("--url") + 1] if "--url" in sys.argv else "http://127.0.0.1:8774/index.html"
S = json.load(open(os.path.join(ROOT, "web", "spaces.json")))
D = {d["id"]: d for d in S["doors"]}
SPC = S["spaces"]
SHOTS = os.path.join(HERE, "door_views")
DOORS = ("NW_door", "NE_door", "W0_door")


def side_points(did, k=1.7):
    d = D[did]
    c, n = d["center"], d["normal"]
    pa = SPC[d["a"]]["probe"]
    s = -1 if ((c[0] - pa[0]) * n[0] + (c[1] - pa[1]) * n[1]) < 0 else 1
    outside = (c[0] - s * n[0] * k, c[1] - s * n[1] * k, c[2])
    inside = (c[0] + s * n[0] * k, c[1] + s * n[1] * k, c[2])
    return outside, inside


def yaw_to(dx, dy):
    return math.atan2(-dx, dy)


async def main():
    os.makedirs(SHOTS, exist_ok=True)
    fails = []

    def check(name, cond, detail=""):
        print(("OK" if cond else "FAIL"), name, detail)
        if not cond:
            fails.append(name if not detail else f"{name}: {detail}")

    async with async_playwright() as p:
        br = await p.chromium.launch(
            executable_path="/usr/bin/google-chrome",
            args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"],
        )
        pg = await br.new_page(viewport={"width": 1100, "height": 700})
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        await pg.goto(URL + ("&" if "?" in URL else "?") + "test=1")
        await pg.wait_for_function("window.__walk && window.__walk.ready", timeout=300000)
        W = "window.__walk"

        async def ev(expr):
            return await pg.evaluate(expr)

        async def st():
            return await ev(f"{W}.state()")

        async def shot(name, eye, target):
            ex, ey, ez = eye
            tx, ty, tz = target
            await ev(f"{W}.lookAt({ex},{ey},{ez},{tx},{ty},{tz}); {W}.setFly(true)")
            await pg.wait_for_timeout(200)
            await ev(f"{W}.render()")
            await pg.screenshot(path=os.path.join(SHOTS, name + ".png"))

        for did in DOORS:
            outside, inside = side_points(did)
            c = D[did]["center"]
            await ev(f"{W}.setFly(false)")
            await ev(f"{W}.teleport({outside[0]},{outside[1]},{outside[2]},0)")
            await pg.wait_for_timeout(200)
            opened = 0
            for _ in range(40):
                doors = await ev(f"{W}.doorsNear(3.2)")
                hit = [d for d in doors if d["id"] == did]
                opened = hit[0]["open"] if hit else 0
                if opened >= 0.9:
                    break
                await pg.wait_for_timeout(100)
            check(f"{did} opens", opened >= 0.9, f"open={opened}")
            await shot(f"{did}_front", (outside[0], outside[1], outside[2] + 1.5), (c[0], c[1], c[2] + 1.3))
            await ev(f"{W}.setFly(false)")
            await ev(f"{W}.teleport({outside[0]},{outside[1]},{outside[2]},0)")
            await pg.keyboard.down("w")
            reached = False
            for _ in range(80):
                s = await st()
                if math.hypot(s["x"] - inside[0], s["y"] - inside[1]) < 0.55 and abs(s["z"] - inside[2]) < 0.5:
                    reached = True
                    break
                await ev(f"{W}.setYaw({yaw_to(inside[0] - s['x'], inside[1] - s['y'])})")
                await pg.wait_for_timeout(80)
            await pg.keyboard.up("w")
            s = await st()
            check(f"{did} in", reached and s.get("fly") is False, f"at {s['x']:.2f},{s['y']:.2f},{s['z']:.2f}")
            await shot(f"{did}_through", (s["x"], s["y"], s["z"] + 1.5), (outside[0], outside[1], outside[2] + 1.2))
            await pg.keyboard.down("w")
            back = False
            for _ in range(80):
                s = await st()
                if math.hypot(s["x"] - outside[0], s["y"] - outside[1]) < 0.7 and abs(s["z"] - outside[2]) < 0.5:
                    back = True
                    break
                await ev(f"{W}.setYaw({yaw_to(outside[0] - s['x'], outside[1] - s['y'])})")
                await pg.wait_for_timeout(80)
            await pg.keyboard.up("w")
            s = await st()
            check(f"{did} out", back, f"at {s['x']:.2f},{s['y']:.2f},{s['z']:.2f}")
            await shot(f"{did}_open", (outside[0], outside[1], outside[2] + 1.5), (c[0], c[1], c[2] + 1.3))
        check("no page errors", not errs, str(errs[:2]))
        await br.close()
    res = {"PASS": not fails and not errs, "fails": fails, "page_errors": errs}
    json.dump(res, open(os.path.join(HERE, "door_timber_result.json"), "w"), indent=1)
    print("DOORS", "PASS" if res["PASS"] else "FAIL", fails)
    if fails or errs:
        sys.exit(1)


asyncio.run(main())
