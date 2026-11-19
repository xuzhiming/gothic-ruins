"""Gap #2 sheets: west elevation reference | before | after (aligned to metres), street-level W row before/after, iso before/after."""
import json, os
from PIL import Image, ImageDraw
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); J = lambda *a: os.path.join(R, *a)
P = json.load(open(J("params.json"))); D = P["ref_scale"]["site_D"]; H = P["ref_scale"]["H_anchor"]
meta = json.load(open(J("renders", "sil_meta.json"))); mpp = meta["mpp"]; g = meta["ground_from_bottom_m"]
def model_panel(p):
    im = Image.open(p).convert("RGB"); w, h = im.size
    x0 = w/2 - D/2/mpp; yb = h - g/mpp
    return im.crop((int(x0), int(yb - H/mpp), int(x0 + D/mpp), int(yb)))
def sheet(panels, labels, out, size, vertical=False):
    pw, ph = size
    c = Image.new("RGB", ((pw, (ph + 24)*len(panels)) if vertical else (pw*len(panels), ph + 24)), "white"); d = ImageDraw.Draw(c)
    for i, (im, lb) in enumerate(zip(panels, labels)):
        x, y = (0, i*(ph + 24)) if vertical else (i*pw, 0)
        c.paste(im.resize((pw, ph)), (x, y + 24)); d.text((x + 8, y + 6), lb, fill=(0, 0, 0))
    c.save(out); print("wrote", out)
ref = Image.open(J("ref", "left_west.png")).convert("RGB").crop((14, 9, 739, 404))
pans = [ref, model_panel(J("renders", "shaded_west_before2.png")), model_panel(J("renders", "shaded_west.png"))]
sheet(pans, ["reference left_west (looking east: rear faces of the west row)", "model BEFORE (gap #2)", "model AFTER (gap #2)"],
      J("renders", "west_before_after.png"), (1100, 450), vertical=True)
low = lambda im: im.crop((0, int(im.height*0.45), im.width, im.height))   # house band only
sheet([low(p) for p in pans], ["reference (house band)", "BEFORE", "AFTER"], J("renders", "west_before_after_houses.png"), (1100, 250), vertical=True)
sheet([Image.open(J("renders", "street_W_before.png")), Image.open(J("renders", "street_W_after.png"))], ["west street BEFORE", "west street AFTER"],
      J("renders", "street_W_before_after.jpg"), (1000, 620))
sheet([Image.open(J("renders", "beauty_iso_before2.png")), Image.open(J("renders", "beauty_iso.png"))], ["iso BEFORE (gap #2)", "iso AFTER (gap #2)"],
      J("renders", "beauty_iso_before_after2.jpg"), (800, 950))
