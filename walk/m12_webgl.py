"""gap #12: three.js close-ups of the lime-plaster skin / brick patches / lime residue (optimized GLB) for a model given by
?model=. usage: python3 walk/m12_webgl.py MODEL_URLPATH SUFFIX  -> renders/webgl_m12_<shot><SUFFIX>.png"""
import asyncio, math, os, sys
from playwright.async_api import async_playwright
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL, SUFFIX = sys.argv[1], sys.argv[2]
SHOTS = [("W4_hole", (-18.9, -25.4, 4.2), (-20.35, -22.6)),
         ("W4_end", (-23.4, -35.2, 4.2), (-21.4, -32.9)),
         ("E4_lime", (19.0, -25.6, 4.2), (20.35, -23.0)),
         ("W4_wall", (-16.2, -27.0, 4.2), (-20.4, -27.0)),
         ("W4_far", (6.0, -40.0, 4.2), (-20.4, -27.0)),          # M12b: ~29 m, z-fighting check at distance
         ("NW_far", (-2.0, 20.0, 4.2), (-20.5, 37.0))]           # M12b: NW street face + exposed end from the nave side, ~25 m
async def main():
    async with async_playwright() as p:
        br = await p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
        pg = await br.new_page(viewport={"width": 1100, "height": 760}); errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
        await pg.goto(f"http://localhost:8766/index.html?test=1&model={MODEL}"); await pg.wait_for_function("window.__walk && window.__walk.ready", timeout=300000)
        for name, (x, y, z), (lx, ly) in SHOTS:
            yaw = math.atan2(-(lx - x), ly - y)
            await pg.evaluate(f"window.__walk.teleport({x},{y},{z},{yaw})"); await pg.wait_for_timeout(600)
            await pg.evaluate("window.__walk.render()"); await pg.screenshot(path=os.path.join(R, "renders", f"webgl_m12_{name}{SUFFIX}.png")); print("shot", name)
        await br.close(); print("page errors:", errs or "none")
asyncio.run(main())
