"""Close-up material swatch sheet: per material  ref sample crop | ref colour | ours before colour | ours after colour |
our neutral render crop before / after (same window, chosen where the material mask covers most) | ΔE00 before -> after.
  python3 compare/mat/mat_swatches.py BEFORE_DIR AFTER_DIR OUT.png"""
import json, os, sys, numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
H = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(H))
BD, AD, OUTP = sys.argv[1:4]; S = json.load(open(os.path.join(H, "ref_samples.json")))
TB, TA = (sys.argv[4:6] if len(sys.argv) > 5 else ("before", "after"))   # optional json tags (gap #8: m7 -> m8)
MB, MA = json.load(open(os.path.join(H, f"mat_{TB}.json")))["materials"], json.load(open(os.path.join(H, f"mat_{TA}.json")))["materials"]
CATS = {"stone_cathedral": (255, 0, 0), "slate": (0, 0, 255), "plaster": (255, 255, 0), "brick": (255, 0, 255), "timber": (0, 255, 0),
        "stone_plinth": (0, 255, 255), "plinth_rock": (128, 64, 0), "cobble": (128, 128, 128), "stair": (255, 128, 0), "chimney": (128, 0, 0), "iron": (0, 0, 128)}
srgb = lambda c: np.where(c/255 <= 0.0031308, 12.92*c/255, 1.055*(c/255)**(1/2.4) - 0.055)*255
nb, na = Image.open(os.path.join(BD, "neutral.png")).convert("RGB"), Image.open(os.path.join(AD, "neutral.png")).convert("RGB")
mid = np.asarray(Image.open(os.path.join(AD, "matid.png")).convert("RGB")).astype(int)
T = 150; rows = []
for m, c in CATS.items():
    e = srgb(np.array(c, float)).round(); mask = np.abs(mid - e).max(2) <= 3
    win = 36 if m not in ("chimney", "iron", "timber") else 18
    cov = ndi.uniform_filter(mask.astype(float), win); y, x = np.unravel_index(np.argmax(cov), cov.shape); b = (x - win//2, y - win//2, x + win//2, y + win//2)
    panel, rects = next(iter(S[m]["rects"].items())); r = rects[0]
    refc = Image.open(os.path.join(ROOT, "ref", panel + ".png")).convert("RGB").crop(r).resize((T, T), Image.NEAREST)
    chip = lambda rgb: Image.new("RGB", (T//2, T), tuple(int(v) for v in rgb))
    row = Image.new("RGB", (T*4 + T//2*3 + 70, T + 22), "white"); d = ImageDraw.Draw(row); xx = 0
    for im in (refc, chip(MB[m]["ref"]["rgb"]), chip(MB[m]["ours"]["rgb"]), chip(MA[m]["ours"]["rgb"]), nb.crop(b).resize((T, T), Image.NEAREST), na.crop(b).resize((T, T), Image.NEAREST)):
        row.paste(im, (xx, 20)); xx += im.width + 10
    tex = {"stone_cathedral": "stone", "slate": "slate", "plaster": "plaster", "brick": "brick", "timber": "timber", "stone_plinth": "rubble", "plinth_rock": "soil",
           "cobble": "cobble", "stair": "stair", "chimney": "brick_red", "iron": "iron"}[m]
    row.paste(Image.open(os.path.join(ROOT, "tex", tex + ".png")).convert("RGB").resize((T, T)), (xx, 20))
    d.text((4, 3), f"{m}: dE00 {MB[m]['dE2000']} -> {MA[m]['dE2000']} | L* IQR ref {MA[m]['contrast_ref_IQR_L']}  ours {MB[m]['contrast_ours_IQR_L']} -> {MA[m]['contrast_ours_IQR_L']}  (ref {panel} {r})", fill=(0, 0, 0)); rows.append(row)
hdr = Image.new("RGB", (rows[0].width, 22), "white"); ImageDraw.Draw(hdr).text((4, 5), "ref sample | ref colour | ours before | ours after | our neutral render: before | after | after texture tile", fill=(0, 0, 0))
out = Image.new("RGB", (rows[0].width, 22 + sum(r.height for r in rows)), "white"); out.paste(hdr, (0, 0)); y = 22
for r in rows: out.paste(r, (0, y)); y += r.height
out.save(OUTP); print(OUTP, out.size)
