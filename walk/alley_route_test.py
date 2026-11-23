"""Walk the eight new alleys, both rear lanes, the south parapets, and the north returns.
Drives real WASD against window.__walk. Does not change server data.
usage: python3 walk/alley_route_test.py --url http://127.0.0.1:8772/index.html
"""
import asyncio, json, math, os, sys
from playwright.async_api import async_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
URL = sys.argv[sys.argv.index("--url") + 1] if "--url" in sys.argv else "http://127.0.0.1:8772/index.html"
S = json.load(open(os.path.join(ROOT, "web", "spaces.json")))
SHOTS = os.path.join(HERE, "alley_views")


def yaw_to(dx, dy):
    return math.atan2(-dx, dy)


def link(a, b):
    for item in S["open_links"]:
        if item["a"] == a and item["b"] == b:
            return item["path"]
    raise KeyError((a, b))


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

        async def arrive(tx, ty, limit=12):
            await pg.keyboard.down("w")
            best, still = 1e9, 0
            reached = False
            for _ in range(int(limit / 0.08)):
                s = await st()
                dist = math.hypot(tx - s["x"], ty - s["y"])
                if dist < 0.45:
                    reached = True
                    break
                await ev(f"{W}.setYaw({yaw_to(tx - s['x'], ty - s['y'])})")
                if dist < best - 0.05:
                    best, still = dist, 0
                else:
                    still += 1
                    if still > 25:
                        break
                await pg.wait_for_timeout(80)
            await pg.keyboard.up("w")
            s = await st()
            return reached, s

        async def walk_path(name, pts):
            x, y, z = pts[0]
            await ev(f"{W}.teleport({x},{y},{z},0)")
            await pg.wait_for_timeout(200)
            ok = True
            for tx, ty, tz in pts[1:]:
                dist = math.hypot(tx - x, ty - y)
                reached, s = await arrive(tx, ty, limit=max(12, dist / 3.2 + 5))
                x, y = s["x"], s["y"]
                level = abs(s["z"] - tz) < 0.6
                if not (reached and level and s.get("fly") is False):
                    ok = False
                    check(name, False, f"missed {[tx, ty]} at {s['x']:.2f},{s['y']:.2f},{s['z']:.2f}")
                    return
            check(name, ok)

        for side in ("W", "E"):
            for i in range(4):
                aid = f"alley_{side}{i}{i+1}"
                await walk_path(aid + " street-to-mid", link(f"street_{side}", aid))
                await walk_path(aid + " mid-to-rear", link(aid, f"rear_{side}"))
            await walk_path(f"rear_{side}", link(f"rear_{side}", f"turn_{side}"))
            await walk_path(f"turn_{side}", link(f"turn_{side}", f"north_{side}"))

        # South parapet: walk into the closed end and stay on the deck.
        for side, x in (("W", -32.185), ("E", 32.185)):
            await ev(f"{W}.teleport({x},-31.6,4.2,{math.pi})")
            await pg.wait_for_timeout(150)
            await ev(f"{W}.setYaw({math.pi})")
            await pg.keyboard.down("w")
            await pg.wait_for_timeout(1200)
            await pg.keyboard.up("w")
            s = await st()
            blocked = await ev(f"{W}.blocked({x},-32.85,4.2)")
            check(f"south rail {side}", s["y"] > -32.8 and s["y"] < -32.05 and blocked is True and abs(s["z"] - 4.2) < 0.5, f"y={s['y']:.2f} z={s['z']:.2f} blocked={blocked}")

        async def shot(name, eye, target):
            ex, ey, ez = eye
            tx, ty, tz = target
            await ev(f"{W}.lookAt({ex},{ey},{ez},{tx},{ty},{tz}); {W}.setFly(true)")
            await pg.wait_for_timeout(150)
            await ev(f"{W}.render()")
            await pg.screenshot(path=os.path.join(SHOTS, name + ".png"))

        await shot("alley_W01", (-26.0, 17.97, 5.8), (-32.0, 17.97, 5.2))
        await shot("rear_W", (-32.0, 0.0, 5.6), (-32.2, -20.0, 5.0))
        await shot("south_rail_W", (-31.6, -30.2, 5.8), (-32.4, -32.8, 4.6))
        await shot("north_turn_W", (-24.0, 31.3, 6.0), (-32.0, 31.3, 5.0))
        check("no page errors", not errs, str(errs[:2]))
        await br.close()
    res = {"PASS": not fails and not errs, "fails": fails, "page_errors": errs}
    json.dump(res, open(os.path.join(HERE, "alley_route_result.json"), "w"), indent=1)
    print("ALLEY", "PASS" if res["PASS"] else "FAIL", fails)
    if fails or errs:
        sys.exit(1)


asyncio.run(main())
