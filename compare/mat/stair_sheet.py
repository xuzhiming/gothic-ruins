"""gap #9: reference | before | after crop of the south monumental stairs in the beauty iso.
  python3 compare/mat/stair_sheet.py OUT.png BEFORE.png AFTER.png MATID(1600).png"""
import sys, numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
out, bp, ap, mp = sys.argv[1:5]
srgb = lambda c: np.where(c/255 <= 0.0031308, 12.92*c/255, 1.055*(c/255)**(1/2.4) - 0.055)*255
mid = np.asarray(Image.open(mp).convert("RGB")).astype(int); m = np.abs(mid - srgb(np.array((255, 128, 0), float)).round()).max(2) <= 3
lab, n = ndi.label(ndi.binary_dilation(m, iterations=4)); sl = ndi.find_objects(lab)
south = [s for s in sl if s[0].start > mid.shape[0]*0.6]   # flights in the lower part of the frame = south stairs
y0 = min(s[0].start for s in south); y1 = max(s[0].stop for s in south); x0 = min(s[1].start for s in south); x1 = max(s[1].stop for s in south)
py, px = int((y1 - y0)*0.15), int((x1 - x0)*0.12); box = (max(0, x0 - px), max(0, y0 - py), x1 + px, y1 + py)
ref = Image.open("ref/isometric.png").convert("RGB").crop((60, 690, 420, 900))
H = 520; P = [("reference isometric.png (south stairs)", ref)] + [(l, Image.open(p).convert("RGB").crop(box)) for l, p in (("before (M8)", bp), ("after (M9)", ap))]
P = [(l, im.resize((int(im.width*H/im.height), H), Image.LANCZOS)) for l, im in P]
W = sum(im.width for _, im in P) + 10*(len(P) - 1); o = Image.new("RGB", (W, H + 26), "white"); d = ImageDraw.Draw(o); x = 0
for l, im in P: o.paste(im, (x, 26)); d.text((x + 4, 6), l, fill=(0, 0, 0)); x += im.width + 10
o.save(out); print(out, o.size, "crop", box)
