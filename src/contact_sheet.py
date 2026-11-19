"""Contact sheet of the final stills: python3 src/contact_sheet.py DIR OUT.jpg  (labels = file name, resolution)"""
import sys, glob, os
from PIL import Image, ImageDraw
D, OUT = sys.argv[1:3]; fs = sorted(f for f in glob.glob(os.path.join(D, "*.png")))
W = 760; cells = []
for f in fs:
    im = Image.open(f).convert("RGB"); lab = f"{os.path.basename(f)}  {im.width}x{im.height}"
    t = im.resize((W, int(W*im.height/im.width)), Image.LANCZOS)
    if t.height > 900: t = t.resize((int(t.width*900/t.height), 900), Image.LANCZOS)
    c = Image.new("RGB", (W, t.height + 26), "white"); c.paste(t, ((W - t.width)//2, 26)); ImageDraw.Draw(c).text((6, 7), lab, fill=(0, 0, 0)); cells.append(c)
cols = 2; rows = [cells[i:i + cols] for i in range(0, len(cells), cols)]; H = sum(max(c.height for c in r) for r in rows) + 10*(len(rows) + 1)
o = Image.new("RGB", (cols*W + 10*(cols + 1), H), (235, 232, 226)); y = 10
for r in rows:
    for k, c in enumerate(r): o.paste(c, (10 + k*(W + 10), y))
    y += max(c.height for c in r) + 10
o.save(OUT, quality=90); print(OUT, o.size, len(fs), "stills")
