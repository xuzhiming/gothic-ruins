"""Reference-mask sensitivity for the side elevations: re-extract with other thresholds / morphology and score against the same
model silhouettes (diagnostic).   python3 compare/mask_check.py SIL_DIR"""
import numpy as np, json, os, sys
from PIL import Image
from scipy import ndimage as ndi
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); SIL = sys.argv[1]
src = open(os.path.join(HERE, "compare.py")).read().split("scores = {}")[0]; sys.argv = [sys.argv[0], SIL, "/tmp/_x"]
G = {"__file__": os.path.join(HERE, "compare.py")}; exec(compile(src, "compare.py", "exec"), G)
F = {"west": "left_west", "east": "right_east"}; out = {}
def extract(f, thr, sat_t, close_it, fill=True):
    rgb = np.asarray(Image.open(os.path.join(ROOT, "ref", f + ".png")).convert("RGB")).astype(float)
    B = 4; rgb[:B] = rgb[-B:] = 226; rgb[:, :B] = rgb[:, -B:] = 226
    paper = np.median(rgb[B:B+20, B:-B].reshape(-1, 3), 0); d = np.abs(rgb - paper).max(2); sat = rgb.max(2) - rgb.min(2)
    m = (d > thr) | (sat > sat_t)
    if close_it: m = ndi.binary_closing(m, np.ones((5, 5)), iterations=close_it)
    m = ndi.binary_opening(m, np.ones((3, 3))); lab, n = ndi.label(m); sizes = ndi.sum(m, lab, range(1, n + 1))
    m = np.isin(lab, 1 + np.where(sizes >= 0.02*sizes.max())[0])
    if fill: m = ndi.binary_fill_holes(m)
    return m, paper
for v, f in F.items():
    mm = G["model_mask"](v); u, z = G["grid"](v, mm.shape); mm[z < 0, :] = False
    x0, y0, x1, y1 = G["RM"][v]["bbox_px"]; res = {}
    for name, a in (("used: d>22|sat>18, close 2", (22, 18, 2)), ("looser d>14|sat>12", (14, 12, 2)), ("stricter d>32|sat>26", (32, 26, 2)), ("no closing", (22, 18, 0))):
        m, paper = extract(f, *a)
        ys, xs = np.where(m); bb = [int(xs.min()), int(ys.min()), int(xs.max() + 1), int(ys.max() + 1)]
        r = m[y0:y1, x0:x1]; h, w = r.shape   # keep the fixed anchors (bbox of the used mask) so only the mask content changes
        mx = G["EXT"][v]/w; mz = G["RS"]["H_anchor"]/h; px = u/mx + w/2; py = h - z/mz
        PX, PY = np.meshgrid(np.floor(px).astype(int), np.floor(py).astype(int)); ok = (PX >= 0) & (PX < w) & (PY >= 0) & (PY < h)
        rm = np.zeros(mm.shape, bool); rm[ok] = r[PY[ok], PX[ok]]
        res[name] = {"bbox_px": bb, "ref_area_m2": round(float(rm.sum()*G["MPP"]**2), 1), "iou": round(float((mm & rm).sum()/(mm | rm).sum()), 4)}
    res["paper_rgb"] = [round(float(c), 1) for c in paper]
    out[v] = res; print(v, json.dumps(res))
json.dump(out, open(os.path.join(HERE, "diag", "mask_check.json"), "w"), indent=1)
