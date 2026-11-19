"""Gap #8: colour of our BEAUTY render (no gain: lighting/exposure are what is being tuned) vs the reference isometric.
  python3 compare/mat/beauty_compare.py RENDER.png MATID.png TAG   -> compare/mat/beauty_TAG.json + table
Per material: median colour of the eroded matid mask (ours) vs the ref_samples.json statistic (same as mat_compare.py) -> dE00.
Whole building: ref = all non-paper pixels of ref/isometric.png, ours = all non-background matid pixels; mean / median Lab,
white balance = mean a*, b*; overall dE00 of the mean colours. Spread = L* IQR (p25-p75) and p10-p90."""
import json, os, sys, numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage.color import rgb2lab, deltaE_ciede2000
H = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(H))
RP, MP, TAG = sys.argv[1:4]; S = json.load(open(os.path.join(H, "ref_samples.json")))
CATS = {"stone_cathedral": (255, 0, 0), "slate": (0, 0, 255), "plaster": (255, 255, 0), "brick": (255, 0, 255), "timber": (0, 255, 0),
        "stone_plinth": (0, 255, 255), "plinth_rock": (128, 64, 0), "cobble": (128, 128, 128), "stair": (255, 128, 0), "chimney": (128, 0, 0), "iron": (0, 0, 128)}
srgb = lambda c: np.where(c/255 <= 0.0031308, 12.92*c/255, 1.055*(c/255)**(1/2.4) - 0.055)*255
def lab(px): return rgb2lab(np.asarray(px, float)[None]/255.0)[0]
def stat(px, kind="median"):
    L = lab(px)[:, 0]
    sel = L <= np.percentile(L, 15) if kind == "dark" else (L >= np.percentile(L, 85) if kind == "light" else np.ones(len(px), bool))
    med = np.median(px[sel], 0); l = lab(med[None])[0]
    p = lambda q: float(np.percentile(L, q))
    return {"rgb": [round(float(v), 1) for v in med], "lab": [round(float(v), 2) for v in l], "IQR": round(p(75) - p(25), 1), "P1090": round(p(90) - p(10), 1)}
REF = {}
for m, s in S.items():
    if m.startswith("_") or m not in CATS: continue
    allpx = []
    for panel, rects in s["rects"].items():
        im = np.asarray(Image.open(os.path.join(ROOT, "ref", panel + ".png")).convert("RGB")).astype(float); paper = np.median(im[4:24, 4:-4].reshape(-1, 3), 0)
        for (x0, y0, x1, y1) in rects:
            p = im[y0:y1, x0:x1].reshape(-1, 3); allpx.append(p[np.abs(p - paper).max(1) > 14])
    REF[m] = stat(np.concatenate(allpx), s["stat"])
ri = np.asarray(Image.open(os.path.join(ROOT, "ref", "isometric.png")).convert("RGB")).astype(float); paper = np.median(ri[4:24, 4:-4].reshape(-1, 3), 0)
rbm = ndi.binary_erosion(np.abs(ri - paper).max(2) > 18, iterations=2); rb = ri[rbm]
im = Image.open(RP).convert("RGB"); mi = Image.open(MP).convert("RGB")
if mi.size != im.size: mi = mi.resize(im.size, Image.NEAREST)
a = np.asarray(im).astype(float); mid = np.asarray(mi).astype(int)
ob = a[ndi.binary_erosion(np.abs(mid - 255).max(2) > 6, iterations=2)]
def whole(px):
    L = lab(px); m = L.mean(0); return {"mean_lab": [round(float(v), 2) for v in m], "median_L": round(float(np.median(L[:, 0])), 1),
        "IQR_L": round(float(np.percentile(L[:, 0], 75) - np.percentile(L[:, 0], 25)), 1), "P1090_L": round(float(np.percentile(L[:, 0], 90) - np.percentile(L[:, 0], 10)), 1)}
res = {"whole": {"ref": whole(rb), "ours": whole(ob)}, "materials": {}}
res["whole"]["dE00_mean"] = round(float(deltaE_ciede2000(np.array(res["whole"]["ref"]["mean_lab"]), np.array(res["whole"]["ours"]["mean_lab"]))), 2)
for m, c in CATS.items():
    mask = ndi.binary_erosion(np.abs(mid - srgb(np.array(c, float)).round()).max(2) <= 3, iterations=1)
    if mask.sum() < 20: continue
    o = stat(a[mask]); r = REF[m]
    res["materials"][m] = {"ref": r, "ours": o, "dE2000": round(float(deltaE_ciede2000(np.array(r["lab"]), np.array(o["lab"]))), 2)}
res["mean_dE00"] = round(float(np.mean([v["dE2000"] for v in res["materials"].values()])), 2)
json.dump(res, open(os.path.join(H, f"beauty_{TAG}.json"), "w"), indent=1)
w = res["whole"]; print("whole building  ref Lab", w["ref"]["mean_lab"], "ours", w["ours"]["mean_lab"], "dE00", w["dE00_mean"],
    "| IQR L ref/ours", w["ref"]["IQR_L"], w["ours"]["IQR_L"])
for m, v in res["materials"].items():
    print(f"{m:16s} ref {str(tuple(int(x) for x in v['ref']['rgb'])):>16s} ours {str(tuple(int(x) for x in v['ours']['rgb'])):>16s} dE00 {v['dE2000']:5.1f}  dL {v['ours']['lab'][0]-v['ref']['lab'][0]:6.1f} db {v['ours']['lab'][2]-v['ref']['lab'][2]:5.1f}")
print("mean dE00 under beauty light", res["mean_dE00"])
