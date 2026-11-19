"""Crop-matched side-by-side: reference iso | ours before | ours after (each cropped to its own building bbox and scaled to the
reference bbox height).   python3 compare/mat/iso_sheet.py OUT.png 'label:render.png:matid.png' ...  (first panel = ref)"""
import sys, os, numpy as np
from PIL import Image, ImageDraw
H = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(H))
def bbox_mask(m):
    ys, xs = np.where(m); return xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
ref = Image.open(os.path.join(ROOT, "ref", "isometric.png")).convert("RGB"); a = np.asarray(ref).astype(float)
paper = np.median(a[4:24, 4:-4].reshape(-1, 3), 0); rb = bbox_mask(np.abs(a - paper).max(2) > 18)
rc = ref.crop(rb); HH = 900; rc = rc.resize((int(rc.width*HH/rc.height), HH), Image.LANCZOS)
panels = [("reference isometric.png", rc)]
for spec in sys.argv[2:]:
    lab, img, mid = spec.split("::")
    im = Image.open(img).convert("RGB"); m = np.asarray(Image.open(mid).convert("RGB")).astype(int)
    if m.shape[:2] != (im.height, im.width): m = np.asarray(Image.open(mid).convert("RGB").resize(im.size, Image.NEAREST)).astype(int)
    b = bbox_mask(np.abs(m - 255).max(2) > 6); c = im.crop(b); panels.append((lab, c.resize((int(c.width*HH/c.height), HH), Image.LANCZOS)))
W = sum(p.width for _, p in panels) + 10*(len(panels) - 1); out = Image.new("RGB", (W, HH + 30), "white"); d = ImageDraw.Draw(out); x = 0
for lab, p in panels: out.paste(p, (x, 30)); d.text((x + 6, 8), lab, fill=(0, 0, 0)); x += p.width + 10
out.save(sys.argv[1]); print(sys.argv[1], out.size)
