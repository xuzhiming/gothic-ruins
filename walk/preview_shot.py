"""Headless-Chrome screenshots of the three.js preview (optimized GLB: WebP textures + Meshopt): house walls up close.
usage: python3 walk/preview_shot.py [--url http://localhost:8766/index.html]  -> renders/preview_*.png"""
import asyncio, math, os, sys
from playwright.async_api import async_playwright
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = sys.argv[sys.argv.index("--url") + 1] if "--url" in sys.argv else "http://localhost:8766/index.html"
SUFFIX = sys.argv[sys.argv.index("--suffix") + 1] if "--suffix" in sys.argv else ""
SHOTS = [("preview_house_wall_W4", (-16.2, -27.0, 4.2), (-20.4, -27.0)),     # plastered W4 street face (tone A) with brick patches
         ("preview_street_W", (-17.2, -31.0, 4.2), (-19.5, 0.0)),            # up the west street
         ("preview_house_wall_E1", (16.6, 12.0, 4.2), (20.7, 12.0)),         # E1 (tone B, stone GF, half-timber)
         ("preview_nave", (0.0, 7.0, 6.6), (0.0, 40.0)),
         ("preview_plaza", (-7.0, -24.0, 4.2), (0.0, -2.0)),
         ("preview_stairs_south", (5.0, -56.5, 1.7), (0.0, -44.0)),
         ("preview_cathedral_steps", (-2.5, -9.5, 4.2), (0.0, -1.0)),
         ("preview_house_row_E", (-1.0, -24.0, 5.8), (17.0, -8.0))]   # M10: east house row from the plaza         # gap #9: cathedral steps close-up           # gap #9: south monumental stairs from the approach                  # plaza setts, cathedral steps + facade                      # nave looking toward the apse          # E1 (tone B, stone GF, half-timber)
async def main():
    async with async_playwright() as p:
        br = await p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
        pg = await br.new_page(viewport={"width": 1280, "height": 800}); errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
        await pg.goto(URL + "?test=1"); await pg.wait_for_function("window.__walk && window.__walk.ready", timeout=300000)
        for name, (x, y, z), (lx, ly) in SHOTS:
            yaw = math.atan2(-(lx - x), ly - y)
            await pg.evaluate(f"window.__walk.teleport({x},{y},{z},{yaw})"); await pg.wait_for_timeout(600)
            await pg.evaluate("window.__walk.render()"); await pg.screenshot(path=os.path.join(R, "renders", name + SUFFIX + ".png")); print("shot", name)
        await br.close(); print("page errors:", errs or "none")
asyncio.run(main())
