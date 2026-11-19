"""Before/after sheets for a change: south elevation (reference | before | after, aligned to metres) + iso beauty pair.
usage: python3 src/before_after.py   (expects renders/shaded_south_before.png, renders/shaded_south.png, renders/beauty_iso_before.png, renders/beauty_iso.png)"""
import json, os
from PIL import Image, ImageDraw
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); J = lambda *a: os.path.join(R, *a)
P = json.load(open(J("params.json"))); W = P["ref_scale"]["site_W"]; H = P["ref_scale"]["H_anchor"]
meta = json.load(open(J("renders", "sil_meta.json"))); mpp = meta["mpp"]; g = meta["ground_from_bottom_m"]
def model_panel(p):
    im = Image.open(p).convert("RGB"); w, h = im.size
    x0 = w/2 - W/2/mpp; x1 = w/2 + W/2/mpp; yb = h - g/mpp; yt = yb - H/mpp
    return im.crop((int(x0), int(yt), int(x1), int(yb)))
ref = Image.open(J("ref", "front_south.png")).convert("RGB").crop((22, 9, 722, 448))
def sheet(panels, labels, out, size):
    pw, ph = size; c = Image.new("RGB", (pw*len(panels), ph + 28), "white"); d = ImageDraw.Draw(c)
    for i, (im, lb) in enumerate(zip(panels, labels)):
        c.paste(im.resize((pw, ph)), (i*pw, 28)); d.text((i*pw + 8, 8), lb, fill=(0, 0, 0))
    c.save(out); print("wrote", out)
pans = [ref, model_panel(J("renders", "shaded_south_before.png")), model_panel(J("renders", "shaded_south.png"))]
sheet(pans, ["reference front_south", "model BEFORE", "model AFTER"], J("renders", "south_before_after.png"), (700, 439))
# cathedral zoom (u -17..17 m, z 11..42.4 m)
def zoom(im):
    w, h = im.size; sx, sy = w/W, h/H
    return im.crop((int((W/2 - 17)*sx), int((H - 42.4)*sy) if H > 42.4 else 0, int((W/2 + 17)*sx), int((H - 11)*sy)))
sheet([zoom(p) for p in pans], ["reference (zoom)", "BEFORE", "AFTER"], J("renders", "south_before_after_zoom.png"), (520, 480))
b0, b1 = Image.open(J("renders", "beauty_iso_before.png")).convert("RGB"), Image.open(J("renders", "beauty_iso.png")).convert("RGB")
sheet([b0, b1], ["iso BEFORE", "iso AFTER"], J("renders", "beauty_iso_before_after.jpg"), (800, 950))
