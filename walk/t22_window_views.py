"""Fixed-window screenshots for the t22 asset. Client only; does not write to the server.
usage: python3 walk/t22_window_views.py --url URL --out DIR
"""
import asyncio, os, sys
from playwright.async_api import async_playwright

URL = sys.argv[sys.argv.index("--url") + 1]
OUT = sys.argv[sys.argv.index("--out") + 1]
# Blender coordinates from window-audit view_center / outward normal (0, -1, 0).
VIEWS = [
    ("rose_out_far", (0.0, -12.0, 14.0), (0.0, 3.9, 21.1)),
    ("rose_out_near", (0.0, 0.4, 20.6), (0.0, 3.9, 21.1)),
    ("rose_in", (0.0, 12.0, 16.5), (0.0, 3.9, 21.1)),
    ("rose_in_up", (0.0, 8.2, 20.5), (0.0, 3.9, 21.15)),
    ("nw_dormer_out_far", (-20.56, 27.5, 9.5), (-20.56, 37.48, 12.10)),
    ("nw_dormer_out_near", (-20.56, 35.3, 12.05), (-20.56, 37.48, 12.10)),
    ("nw_dormer_in", (-20.56, 41.2, 11.7), (-20.56, 37.48, 12.10)),
]


async def main():
    os.makedirs(OUT, exist_ok=True)
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
        for name, eye, target in VIEWS:
            ex, ey, ez = eye
            tx, ty, tz = target
            await pg.evaluate(f"window.__walk.lookAt({ex},{ey},{ez},{tx},{ty},{tz}); window.__walk.setFly(true)")
            await pg.wait_for_timeout(150)
            await pg.evaluate("window.__walk.render()")
            path = os.path.join(OUT, name + ".png")
            await pg.screenshot(path=path)
            print("SHOT", path)
        await br.close()
    if errs:
        print("PAGE_ERRORS", errs[:3])
        sys.exit(1)


asyncio.run(main())
