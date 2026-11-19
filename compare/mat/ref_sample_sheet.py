"""Draw the reference sample rectangles (per material) on the ref panels -> compare/mat/ref_sample_locations_<panel>.png"""
import json, os
from PIL import Image, ImageDraw
H = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(H)); S = json.load(open(os.path.join(H, "ref_samples.json")))
COL = [(255,0,0),(255,128,0),(0,160,255),(255,255,0),(200,0,200),(0,255,0),(0,255,255),(255,0,128),(128,255,128),(255,200,150),(150,80,255),(255,255,255)]
for panel in ("isometric", "front_south"):
    im = Image.open(os.path.join(ROOT, "ref", panel + ".png")).convert("RGB"); k = 2; im = im.resize((im.width*k, im.height*k)); d = ImageDraw.Draw(im)
    for i, (m, s) in enumerate((m, s) for m, s in S.items() if not m.startswith("_")):
        for r in s["rects"].get(panel, []):
            d.rectangle([c*k for c in r], outline=COL[i % len(COL)], width=2); d.text((r[0]*k + 2, r[1]*k - 11), m, fill=COL[i % len(COL)])
    im.save(os.path.join(H, f"ref_sample_locations_{panel}.png"))
