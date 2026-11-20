"""M12: headless-Chrome screenshot of web/_relief.html (test wall GLB under a grazing light). usage: relief_shot.py GLB_URLPATH OUT.png [extra query]"""
import asyncio, sys
from playwright.async_api import async_playwright
async def main():
    glb, out = sys.argv[1], sys.argv[2]; extra = sys.argv[3] if len(sys.argv) > 3 else ""
    async with async_playwright() as p:
        br = await p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
        pg = await br.new_page(viewport={"width": 900, "height": 900}); errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
        await pg.goto(f"http://localhost:8766/_relief.html?glb={glb}&{extra}"); await pg.wait_for_function("window.__done", timeout=120000); await pg.wait_for_timeout(300)
        await pg.locator("canvas").screenshot(path=out); print("SHOT", out, await pg.title(), errs or "")
        await br.close()
asyncio.run(main())
