"""Side-elevation diagnosis (west/east): per-column FP/FN overlay with skylines + zone breakdown of the IoU loss, extraction checks.
   python3 compare/diag_side.py SIL_DIR OUT_DIR [TAG]
Zones are defined in plan coordinates (y, z) and mapped to u per view (west: u = -y, east: u = +y), so ref and model share them.
IoU loss = (FP + FN) / union; each zone's share = (FP_z + FN_z) / union (shares sum to 1 - IoU)."""
import numpy as np, json, os, sys
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.argv += [] 
SIL, OUT = sys.argv[1], sys.argv[2]; TAG = sys.argv[3] if len(sys.argv) > 3 else ""; os.makedirs(OUT, exist_ok=True)
sys.argv = [sys.argv[0], SIL, os.path.join(OUT, "_cmp")]
import importlib.util
P = json.load(open(os.environ.get("PARAMS", os.path.join(ROOT, "params.json")))); RS = P["ref_scale"]
META = json.load(open(os.path.join(SIL, "sil_meta.json"))); MPP = META["mpp"]; G0 = META["ground_from_bottom_m"]
spec = importlib.util.spec_from_file_location("cmpmod", os.path.join(HERE, "compare.py"))
src = open(os.path.join(HERE, "compare.py")).read().split("scores = {}")[0]   # reuse the exact mapping functions of compare.py
G = {"__file__": os.path.join(HERE, "compare.py")}; exec(compile(src, "compare.py", "exec"), G)
PZ = P["site"]["plaza_z"]; C = P["cathedral"]; HS = P["houses"]; ZH = 17.5
ry0, ry1 = HS["row_y"]; yF, yB = C["y_front"], C["y_back"]; yT = C["tower_sw"]["y"][1]
ZONES = [  # name, y0, y1, z0, z1
    ("plinth / stairs (z<4.4)", -99, 99, -1, 4.4),
    ("houses band (row, 4.4-17.5 m)", ry0, ry1, 4.4, ZH),
    ("north end low (corner houses, chevet base)", ry1, 99, 4.4, ZH),
    ("south end (terrace, balustrades, stairs)", -99, ry0, 4.4, 99),
    ("over the plaza (ref draws cathedral, plan: plaza) z>17.5", ry0, yF, ZH, 99),
    ("towers / spire bay z>17.5", yF, yT, ZH, 99),
    ("nave z>17.5", yT, yB, ZH, 99),
    ("apse / chevet z>17.5", yB, 99, ZH, 99)]
