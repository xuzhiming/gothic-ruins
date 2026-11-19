"""gap #8: L* spread table (IQR p25-p75 and p10-p90) per material: reference samples vs our neutral renders (frozen gain applied).
  python3 compare/mat/spread.py LABEL=DIR ...  -> table + compare/mat/spread.json"""
import json, os, sys, numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage.color import rgb2lab
H = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(H)); S = json.load(open(os.path.join(H, "ref_samples.json")))
CATS = {"stone_cathedral": (255, 0, 0), "slate": (0, 0, 255), "plaster": (255, 255, 0), "brick": (255, 0, 255), "timber": (0, 255, 0),
        "stone_plinth": (0, 255, 255), "plinth_rock": (128, 64, 0), "cobble": (128, 128, 128), "stair": (255, 128, 0), "chimney": (128, 0, 0), "iron": (0, 0, 128)}
srgb = lambda c: np.where(c/255 <= 0.0031308, 12.92*c/255, 1.055*(c/255)**(1/2.4) - 0.055)*255
G = json.load(open(os.path.join(H, "gain.json")))["gain_linear"]
def sp(px):
    L = rgb2lab(px[None]/255.0)[0][:, 0]; q = np.percentile(L, [10, 25, 75, 90]); return [round(float(q[2] - q[1]), 1), round(float(q[3] - q[0]), 1)]
out = {"ref": {}}
for m in CATS:
    allpx = []
    for panel, rects in S[m]["rects"].items():
        im = np.asarray(Image.open(os.path.join(ROOT, "ref", panel + ".png")).convert("RGB")).astype(float); paper = np.median(im[4:24, 4:-4].reshape(-1, 3), 0)
        for (x0, y0, x1, y1) in rects:
            p = im[y0:y1, x0:x1].reshape(-1, 3); allpx.append(p[np.abs(p - paper).max(1) > 14])
    out["ref"][m] = sp(np.concatenate(allpx))
for arg in sys.argv[1:]:
    lab, d = arg.split("="); a = np.asarray(Image.open(os.path.join(d, "neutral.png")).convert("RGB")).astype(float)
    a = np.clip(255*(((a/255.0)**2.2)*G)**(1/2.2), 0, 255); mid = np.asarray(Image.open(os.path.join(d, "matid.png")).convert("RGB")).astype(int); out[lab] = {}
    for m, c in CATS.items():
        mask = ndi.binary_erosion(np.abs(mid - srgb(np.array(c, float)).round()).max(2) <= 3, iterations=1); out[lab][m] = sp(a[mask])
json.dump(out, open(os.path.join(H, "spread.json"), "w"), indent=1)
labs = list(out); print(f"{'material':16s}" + "".join(f"{l+' IQR/p10-90':>22s}" for l in labs))
for m in CATS: print(f"{m:16s}" + "".join(f"{str(out[l][m][0])+' / '+str(out[l][m][1]):>22s}" for l in labs))
