"""Silhouette comparison: model ortho renders (known m/px) vs reference panels aligned to metres.
   python3 compare/compare.py SIL_DIR OUT_DIR [--sbs]
Reference -> metres (params.json:ref_scale, never tuned):
  elevations: horizontal: panel bbox width == site extent from the plan (W for south/north, D for west/east), bbox centre == site centre;
              vertical: bbox bottom == ground line (z=0), bbox top == spire-cross tip (H_anchor)
  plan: isotropic plan_mpp about plan_center_px (north up).
Scores per view: IoU of silhouettes; skyline (top-edge) error = mean |z_model - z_ref| over columns where either has content;
plan view: IoU + mean outline distance. Writes OUT_DIR/scores.json (+ side-by-side PNGs with --sbs)."""
import numpy as np, json, os, sys
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
SIL, OUT = sys.argv[1], sys.argv[2]; SBS = "--sbs" in sys.argv; os.makedirs(OUT, exist_ok=True)
P = json.load(open(os.environ.get("PARAMS", os.path.join(ROOT, "params.json")))); RS = P["ref_scale"]
META = json.load(open(os.path.join(SIL, "sil_meta.json"))); MPP = META["mpp"]; G0 = META["ground_from_bottom_m"]
RM = json.load(open(os.path.join(HERE, "ref", "ref_measure.json")))
EXT = {"south": RS["site_W"], "north": RS["site_W"], "west": RS["site_D"], "east": RS["site_D"]}

def model_mask(v):
    return np.asarray(Image.open(os.path.join(SIL, f"sil_{v}.png")).convert("RGBA"))[..., 3] > 40
def grid(v, shape):
    fw, fh = META["views"][v]["frame_w"], META["views"][v]["frame_h"]; H, W = shape
    u = (np.arange(W) + 0.5)*MPP - fw/2
    if v == "top": z = fh/2 - (np.arange(H) + 0.5)*MPP
    else: z = (H - np.arange(H) - 0.5)*MPP - G0
    return u, z
def ref_mask(v, shape):
    r = np.asarray(Image.open(os.path.join(HERE, "ref", f"{v}_sil.png"))) > 127; h, w = r.shape
    u, z = grid(v, shape)
    if v == "top":
        x0, y0 = RM["top"]["bbox_px"][:2]; cx, cy = RS["plan_center_px"]; m = RS["plan_mpp"]
        px = (u/m + cx - x0); py = (cy - z/m - y0)
    else:
        mx = EXT[v]/w; mz = RS["H_anchor"]/h
        px = u/mx + w/2; py = h - z/mz
    PX, PY = np.meshgrid(np.floor(px).astype(int), np.floor(py).astype(int))
    ok = (PX >= 0) & (PX < w) & (PY >= 0) & (PY < h)
    out = np.zeros(shape, bool); out[ok] = r[PY[ok], PX[ok]]
    return out
def ref_rgb(v, shape):
    im = np.asarray(Image.open(os.path.join(HERE, "ref", f"{v}_crop.png")).convert("RGB")); h, w = im.shape[:2]
    u, z = grid(v, shape)
    if v == "top":
        x0, y0 = RM["top"]["bbox_px"][:2]; cx, cy = RS["plan_center_px"]; m = RS["plan_mpp"]; px = (u/m + cx - x0); py = (cy - z/m - y0)
    else:
        mx = EXT[v]/w; mz = RS["H_anchor"]/h; px = u/mx + w/2; py = h - z/mz
    PX, PY = np.meshgrid(np.floor(px).astype(int), np.floor(py).astype(int))
    ok = (PX >= 0) & (PX < w) & (PY >= 0) & (PY < h)
    out = np.full(shape + (3,), 255, np.uint8); out[ok] = im[PY[ok], PX[ok]]
    return out
def skyline(m, z):
    has = m.any(0); top = np.argmax(m, 0)
    return np.where(has, z[top], np.nan)

