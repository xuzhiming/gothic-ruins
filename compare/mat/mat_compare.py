"""Per-material colour comparison: reference samples (ref_samples.json rectangles) vs our neutral render (matid category masks).
  python3 compare/mat/mat_compare.py RENDER_DIR TAG      -> compare/mat/mat_TAG.json (+ prints a table)
Colour of a sample = median (ref: or dark / light percentile where the ref rectangle mixes materials, see ref_samples.json; ours: masks are pure, always median) in sRGB -> CIE Lab (D65). dE = CIEDE2000.
Our side: pixels of the category mask (eroded 1 px against edges), same statistic. One global gain (compare/mat/gain.json) is
fitted ONCE on the 'before' state (median luminance ratio ref/ours over all categories) and then frozen, so it only removes the
unknown lighting/exposure scale of the AI render, never per-material differences."""
import json, os, sys, numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage.color import rgb2lab, deltaE_ciede2000
H = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(H))
RD, TAG = sys.argv[1], sys.argv[2]; S = json.load(open(os.path.join(H, "ref_samples.json")))
sys.argv = [sys.argv[0]]; import importlib.util
spec = importlib.util.spec_from_file_location("rm", os.path.join(H, "render_mat.py"))
CATS = {"stone_cathedral": (255, 0, 0), "slate": (0, 0, 255), "plaster": (255, 255, 0), "brick": (255, 0, 255), "timber": (0, 255, 0),
        "stone_plinth": (0, 255, 255), "plinth_rock": (128, 64, 0), "cobble": (128, 128, 128), "stair": (255, 128, 0), "chimney": (128, 0, 0), "iron": (0, 0, 128)}
def srgb(c):
    c = c/255.0; return np.where(c <= 0.0031308, 12.92*c, 1.055*c**(1/2.4) - 0.055)*255
def stat(px, kind):
    if len(px) < 20: return None
    L = rgb2lab(px[None]/255.0)[0][:, 0]
    if kind == "dark": sel = L <= np.percentile(L, 15)
    elif kind == "light": sel = L >= np.percentile(L, 85)
    else: sel = np.ones(len(px), bool)
    p = px[sel]; med = np.median(p, 0)
    lab = rgb2lab(med[None, None]/255.0)[0, 0]
    return {"rgb": [round(float(v), 1) for v in med], "lab": [round(float(v), 2) for v in lab], "L_p25": round(float(np.percentile(L, 25)), 1),
            "L_p75": round(float(np.percentile(L, 75)), 1), "n": int(len(px))}
# reference
REF = {}
for m, s in S.items():
    if m.startswith("_"): continue
    allpx = []
    for panel, rects in s["rects"].items():
        im = np.asarray(Image.open(os.path.join(ROOT, "ref", panel + ".png")).convert("RGB")).astype(float)
        paper = np.median(im[4:24, 4:-4].reshape(-1, 3), 0)
        for (x0, y0, x1, y1) in rects:
            p = im[y0:y1, x0:x1].reshape(-1, 3); keep = np.abs(p - paper).max(1) > 14; allpx.append(p[keep])
    REF[m] = stat(np.concatenate(allpx), s["stat"])
REF["stone_cathedral_buttress"] = None
# ours
nim = np.asarray(Image.open(os.path.join(RD, "neutral.png")).convert("RGB")).astype(float)
mid = np.asarray(Image.open(os.path.join(RD, "matid.png")).convert("RGB")).astype(int)
gp = os.path.join(H, "gain.json")
OURS_RAW = {}; MASKS = {}
for m, c in CATS.items():
    e = srgb(np.array(c, float)).round()
    mask = (np.abs(mid - e).max(2) <= 3); mask = ndi.binary_erosion(mask, iterations=1)
    OURS_RAW[m] = nim[mask]; MASKS[m] = mask
OURS_RAW["house_walls"] = nim[MASKS["plaster"] | MASKS["brick"] | MASKS["timber"]]   # overall wall tone (union), not graded on
if not os.path.exists(gp):   # fit once (before state): luminance gain in linear light
    lin = lambda v: (np.asarray(v)/255.0)**2.2
    r = [np.median(lin(np.array(REF[m]["rgb"])).mean()/max(1e-6, lin(np.median(OURS_RAW[m], 0)).mean())) for m in CATS if REF.get(m) and len(OURS_RAW[m]) > 50]
    json.dump({"gain_linear": float(np.median(r)), "_doc": "global exposure gain fitted on the BEFORE state (median over categories), frozen"}, open(gp, "w"), indent=1)
G = json.load(open(gp))["gain_linear"]
res = {"gain_linear": G, "materials": {}}
for m in list(CATS) + ["house_walls"]:
    px = OURS_RAW[m]
    pxg = np.clip(255*(((px/255.0)**2.2)*G)**(1/2.2), 0, 255) if len(px) else px
    o = stat(pxg, "median") if len(px) else None; r = REF[m]   # our masks are pure material -> always the median
    de = float(deltaE_ciede2000(np.array(r["lab"]), np.array(o["lab"]))) if o else None
    res["materials"][m] = {"ref": r, "ours": o, "dE2000": round(de, 2) if de is not None else None,
                           "dL": round(o["lab"][0] - r["lab"][0], 1) if o else None, "contrast_ref_IQR_L": round(r["L_p75"] - r["L_p25"], 1),
                           "contrast_ours_IQR_L": round(o["L_p75"] - o["L_p25"], 1) if o else None}
json.dump(res, open(os.path.join(H, f"mat_{TAG}.json"), "w"), indent=1)
print(f"{'material':16s} {'ref rgb':>18s} {'ours rgb':>18s}  dE00   dL  IQR ref/ours  (gain {G:.3f})")
for m, v in res["materials"].items():
    if v["ours"] is None: print(m, "no pixels"); continue
    print(f"{m:16s} {str(tuple(int(x) for x in v['ref']['rgb'])):>18s} {str(tuple(int(x) for x in v['ours']['rgb'])):>18s} {v['dE2000']:5.1f} {v['dL']:5.1f}  {v['contrast_ref_IQR_L']:4.1f}/{v['contrast_ours_IQR_L']:4.1f}")
print("mean dE00 (11 materials)", round(float(np.mean([v["dE2000"] for k, v in res["materials"].items() if v["dE2000"] is not None and k != "house_walls"])), 2))
