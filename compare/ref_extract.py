"""Reference panels -> binary silhouettes + bbox (pixel) measurements.
Paper background is ~(225,223,222); building = pixels clearly darker / more saturated than paper.
Output: compare/ref/<view>_sil.png (tight crop to the building bbox) and compare/ref/ref_measure.json"""
import numpy as np, json, os
from PIL import Image
from scipy import ndimage as ndi
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
OUT = os.path.join(HERE, "ref"); os.makedirs(OUT, exist_ok=True)
VIEWS = {"south": "front_south", "north": "back_north", "west": "left_west", "east": "right_east", "top": "top_plan"}
meas = {}
for v, f in VIEWS.items():
    rgb = np.asarray(Image.open(os.path.join(ROOT, "ref", f + ".png")).convert("RGB")).astype(float)
    B = 4; rgb[:B] = rgb[-B:] = 226; rgb[:, :B] = rgb[:, -B:] = 226          # kill the thin panel border
    paper = np.median(rgb[B:B+20, B:-B].reshape(-1, 3), 0)
    d = np.abs(rgb - paper).max(2); sat = rgb.max(2) - rgb.min(2)
    m = (d > 22) | (sat > 18)
    m = ndi.binary_closing(m, np.ones((5, 5)), iterations=2)
    m = ndi.binary_opening(m, np.ones((3, 3)))
    lab, n = ndi.label(m); sizes = ndi.sum(m, lab, range(1, n + 1))
    keep = np.isin(lab, 1 + np.where(sizes >= 0.02 * sizes.max())[0])
    if v == "top":   # compass rose in the NW corner is not building
        keep = lab == (1 + np.argmax(sizes))
    m = ndi.binary_fill_holes(keep)
    ys, xs = np.where(m); x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    Image.fromarray((m[y0:y1, x0:x1] * 255).astype(np.uint8)).save(os.path.join(OUT, f"{v}_sil.png"))
    Image.fromarray(np.asarray(Image.open(os.path.join(ROOT, "ref", f + ".png")).convert("RGB"))[y0:y1, x0:x1]).save(os.path.join(OUT, f"{v}_crop.png"))
    meas[v] = {"panel": f + ".png", "bbox_px": [int(x0), int(y0), int(x1), int(y1)], "w_px": int(x1 - x0), "h_px": int(y1 - y0)}
    print(v, meas[v])
json.dump(meas, open(os.path.join(OUT, "ref_measure.json"), "w"), indent=1)
