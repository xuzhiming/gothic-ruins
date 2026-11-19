"""Gap #6 sheets: west/east reference | before | after overlays, and the plan: reference | before / after overlay + footprint."""
import os, json
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
BEF, AFT = os.path.join(ROOT, "tmp", "before6", "cmp"), os.path.join(HERE, "out")
SB, SA = json.load(open(os.path.join(BEF, "scores.json"))), json.load(open(os.path.join(AFT, "scores.json")))
def side_panels(p):
    im = Image.open(p); W = (im.width - 32)//3; return [im.crop((8 + i*(W + 8), 0, 8 + i*(W + 8) + W, im.height)) for i in range(3)]
def stack(rows, path):
    W = max(r[1].width for r in rows); H = sum(r[1].height + 26 for r in rows); out = Image.new("RGB", (W, H), "white"); d = ImageDraw.Draw(out); y = 0
    for t, im in rows: d.text((8, y + 7), t, fill=(0, 0, 0)); out.paste(im, (0, y + 26)); y += im.height + 26
    out.save(path); print(path, out.size)
for v in ("west", "east"):
    b, a = side_panels(f"{BEF}/sbs_{v}.png"), side_panels(f"{AFT}/sbs_{v}.png")
    stack([(f"{v} reference", b[0]),
           (f"before (apse centre y 41.0): IoU {SB[v]['iou']:.3f}, skyline MAE {SB[v]['skyline_mae_m']:.2f} m  - grey both, red ref only, blue model only", b[2]),
           (f"after M6 (apse centre y 38.0): IoU {SA[v]['iou']:.3f}, skyline MAE {SA[v]['skyline_mae_m']:.2f} m", a[2])], f"{HERE}/diag/m6_{v}_ref_before_after.png")
def top_panels(p):
    im = Image.open(p); q = im.width//4; return [im.crop((i*q, 0, (i + 1)*q, im.height)) for i in range(4)]
b, a = top_panels(f"{BEF}/sbs_top.png"), top_panels(f"{AFT}/sbs_top.png")
def row(x, y): r = Image.new("RGB", (x.width + y.width, max(x.height, y.height)), "white"); r.paste(x, (0, 0)); r.paste(y, (x.width, 0)); return r
stack([("plan reference (ref/top_plan.png) | model plan render after", row(b[0], a[1])),
       (f"before (apse y 41.0): site overlay IoU {SB['top']['iou']:.3f} | building footprint vs plan IoU {SB['top']['footprint_iou']:.3f}  (red ref only, blue model only)", row(b[2], b[3])),
       (f"after M6 (apse y 38.0): site overlay IoU {SA['top']['iou']:.3f} | building footprint vs plan IoU {SA['top']['footprint_iou']:.3f}", row(a[2], a[3]))], f"{HERE}/diag/m6_top_before_after.png")