COLS = [(120, 120, 120), (200, 170, 90), (150, 110, 60), (90, 160, 90), (220, 60, 160), (60, 160, 220), (90, 90, 200), (180, 90, 200)]
res = {}
for v in ("west", "east"):
    mm = G["model_mask"](v); u, z = G["grid"](v, mm.shape); mm[z < 0, :] = False; rm = G["ref_mask"](v, mm.shape)
    H, W = mm.shape; y = -u if v == "west" else u
    YY = np.repeat(y[None, :], H, 0); ZZ = np.repeat(z[:, None], W, 1)
    fp, fn, both = mm & ~rm, rm & ~mm, mm & rm; uni = (mm | rm).sum(); iou = both.sum()/uni
    zr = []
    for (nm, y0, y1, z0, z1) in ZONES:
        sel = (YY >= y0) & (YY < y1) & (ZZ >= z0) & (ZZ < z1)
        zr.append({"zone": nm, "FP_m2": round(float((fp & sel).sum()*MPP*MPP), 1), "FN_m2": round(float((fn & sel).sum()*MPP*MPP), 1),
                   "iou_loss": round(float(((fp | fn) & sel).sum()/uni), 4), "ref_m2": round(float((rm & sel).sum()*MPP*MPP), 1), "model_m2": round(float((mm & sel).sum()*MPP*MPP), 1)})
    # ceiling: IoU if the plaza-zone conflict did not exist (both masks cleared there)
    sel = (YY >= ry0) & (YY < yF) & (ZZ >= ZH); m2, r2 = mm & ~sel, rm & ~sel
    res[v] = {"iou": round(float(iou), 4), "union_m2": round(float(uni*MPP*MPP), 1), "FP_m2": round(float(fp.sum()*MPP*MPP), 1), "FN_m2": round(float(fn.sum()*MPP*MPP), 1),
              "zones": zr, "iou_without_plaza_zone": round(float((m2 & r2).sum()/(m2 | r2).sum()), 4)}
    # ---- overlay image + per-column bars
    S = 3 if MPP >= 0.2 else 1
    ov = np.full((H, W, 3), 255, np.uint8); ov[both] = (170, 170, 170); ov[fn] = (230, 60, 50); ov[fp] = (40, 130, 235)
    sk = lambda m: np.where(m.any(0), np.argmax(m, 0), -1)
    for s_, c in ((sk(rm), (150, 0, 0)), (sk(mm), (0, 50, 170))):
        for i, r_ in enumerate(s_):
            if r_ >= 0: ov[max(0, r_ - 1):r_ + 2, i] = c
    gr = int(round(H - G0/MPP)); ov[gr, :] = 0
    bh = 160; bars = np.full((bh, W, 3), 255, np.uint8)
    fpc, fnc = fp.sum(0)*MPP, fn.sum(0)*MPP; sc_ = (bh/2 - 4)/max(20.0, fpc.max(), fnc.max())
    for i in range(W):
        a = int(fnc[i]*sc_); b = int(fpc[i]*sc_); bars[bh//2 - a:bh//2, i] = (230, 60, 50); bars[bh//2:bh//2 + b, i] = (40, 130, 235)
    bars[bh//2, :] = 0
    zb = np.full((22, W, 3), 255, np.uint8)
    for k, (nm, y0, y1, z0, z1) in enumerate(ZONES):   # zone strip (u extents of the y-defined zones, upper zones only)
        if z0 < ZH - 1: continue
        cs = (y >= y0) & (y < y1); zb[:, cs] = COLS[k]
    img = Image.new("RGB", (W + 20, H + bh + 22 + 190), (255, 255, 255)); img.paste(Image.fromarray(ov), (10, 30)); img.paste(Image.fromarray(zb), (10, 30 + H)); img.paste(Image.fromarray(bars), (10, 52 + H))
    d = ImageDraw.Draw(img)
    d.text((10, 4), f"{v.upper()} {TAG}: IoU {iou:.3f}   grey = both, red = ref only (FN), blue = model only (FP); dark red / dark blue lines = ref / model skyline;"
                    f" u = {'-y (north left)' if v == 'west' else '+y (south left)'}; grid 10 m", fill=0)
    for gu in np.arange(-60, 61, 10):
        c = int(round((gu - u[0])/MPP)) + 10
        if 10 <= c < W + 10: d.line([(c, 30 + H - 6), (c, 30 + H)], fill=0); d.text((c - 8, 30 + H + 24 + bh), f"{gu:+d}", fill=0)
    d.text((10, 52 + H + bh + 16), "bars: metres of FN (up, red) / FP (down, blue) per column    zone strip (upper zones): " +
           ", ".join(nm.split(" z>")[0].split(" (")[0] for nm, *_r, z0, z1 in [(z_[0], z_[1], z_[2], z_[3], z_[4]) for z_ in ZONES] if z0 >= ZH - 1), fill=0)
    yy = 52 + H + bh + 34
    for k, zr_ in enumerate(zr):
        d.rectangle([10, yy + 13*k, 20, yy + 13*k + 9], fill=COLS[k]); d.text((26, yy + 13*k - 1), f"{zr_['zone']}: FN {zr_['FN_m2']} m2, FP {zr_['FP_m2']} m2 -> IoU loss {zr_['iou_loss']:.3f}", fill=0)
    if S > 1: img = img.resize((img.width*S//2, img.height*S//2), Image.LANCZOS)
    img.save(os.path.join(OUT, f"diag_{v}{('_' + TAG) if TAG else ''}.png"))
json.dump(res, open(os.path.join(OUT, f"diag{('_' + TAG) if TAG else ''}.json"), "w"), indent=1)
for v, r in res.items():
    print(f"{v}: IoU {r['iou']}  FP {r['FP_m2']} FN {r['FN_m2']} union {r['union_m2']}  (without plaza-zone conflict: {r['iou_without_plaza_zone']})")
    for zr_ in r["zones"]: print(f"   {zr_['zone']:<58} FN {zr_['FN_m2']:7.1f}  FP {zr_['FP_m2']:7.1f}  loss {zr_['iou_loss']:.3f}")
