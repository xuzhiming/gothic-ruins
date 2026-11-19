"""Alignment sanity scan for the side elevations: IoU vs horizontal scale / shift / vertical scale of the reference mapping
(diagnostic only - the fixed anchors in params.ref_scale are what the scores use).   python3 compare/align_scan.py SIL_DIR"""
import numpy as np, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); SIL = sys.argv[1]
src = open(os.path.join(HERE, "compare.py")).read().split("scores = {}")[0]; sys.argv = [sys.argv[0], SIL, "/tmp/_x"]
G = {"__file__": os.path.join(HERE, "compare.py")}; exec(compile(src, "compare.py", "exec"), G)
from PIL import Image
out = {}
for v in ("west", "east"):
    mm = G["model_mask"](v); u, z = G["grid"](v, mm.shape); mm[z < 0, :] = False
    r = np.asarray(Image.open(os.path.join(HERE, "ref", f"{v}_sil.png"))) > 127; h, w = r.shape
    def iou(sx=1.0, ox=0.0, sz=1.0):
        mx = G["EXT"][v]*sx/w; mz = G["RS"]["H_anchor"]*sz/h; px = (u - ox)/mx + w/2; py = h - z/mz
        PX, PY = np.meshgrid(np.floor(px).astype(int), np.floor(py).astype(int)); ok = (PX >= 0) & (PX < w) & (PY >= 0) & (PY < h)
        rm = np.zeros(mm.shape, bool); rm[ok] = r[PY[ok], PX[ok]]; return (mm & rm).sum()/(mm | rm).sum()
    base = iou(); best = max(((iou(sx, ox, sz), sx, ox, sz) for sx in np.arange(0.88, 1.061, 0.02) for ox in np.arange(-6, 6.1, 1.0) for sz in (0.96, 1.0, 1.04)))
    out[v] = {"anchored": round(base, 4), "best": round(best[0], 4), "best_sx": round(best[1], 2), "best_shift_m": best[2], "best_sz": best[3],
              "shift_only": {f"{o:+.0f}": round(iou(1, o), 4) for o in (-6, -3, 0, 3, 6)}, "scale_only": {f"{s:.2f}": round(iou(s), 4) for s in (0.9, 0.95, 1.0, 1.05)}}
    print(v, out[v])
json.dump(out, open(os.path.join(HERE, "diag", "align_scan.json"), "w"), indent=1)