scores = {}
for v in ("south", "north", "west", "east", "top"):
    mm = model_mask(v); u, z = grid(v, mm.shape)
    if v != "top": mm[z < 0, :] = False
    rm = ref_mask(v, mm.shape)
    inter, uni = (mm & rm).sum(), (mm | rm).sum(); iou = float(inter/max(uni, 1))
    s = {"iou": round(iou, 4), "model_area_m2": round(float(mm.sum()*MPP*MPP), 1), "ref_area_m2": round(float(rm.sum()*MPP*MPP), 1)}
    if v != "top":
        sm, sr = skyline(mm, z), skyline(rm, z)
        both = ~np.isnan(sm) | ~np.isnan(sr)
        d = np.where(np.isnan(sm), 0, sm) - np.where(np.isnan(sr), 0, sr)
        s["skyline_mae_m"] = round(float(np.abs(d[both]).mean()), 3)
        s["skyline_rmse_m"] = round(float(np.sqrt((d[both]**2).mean())), 3)
        s["skyline_model"] = [None if np.isnan(x) else round(float(x), 2) for x in sm]
        s["skyline_ref"] = [None if np.isnan(x) else round(float(x), 2) for x in sr]
        s["u"] = [round(float(x), 2) for x in u]
        hm = np.where(mm.any(1))[0]; hr = np.where(rm.any(1))[0]
        s["height_model_m"] = round(float(z[hm[0]]), 2) if len(hm) else 0; s["height_ref_m"] = round(float(z[hr[0]]), 2) if len(hr) else 0
    else:
        em = mm ^ ndi.binary_erosion(mm); er = rm ^ ndi.binary_erosion(rm)
        dt_r = ndi.distance_transform_edt(~er)*MPP; dt_m = ndi.distance_transform_edt(~em)*MPP
        s["outline_dist_m"] = round(float((dt_r[em].mean() + dt_m[er].mean())/2), 3)
        # building footprint score vs the footprints read off the plan (compare/ref/top_footprint_px.json)
        FP = json.load(open(os.path.join(HERE, "ref", "top_footprint_px.json"))); cx, cy = RS["plan_center_px"]; m = RS["plan_mpp"]
        UU, ZZ = np.meshgrid(u, z); px = UU/m + cx; py = cy - ZZ/m; fr = np.zeros(mm.shape, bool)
        for (a, b, c, d) in FP["rects"]: fr |= (px >= a) & (px <= c) & (py >= b) & (py <= d)
        for (a, b, r) in FP["circles"]: fr |= (px - a)**2 + (py - b)**2 <= r*r
        fm = np.asarray(Image.open(os.path.join(SIL, "sil_foot.png")).convert("RGBA"))[..., 3] > 40
        s["footprint_iou"] = round(float((fm & fr).sum()/max((fm | fr).sum(), 1)), 4)
        FOOT = (fm, fr)
    scores[v] = s
    if SBS:
        H, W = mm.shape
        rgb = ref_rgb(v, mm.shape)
        sh = os.path.join(SIL, f"shaded_{v}.png")
        if os.path.exists(sh):
            a = np.asarray(Image.open(sh).convert("RGBA")).astype(float); al = a[..., 3:4]/255
            mod = (a[..., :3]*al + 255*(1 - al)).astype(np.uint8)
        else: mod = np.where(mm[..., None], 60, 255).astype(np.uint8).repeat(3, 2)
        ov = np.full((H, W, 3), 255, np.uint8); ov[rm & ~mm] = (230, 60, 50); ov[mm & ~rm] = (40, 140, 230); ov[mm & rm] = (150, 150, 150)
        if v != "top":   # skylines on the overlay
            for sk, c in ((s["skyline_ref"], (200, 0, 0)), (s["skyline_model"], (0, 70, 200))):
                for i, zz in enumerate(sk):
                    if zz is None: continue
                    r_ = int(round(H - (zz + G0)/MPP)); ov[max(0, r_ - 1):r_ + 1, i] = c
            gr = int(round(H - G0/MPP)); ov[gr, :] = (0, 0, 0)
        pad = 8; canvas = Image.new("RGB", (3*W + 4*pad, H + 46), (255, 255, 255)); dr = ImageDraw.Draw(canvas)
        for k, (img, title) in enumerate(((rgb, "reference (aligned to metres)"), (mod, "model (ortho render)"), (ov, "overlay: red=ref only, blue=model only, grey=both"))):
            canvas.paste(Image.fromarray(img), (pad + k*(W + pad), 40)); dr.text((pad + k*(W + pad), 6), title, fill=(0, 0, 0))
        txt = f"{v}: IoU {s['iou']:.3f}" + (f"  skyline MAE {s['skyline_mae_m']:.2f} m" if v != "top" else f"  outline dist {s['outline_dist_m']:.2f} m") + f"   (1 px = {MPP} m; grid 10 m)"
        dr.text((pad, 22), txt, fill=(0, 0, 0))
        for k in range(3):   # 10 m grid ticks
            x0 = pad + k*(W + pad)
            for gu in np.arange(-200, 200, 10):
                c = int(round((gu - u[0])/MPP))
                if 0 <= c < W: dr.line([(x0 + c, 40 + H - 4), (x0 + c, 40 + H)], fill=(0, 0, 0))
        if v == "top":   # extra panel: footprint overlay
            fm, fr = FOOT; fo = np.full((H, W, 3), 255, np.uint8); fo[fr & ~fm] = (230, 60, 50); fo[fm & ~fr] = (40, 140, 230); fo[fm & fr] = (150, 150, 150)
            c2 = Image.new("RGB", (canvas.width + W + pad, canvas.height), (255, 255, 255)); c2.paste(canvas, (0, 0)); c2.paste(Image.fromarray(fo), (canvas.width, 40))
            ImageDraw.Draw(c2).text((canvas.width, 6), f"building footprint: IoU {s['footprint_iou']:.3f}", fill=(0, 0, 0)); canvas = c2
        canvas.save(os.path.join(OUT, f"sbs_{v}.png"))
json.dump(scores, open(os.path.join(OUT, "scores.json"), "w"))
print("SCORES", " ".join(f"{v}:IoU={s['iou']:.3f}" + (f",sky={s['skyline_mae_m']:.2f}m" if "skyline_mae_m" in s else f",outline={s['outline_dist_m']:.2f}m,footprint={s['footprint_iou']:.3f}") for v, s in scores.items()))
