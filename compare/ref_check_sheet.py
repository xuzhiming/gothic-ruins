"""Side-reference extraction check sheet: ref panel with the extracted mask outline (red), bbox anchors (blue: site extent
left/right, ground line, spire-cross top) and the alignment-scan summary.   python3 compare/ref_check_sheet.py"""
import json, os, numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
RM = json.load(open(os.path.join(HERE, "ref", "ref_measure.json"))); AS = json.load(open(os.path.join(HERE, "diag", "align_scan.json")))
MC = json.load(open(os.path.join(HERE, "diag", "mask_check.json")))
tiles = []
for v, f in (("west", "left_west"), ("east", "right_east")):
    im = Image.open(os.path.join(ROOT, "ref", f + ".png")).convert("RGB"); x0, y0, x1, y1 = RM[v]["bbox_px"]
    m = np.asarray(Image.open(os.path.join(HERE, "ref", v + "_sil.png")).convert("L")) > 127
    full = np.zeros((im.height, im.width), bool); full[y0:y1, x0:x1] = np.asarray(Image.fromarray(m).resize((x1 - x0, y1 - y0), Image.NEAREST))
    edge = full & ~ndi.binary_erosion(full); a = np.asarray(im).copy(); a[ndi.binary_dilation(edge)] = (230, 30, 30)
    im = Image.fromarray(a).resize((im.width*2, im.height*2), Image.LANCZOS); d = ImageDraw.Draw(im)
    for x in (x0, x1): d.line([(2*x, 0), (2*x, im.height)], fill=(30, 80, 230), width=2)
    for y in (y0, y1): d.line([(0, 2*y), (im.width, 2*y)], fill=(30, 80, 230), width=2)
    s = AS[v]; mc = MC[v]
    txt = [f"{v.upper()}: red = extracted silhouette outline, blue = anchors (site extent 101.97 m wide; ground line z0 .. spire-cross tip 41.5 m)",
           f"mask sensitivity IoU: " + ", ".join(f"{k} {r['iou']:.4f}" for k, r in mc.items() if isinstance(r, dict)),
           f"alignment scan (diagnostic only, not applied): anchored {s['anchored']}; best {s['best']} at x-scale {s['best_sx']}, shift {s['best_shift_m']:+.0f} m, z-scale {s['best_sz']} - it slides the ref cathedral off the plaza conflict and the ref plinth ends past the site edge"]
    can = Image.new("RGB", (im.width, im.height + 60), "white"); can.paste(im, (0, 60)); dd = ImageDraw.Draw(can)
    for i, t in enumerate(txt): dd.text((6, 4 + 18*i), t, fill=(0, 0, 0))
    tiles.append(can)
W = max(t.width for t in tiles); out = Image.new("RGB", (W, sum(t.height for t in tiles) + 10), "white"); y = 0
for t in tiles: out.paste(t, (0, y)); y += t.height + 10
out.save(os.path.join(HERE, "diag", "ref_check_sides.png")); print("ok", out.size)
