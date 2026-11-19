"""gap #4 (ruin) before/after sheets -> renders/*_before_after4.jpg"""
import os
from PIL import Image, ImageDraw
R = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "renders"); J = lambda n: os.path.join(R, n)
def sheet(a, b, la, lb, out, w=900):
    A, B = Image.open(J(a)).convert("RGB"), Image.open(J(b)).convert("RGB")
    h = int(A.height*w/A.width); A, B = A.resize((w, h)), B.resize((w, int(B.height*w/B.width)))
    S = Image.new("RGB", (2*w + 10, max(A.height, B.height) + 34), (255, 255, 255)); d = ImageDraw.Draw(S)
    S.paste(A, (0, 34)); S.paste(B, (w + 10, 34)); d.text((8, 10), la, fill=(0, 0, 0)); d.text((w + 18, 10), lb, fill=(0, 0, 0))
    S.save(J(out), quality=90); print(out)
sheet("beauty_iso_before4.png", "beauty_iso.png", "BEFORE (gap #3 state) - beauty iso", "AFTER gap #4 ruin - overcast + light fog", "beauty_iso_before_after4.jpg", 800)
sheet("nave_interior_before4.png", "nave_interior_after4.png", "BEFORE - nave toward the apse (old lighting)", "AFTER - nave toward the apse (ruin, mood light, +2 EV, fog)", "nave_interior_before_after4.jpg")
sheet("street_W_before4.png", "street_W_after4.png", "BEFORE - west street", "AFTER - west street", "street_W_before_after4.jpg")
sheet("street_cath_before4.png", "street_cath_after4.png", "BEFORE - W aisle wall base on the podium (eye 6.6 m above the street)", "AFTER - same view", "street_cath_before_after4.jpg")
for n in ("preview_nave", "preview_street_W", "preview_house_wall_W4", "preview_house_wall_E1"):
    sheet(n + "_before4.png", n + ".png", "BEFORE - three.js preview", "AFTER - three.js preview (optimized GLB)", n + "_before_after4.jpg", 800)
