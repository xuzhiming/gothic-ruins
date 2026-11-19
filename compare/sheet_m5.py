"""Gap #5 sheets: per side view, reference | before | after (overlay panels of compare --sbs) + the two strongest rejected options."""
import os
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
def panels(p):
    im = Image.open(p); W = (im.width - 32)//3; return [im.crop((8 + i*(W + 8), 0, 8 + i*(W + 8) + W, im.height)) for i in range(3)]
for v in ("west", "east"):
    rows = [("reference (extracted from ref/%s)" % ("left_west.png" if v == "west" else "right_east.png"), panels(f"{HERE}/work/exp_base/cmp/sbs_{v}.png")[0]),
            ("before (gap #4 state) - overlay: grey both, red ref only, blue model only", panels(f"{HERE}/work/exp_base/cmp/sbs_{v}.png")[2]),
            ("after (run_all M5: no geometry change accepted - identical)", panels(f"{HERE}/out/sbs_{v}.png")[2]),
            ("rejected E5: apse centre 41->38 m (leaves plan apse tip uncovered)", panels(f"{HERE}/work/exp_E5_cy38.0/cmp/sbs_{v}.png")[2]),
            ("rejected E1: cathedral lengthened over the plaza (footprint 0.851->0.649)", panels(f"{HERE}/work/exp_E1_full_length/cmp/sbs_{v}.png")[2])]
    W = max(r[1].width for r in rows); H = sum(r[1].height + 24 for r in rows); out = Image.new("RGB", (W, H), "white"); y = 0; d = ImageDraw.Draw(out)
    for t, im in rows: d.text((8, y + 6), t, fill=(0, 0, 0)); out.paste(im, (0, y + 24)); y += im.height + 24
    out.save(f"{HERE}/diag/sheet_{v}_ref_before_after.png"); print(v, out.size)
