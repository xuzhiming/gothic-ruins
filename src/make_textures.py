"""Procedural textures (numpy) -> tex/*.png. Deterministic (fixed seeds).
Every TILED texture is built only from exactly periodic sources (FFT noise on a torus, block layouts whose rows/columns divide
the image size, Voronoi with wrapped seeds) -> seamless tiling. Gap #4 (ruin): weathered stone with soot/water streaks and eroded
blocks, *_moss variants used automatically for upward-facing faces (moss/lichen on ledges, wall tops, treads), lichen-spotted
dark slate with broken slates, sooty brick, silver-grey weathered timber, mossy cobble joints, rusted iron.
Decals (RGBA, not tiled vertically): decal_streak (soot / runoff under sills and wall tops), decal_grime (ground splash band with
moss), decal_crack (cracks + spalled stones), decal_lath (plaster fallen off -> riven lath).
Gap #7 (match the reference renders): new slate (0.25 m courses, light lower edges, slope-aligned UVs), granite setts (cobble),
stair flagstones, layered rock/earth flanks (soil), paler weathered house brick + brick_red for chimneys, darker timber, less rust;
tangent-space normal maps *_n.png (512 px) from each texture's own height field; every colour is calibrated by compare/mat/grade.json
(per-texture linear RGB gains fitted against median colour samples of ref/*.png, see compare/mat/ and compare_log.md M7).
Gap #8: per-texture two-band tonal contrast (grade.json "_contrast", contrast()) fitted to the reference L* spread: more patch
mottling / lime residue on house brick, more slab-to-slab tone on stair flagstones, flatter setts and ashlar (compare_log.md M8)."""
import numpy as np, os
from PIL import Image, ImageDraw, ImageFilter
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tex"); os.makedirs(OUT, exist_ok=True)
def pnoise(seed, n, beta, kx=1.0, ky=1.0, kmin=1.0):
    """periodic 1/f^beta noise on an n x n torus (FFT filtered white noise), normalised to 0..1; ky > 1 -> features elongated along y"""
    rng = np.random.default_rng(seed); w = rng.standard_normal((n, n))
    fy = np.fft.fftfreq(n)[:, None]*n*ky; fx = np.fft.fftfreq(n)[None, :]*n*kx; r = np.sqrt(fx*fx + fy*fy)
    filt = np.where(r < kmin, 0.0, 1.0/np.maximum(r, kmin)**beta)
    a = np.real(np.fft.ifft2(np.fft.fft2(w)*filt))
    lo, hi = np.percentile(a, 0.5), np.percentile(a, 99.5); return np.clip((a - lo)/(hi - lo + 1e-9), 0, 1)
import json
GRADE_F = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "compare", "mat", "grade.json")
GRADE = {k: v for k, v in json.load(open(GRADE_F)).items() if not k.startswith("_")} if os.path.exists(GRADE_F) else {}
CONTRAST = json.load(open(GRADE_F)).get("_contrast", {}) if os.path.exists(GRADE_F) else {}
TILE_M = {"stone": 3.0, "stone_moss": 3.0, "rubble": 4.0, "rubble_moss": 4.0, "slate": 2.0, "brick": 2.0, "brick_red": 2.0, "stair": 2.0, "stair_riser": 2.0, "stair_side": 2.0,
          "cobble": 4.0, "timber": 1.5, "soil": 6.0, "iron": 1.0}   # = geom.TEX_M (tile size in metres)
def contrast(name, rgb):
    """gap #8: two-band tonal contrast, k = [k_low, k_high], applied multiplicatively in linear light on log-luminance (no clipping of
    darks, hue/chroma kept): low band = gaussian blur of linear luminance at 0.12 m (what survives at the 0.12 m/px iso view: patches,
    per-unit tint), high band = the rest (joints, grain). Wrap-mode blur -> still seamless. Mean colour is re-calibrated by GRADE."""
    from scipy.ndimage import gaussian_filter
    kl, kh = CONTRAST[name]; lin = s2l(rgb); Y = np.maximum(lin @ np.array([0.2126, 0.7152, 0.0722]), 1e-4); lY = np.log(Y); m = lY.mean()
    sig = 0.12*rgb.shape[0]/TILE_M.get(name, 2.0); lo = gaussian_filter(lY, sig, mode="wrap")
    f = np.exp((kl - 1)*(lo - m) + (kh - 1)*(lY - lo)); return l2s(np.clip(lin*f[..., None], 0, 1))
def s2l(c): return np.where(c <= 0.04045, c/12.92, ((c + 0.055)/1.055)**2.4)
def l2s(c): return np.where(c <= 0.0031308, 12.92*c, 1.055*np.maximum(c, 0)**(1/2.4) - 0.055)
def save(name, rgb, alpha=None):
    if name in CONTRAST: rgb = contrast(name, np.clip(rgb, 0, 1))
    if name in GRADE:   # gap #7: per-texture colour calibration against the reference renders (linear-light per-channel gain)
        rgb = l2s(np.clip(s2l(np.clip(rgb, 0, 1))*np.array(GRADE[name], float)[None, None], 0, 1))
    a = np.clip(rgb*255, 0, 255).astype(np.uint8)
    if alpha is not None: a = np.dstack([a, np.clip(alpha*255, 0, 255).astype(np.uint8)])
    Image.fromarray(a).save(os.path.join(OUT, name + ".png"))
def col(c): return np.array(c, float)/255
def save_normal(name, h, strength):
    """tangent-space normal map (OpenGL convention, +Y = up the texture) from a periodic height field (np.roll -> seamless)"""
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1))/2*strength; dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0))/2*strength
    n = np.dstack([-dx, dy, np.ones_like(h)]); n /= np.linalg.norm(n, axis=2, keepdims=True)
    Image.fromarray(np.clip((n*0.5 + 0.5)*255, 0, 255).astype(np.uint8)).resize((512, 512), Image.LANCZOS).save(os.path.join(OUT, name + ".png"))
def sm(x, a, b): t = np.clip((x - a)/(b - a), 0, 1); return t*t*(3 - 2*t)
def blocks(n, rows, cols, mortar, seed, stagger=True):
    """periodic running-bond block layout: rows | n and cols | n. returns block id, mortar mask, distance-to-joint (px)"""
    assert n % rows == 0 and n % cols == 0
    rh, cw = n//rows, n//cols; y = np.arange(n)[:, None]; x = np.arange(n)[None, :]
    r = (y//rh).repeat(n, 1); xo = (x + np.where(r % 2 == 1, cw//2, 0)*stagger) % n; c = xo//cw
    bid = r*(cols + 1) + c
    dy = np.minimum(y % rh, rh - 1 - y % rh).repeat(n, 1); dx = np.minimum(xo % cw, cw - 1 - xo % cw)
    d = np.minimum(dx, dy); return bid, d < mortar, d
def per_block(bid, seed, k=1):
    rng = np.random.default_rng(seed); v = rng.random((bid.max() + 1, k)); return v[bid]
def moss_layer(img, n, seed, cover, joints=None):
    m = pnoise(seed, n, 1.7, kmin=4.0); g = pnoise(seed + 1, n, 0.6, kmin=30.0)
    mask = sm(m + (0.25*joints if joints is not None else 0), 1 - cover, 1 - cover + 0.18)*(0.75 + 0.25*g)
    mc = col((64, 72, 44))*(0.7 + 0.5*g[..., None]) + col((30, 22, 4))*pnoise(seed + 2, n, 1.5, kmin=4.0)[..., None]*0.5
    mask = mask*0.8
    return img*(1 - mask[..., None]) + mc*mask[..., None]
# ---------------- stone ashlar (cathedral): 1024 px over 3 m, 8 courses x 4 blocks
def stone(seed=1):
    n = 1024; bid, mort, d = blocks(n, 8, 4, 3, seed)
    pb = per_block(bid, seed + 1, 3)
    base = col((132, 127, 118))*(0.93 + 0.1*pb[..., :1]) + (pb - 0.5)*0.01
    tone = pnoise(seed + 2, n, 2.2, kmin=1.0); mott = pnoise(seed + 3, n, 1.4, kmin=4.0); grain = pnoise(seed + 4, n, 0.3, kmin=60.0)
    img = base*(0.82 + 0.16*tone[..., None] + 0.1*mott[..., None] + 0.08*grain[..., None])
    img *= (0.9 + 0.1*np.clip(d/7.0, 0, 1))[..., None]                     # worn, darker arrises along the joints
    ero = (pb[..., 1] < 0.04)                                                 # eroded / spalled blocks
    pit = pnoise(seed + 5, n, 1.0, kmin=12.0)
    img = np.where(ero[..., None], img*(0.75 + 0.25*pit[..., None]), img)
    streak = pnoise(seed + 6, n, 1.8, kx=1.0, ky=5.0, kmin=2.0)               # soot / water runoff (long in v)
    s = sm(streak, 0.5, 0.95)*(0.4 + 0.6*tone)
    img = img*(1 - 0.3*s[..., None]) + col((50, 47, 42))*0.3*s[..., None]
    lich = sm(pnoise(seed + 7, n, 1.1, kmin=14.0), 0.86, 0.95)                # pale lichen spots
    img = img*(1 - 0.5*lich[..., None]) + col((168, 166, 132))*0.5*lich[..., None]
    img[mort] = img[mort]*0.7 + col((80, 76, 68))*0.3
    return img, mort
img, mort = stone(); save("stone", img)
_b, _m, _d = blocks(1024, 8, 4, 3, 1); save_normal("stone_n", np.clip(_d/6.0, 0, 1) + 0.15*pnoise(9, 1024, 1.2, kmin=6.0), 3.0)
save("stone_moss", moss_layer(img, 1024, 31, 0.34, joints=mort.astype(float)))
# ---------------- rubble masonry (plinths, ruins): 512 px over 4 m
def rubble(seed=2):
    n = 512; bid, mort, d = blocks(n, 8, 4, 5, seed); pb = per_block(bid, seed + 1, 3)
    img = col((120, 114, 104))*(0.75 + 0.4*pb[..., :1]) + (pb - 0.5)*0.015
    img *= (0.7 + 0.5*pnoise(seed + 2, n, 1.5, kmin=2.0)[..., None])*(0.7 + 0.3*np.clip(d/10, 0, 1))[..., None]
    img[mort] = col((58, 54, 48))*(0.8 + 0.4*pnoise(seed + 3, n, 0.5, kmin=20)[mort][..., None])
    return img, mort
img, mort = rubble(); save("rubble", img); _b, _m, _d = blocks(512, 8, 4, 5, 2); save_normal("rubble_n", np.clip(_d/9.0, 0, 1) + 0.25*pnoise(42, 512, 1.4, kmin=3.0), 3.0); save("rubble_moss", moss_layer(img, 512, 41, 0.4, joints=mort.astype(float)))
# ---------------- slate (gap #7: blue-grey, 0.25 m courses x 0.5 m slates, light lower edges + shadow line, per-slate variation,
# lichen + lost slates kept): 1024 px over 2 m. UVs are slope-aligned (build.py roof_slope): image rows = courses parallel to the eave.
def slate(seed=3):
    n = 1024; rows, cols = 8, 4; rh = n//rows; bid, mort, d = blocks(n, rows, cols, 3, seed); pb = per_block(bid, seed + 1, 5)
    y = (np.arange(n) % rh)[:, None].repeat(n, 1).astype(float)          # 0 at the top of a course (under the next course's edge)
    base = col((96, 103, 113))*(0.82 + 0.3*pb[..., :1]) + (pb[..., 1:4] - 0.5)*0.035
    img = base*(0.86 + 0.18*pnoise(seed + 2, n, 1.8, kmin=2.0)[..., None] + 0.06*pnoise(seed + 3, n, 0.3, kmin=50)[..., None])
    img *= (0.9 + 0.1*np.clip(d/6, 0, 1))[..., None]
    edge = sm(y, rh - 7, rh - 1); img = img*(1 - 0.35*edge[..., None]) + col((150, 156, 164))*0.35*edge[..., None]   # worn lower edge
    shad = 1 - sm(y, 0, 9); img *= (1 - 0.4*shad)[..., None]                                                         # shadow under the edge above
    rust = sm(pnoise(seed + 5, n, 1.4, kmin=6.0), 0.78, 0.92)*(pb[..., 4] > 0.6); img = img*(1 - 0.4*rust[..., None]) + col((120, 100, 78))*0.4*rust[..., None]
    lich = sm(pnoise(seed + 4, n, 1.2, kmin=10.0), 0.8, 0.92)*(pb[..., 2] > 0.4)
    img = img*(1 - 0.55*lich[..., None]) + col((150, 150, 118))*0.55*lich[..., None]
    broken = pb[..., 3] < 0.025; img = np.where(broken[..., None], col((40, 40, 43))*(0.8 + 0.4*pb[..., :1]), img)   # lost slates
    img[mort] = col((36, 38, 42))
    h = (y/rh)*0.8 + 0.2*np.clip(d/4, 0, 1); h[mort] = 0; h[broken] = 0.1
    return img, h
img, h = slate(); save("slate", img); save_normal("slate_n", h, 4.0)
# ---------------- brick: 512 px over 2 m, 32 courses x 8. brick_red = chimney stacks (the previous sooty red recipe, matches the
# reference chimneys); brick = house walls where the render is gone (gap #7: paler, weathered, more per-brick variation like the ref)
bid, mort, d = blocks(512, 32, 8, 2, 4); pb = per_block(bid, 5, 3)
img = col((128, 84, 64))*(0.72 + 0.45*pb[..., :1]) + (pb - 0.5)*0.05
img *= (0.8 + 0.3*pnoise(14, 512, 1.6, kmin=2.0)[..., None])
s_ = sm(pnoise(15, 512, 1.6, kx=1.0, ky=6.0, kmin=3.0), 0.5, 0.95); img = img*(1 - 0.45*s_[..., None]) + col((40, 32, 28))*0.45*s_[..., None]
img[mort] = col((140, 132, 118))*(0.7 + 0.3*pnoise(16, 512, 0.5, kmin=20)[mort][..., None]); save("brick_red", img)
img = col((150, 108, 86))*(0.55 + 0.8*pb[..., :1]) + (pb - 0.5)*0.07
img *= (0.6 + 0.75*pnoise(14, 512, 1.6, kmin=2.0)[..., None])   # gap #8: stronger patch mottling (survives at iso scale, ref L* IQR ~21)
lime = sm(pnoise(23, 512, 1.8, kmin=2.0), 0.62, 0.86); img = img*(1 - 0.5*lime[..., None]) + col((178, 168, 152))*0.5*lime[..., None]   # lime wash residue
s_ = sm(pnoise(15, 512, 1.6, kx=1.0, ky=6.0, kmin=3.0), 0.5, 0.95); img = img*(1 - 0.5*s_[..., None]) + col((52, 42, 36))*0.5*s_[..., None]
img[mort] = col((150, 142, 128))*(0.72 + 0.3*pnoise(16, 512, 0.5, kmin=20)[mort][..., None]); save("brick", img)
save_normal("brick_n", np.clip(d/2.0, 0, 1) + 0.1*pnoise(24, 512, 1.0, kmin=8.0), 2.5)
# ---------------- plaster (gap #3, unchanged recipe): 1024 px over 4 m, tones A/B/C
def plaster(name, base, seed):
    n = 1024
    tone = pnoise(seed, n, 2.4, kmin=1.0); mott = pnoise(seed + 1, n, 1.6, kmin=3.0); grain = pnoise(seed + 2, n, 0.4, kmin=40.0)
    streak = pnoise(seed + 3, n, 1.7, kx=1.0, ky=7.0, kmin=4.0); pits = pnoise(seed + 4, n, 0.2, kmin=60.0)
    lum = 1.0 + 0.07*(tone - 0.5) + 0.04*(mott - 0.5) + 0.035*(grain - 0.5)
    img = np.array(base, float)[None, None]/255*lum[..., None]
    g = np.clip((streak - 0.6)/0.4, 0, 1)**1.4; grime = np.array((112, 106, 96), float)/255
    img = img*(1 - 0.15*g[..., None]) + grime*(0.15*g[..., None])*0.6
    p = (pits > 0.93)[..., None]; img = np.where(p, img*0.86, img); save(name, img)
plaster("plaster", (198, 191, 176), 501); plaster("plaster_b", (184, 181, 172), 511); plaster("plaster_c", (201, 189, 166), 521)
# ---------------- timber (weathered silver-brown oak, grain along u, shakes)
n = 512; gr = pnoise(8, n, 1.2, kx=10.0, ky=1.0, kmin=2.0); fine = pnoise(9, n, 0.6, kx=12.0, ky=1.0, kmin=10.0)
img = col((92, 76, 60))*(0.62 + 0.38*gr[..., None] + 0.18*fine[..., None])
sil = pnoise(10, n, 2.0, kmin=1.0); img = img*(1 - 0.35*sil[..., None]) + col((120, 116, 106))*0.35*sil[..., None]   # silvering
img = np.where((fine < 0.12)[..., None], img*0.45, img); save("timber", img)
# ---------------- cobbles (gap #7): rounded granite setts in staggered rows like the reference plaza (rows 0.5 m, setts 0.35-0.7 m;
# the ref draws them ~0.8 m, kept smaller for street level), domed tops, dark mossy joints. 512 px over 4 m, periodic.
rng = np.random.default_rng(10); N = 512; R = 8; rh = N//R
sid = np.zeros((N, N), int); dist = np.zeros((N, N)); k = 0
for r in range(R):
    m = int(rng.integers(7, 10)); w = rng.random(m) + 0.7; cuts = np.concatenate([[0], np.cumsum(w)/w.sum()*N]).round().astype(int)
    off = int(rng.integers(0, N)); ys = slice(r*rh, (r + 1)*rh); xr = (np.arange(N) - off) % N
    idx = np.clip(np.searchsorted(cuts, xr, side="right") - 1, 0, m - 1)
    dx = np.minimum(xr - cuts[idx], cuts[idx + 1] - 1 - xr).astype(float)
    t0 = rng.uniform(0, 7, m)[idx]; t1 = rng.uniform(0, 7, m)[idx]; rc = rng.uniform(8, 18, m)[idx]   # per-sett ragged top/bottom + corner radius
    yl = np.arange(rh)[:, None].astype(float); dy = np.minimum(yl - t0[None, :], rh - 1 - t1[None, :] - yl)
    ex, ey = np.maximum(rc[None, :] - dx[None, :], 0), np.maximum(rc[None, :] - dy, 0)
    dist[ys] = np.where((ex > 0) & (ey > 0), rc[None, :] - np.hypot(ex, ey), np.minimum(dx[None, :], dy))
    sid[ys] = (k + idx)[None, :]; k += m
dist += (pnoise(14, N, 1.2, kmin=12.0) - 0.5)*5.0                                       # irregular, chipped outlines
tint = 0.88 + 0.2*rng.random(k); hue = rng.random((k, 3))
dome = np.clip(dist/14.0, 0, 1); joint = dist < 2.0
img = (col((122, 119, 114))[None, None] + (hue[sid] - 0.5)*0.012)*tint[sid][..., None]*(0.84 + 0.22*pnoise(11, N, 1.6, kmin=3.0)[..., None])
img *= (0.88 + 0.14*dome)[..., None]
mz = sm(pnoise(12, N, 2.0, kmin=1.5), 0.4, 0.8)*sm(2.6 - np.clip(dist, 0, 2.6), 0.0, 1.5)
img = np.where(joint[..., None], col((84, 80, 74))*(0.8 + 0.3*pnoise(13, N, 0.6, kmin=20)[..., None]), img)
img = img*(1 - 0.75*mz[..., None]) + col((60, 70, 38))*0.75*mz[..., None]; save("cobble", img)
save_normal("cobble_n", np.sqrt(np.clip(dist/12.0, 0, 1)), 4.0)
# ---------------- stair stone (gap #9): 512 px over 2 m, 5 rows of 0.4 m. build.py/geom.stair maps ONE row per tread (row bottom =
# front nosing) and ONE row per riser (row top = under the nosing, row bottom = grime corner) via per-step UV frames, so the pattern
# follows each step instead of world-tiling across steps. Subtle per-slab tone (+-4 %), fine dark joints, worn rounded nosings
# (lighter + normal-map roll-off), grime at the back of each tread and the foot of each riser, moss in joints and corners.
def stair_rows(seed, base, slab_var, slabs=(2, 4)):
    rng2 = np.random.default_rng(seed); sid2 = np.zeros((512, 512), int); dj = np.full((512, 512), 99.0); vy = np.zeros((512, 512)); k = 0
    for r in range(5):
        y0, y1 = r*512//5, (r + 1)*512//5; m = int(rng2.integers(slabs[0], slabs[1] + 1)); w = rng2.random(m) + 0.6
        cuts = np.concatenate([[0], np.cumsum(w)/w.sum()*512]).round().astype(int); off = int(rng2.integers(0, 512)); xr = (np.arange(512) - off) % 512
        idx = np.clip(np.searchsorted(cuts, xr, side="right") - 1, 0, m - 1); dx = np.minimum(xr - cuts[idx], cuts[idx + 1] - 1 - xr)
        sid2[y0:y1] = (k + idx)[None, :]; k += m; dj[y0:y1] = dx[None, :]
        vy[y0:y1] = ((np.arange(y1 - y0) + 0.5)/(y1 - y0))[:, None]   # 0 = row top (back of tread / top of riser), 1 = row bottom
    tone = 1 + slab_var*(rng2.random(k)*2 - 1); rowt = 1 + 0.025*(rng2.random(5)*2 - 1)
    img = col(base)[None, None]*tone[sid2][..., None]*np.repeat(rowt, 512//5 + 1)[:512][:, None, None]
    img *= (0.93 + 0.12*pnoise(seed + 1, 512, 1.5, kmin=3.0)[..., None])*(0.91 + 0.13*pnoise(seed + 2, 512, 1.4, kmin=2.0)[..., None])
    return img, sid2, dj, vy
img, sid2, dj, vy = stair_rows(30, (122, 116, 108), 0.04)
nose = sm(vy, 0.86, 0.97); back = 1 - sm(vy, 0.0, 0.14)
wear = sm(pnoise(33, 512, 1.2, kmin=4.0), 0.55, 0.9)*(1 - back)
img = img*(1 + 0.03*nose - 0.15*back)[..., None]; img = img*(1 - 0.12*wear[..., None]) + col((150, 144, 134))*0.12*wear[..., None]
chip = sm(pnoise(36, 512, 1.0, kmin=10.0), 0.75, 0.9)*sm(vy, 0.93, 1.0); img = img*(1 - 0.2*chip[..., None])   # chipped nosings
jl = sm(2.2 - dj, 0.0, 1.4); img = img*(1 - 0.55*jl[..., None]) + col((58, 55, 50))*0.55*jl[..., None]
mz = sm(pnoise(34, 512, 1.8, kmin=2.0), 0.55, 0.85)*np.maximum(dj < 3, back > 0.6); img = img*(1 - 0.6*mz[..., None]) + col((66, 74, 44))*0.6*mz[..., None]
save("stair", img)
h = 1 - 0.8*sm(vy, 0.9, 1.0)**1.5 - 0.5*sm(3.0 - dj, 0, 2.5) + 0.08*pnoise(35, 512, 1.3, kmin=4.0)
save_normal("stair_n", h, 4.0)
img, sid3, dj3, vy3 = stair_rows(40, (96, 90, 84), 0.035, slabs=(2, 3))
lip = 1 - sm(vy3, 0.0, 0.22); foot = sm(vy3, 0.6, 1.0)
img = img*(1 - 0.18*lip - 0.2*foot)[..., None]
st_ = sm(pnoise(41, 512, 1.6, kx=1.0, ky=5.0, kmin=3.0), 0.55, 0.95); img = img*(1 - 0.2*st_[..., None]) + col((60, 56, 50))*0.2*st_[..., None]
jl = sm(2.2 - dj3, 0.0, 1.4); img = img*(1 - 0.5*jl[..., None]) + col((52, 49, 44))*0.5*jl[..., None]
mz = sm(pnoise(42, 512, 1.8, kmin=2.0), 0.5, 0.85)*np.maximum(foot > 0.8, dj3 < 3); img = img*(1 - 0.55*mz[..., None]) + col((60, 70, 40))*0.55*mz[..., None]
save("stair_riser", img); save_normal("stair_riser_n", 1 - 0.5*sm(3.0 - dj3, 0, 2.5) + 0.12*pnoise(43, 512, 1.3, kmin=4.0), 3.0)
bid, mort, d = blocks(512, 8, 4, 2, 44); pb = per_block(bid, 45)
img = col((112, 106, 98))*(0.95 + 0.08*pb)*(0.92 + 0.14*pnoise(46, 512, 1.5, kmin=3.0)[..., None])
img[mort] = col((70, 66, 60)); save("stair_side", img); save_normal("stair_side_n", np.clip(d/4.0, 0, 1) + 0.1*pnoise(47, 512, 1.2, kmin=6.0), 2.5)
# ---------------- iron (rust), glass (dirty), soil
r = sm(pnoise(13, N, 1.5, kmin=3.0), 0.55, 0.9); st_ = sm(pnoise(17, N, 1.5, ky=6, kmin=3), 0.6, 0.95)
img = col((36, 34, 33))*(0.8 + 0.4*pnoise(18, N, 0.5, kmin=20)[..., None]); rc = col((112, 54, 24))*(0.7 + 0.5*pnoise(19, N, 0.8, kmin=8)[..., None])
m = np.clip(r + 0.4*st_, 0, 1)[..., None]*0.35; save("iron", img*(1 - m) + rc*m)   # gap #7: ref gate is dark grey, little rust
g = pnoise(20, N, 2.0, kmin=1.0); save("glass", col((40, 48, 52))[None, None]*(0.65 + 0.5*g[..., None]) + col((50, 45, 35))*0.3*sm(pnoise(21, N, 1.4, kmin=3), 0.5, 0.9)[..., None])
# soil (gap #7): the platform's flanks in the ref are layered rock / packed earth with embedded stones, not plain soil.
# 512 px over 6 m (vertical faces: image rows = height), periodic warped strata.
strata = pnoise(22, N, 1.6, kx=3.0, ky=1.0, kmin=2.5)                                  # horizontal rock lenses (kx>1: long in x)
stones = pnoise(29, N, 1.3, kmin=7.0)
earth = col((122, 106, 86))*(0.78 + 0.3*pnoise(25, N, 1.6, kmin=2.0)[..., None]); rock = col((134, 127, 116))*(0.72 + 0.34*pnoise(26, N, 1.4, kmin=3.0)[..., None])
rk = np.clip(sm(strata, 0.45, 0.62) + sm(stones, 0.74, 0.8), 0, 1)[..., None]; img_e = sm(stones, 0.7, 0.74) - sm(stones, 0.74, 0.78); img = earth*(1 - rk) + rock*rk
cr = sm(pnoise(27, N, 0.9, kx=3.0, ky=1.0, kmin=6.0), 0.84, 0.95); img *= (1 - 0.4*cr - 0.35*np.clip(img_e, 0, 1))[..., None]
band = rk[..., 0]
save("soil", img); save_normal("soil_n", 0.6*band + 0.4*pnoise(28, N, 1.3, kmin=4.0) - 0.5*cr, 6.0)
# ---------------- decals (RGBA)
D = 512; v = (1 - np.arange(D)/(D - 1))[:, None].repeat(D, 1)   # v = 1 at the top row of the image (= top of the quad)
st_ = pnoise(30, D, 1.5, kx=1.0, ky=9.0, kmin=2.0)                  # periodic in u (decals tile horizontally)
a = sm(st_, 0.3, 0.85)*(v**1.3)*0.85 + 0.12*v**3
save("decal_streak", col((36, 33, 29))[None, None]*(0.8 + 0.4*pnoise(31, D, 1.0, kmin=6)[..., None]), np.clip(a, 0, 0.9))
gn = pnoise(32, D, 1.6, kx=1.0, ky=2.5, kmin=2.0); mo = sm(pnoise(33, D, 1.8, kmin=3.0), 0.62, 0.85)*(1 - v)**1.2*0.6
a = np.clip(((1 - v)**1.4)*(0.55 + 0.45*gn) + 0.5*mo, 0, 0.92)
c = col((60, 53, 42))*(0.8 + 0.4*gn[..., None]); c = c*(1 - mo[..., None]) + col((56, 64, 40))*mo[..., None]
save("decal_grime", c, a)
def crack_decal(seed):
    rng = np.random.default_rng(seed); im = Image.new("L", (D, D), 0); dr = ImageDraw.Draw(im)
    def walk(x, y, ang, L, w, depth):
        for _ in range(int(L)):
            ang += rng.normal(0, 0.35); nx, ny = x + 6*np.cos(ang), y + 6*np.sin(ang)
            dr.line([(x, y), (nx, ny)], fill=230, width=max(1, int(w))); x, y = nx, ny; w = max(1.0, w*0.985)
            if depth < 2 and rng.random() < 0.05: walk(x, y, ang + rng.choice([-1, 1])*rng.uniform(0.5, 1.1), L*0.45, w*0.7, depth + 1)
            if not (8 < x < D - 8 and 8 < y < D - 8): break
    for _ in range(3): walk(rng.uniform(150, 360), rng.uniform(30, 80), np.pi/2 + rng.normal(0, 0.5), 70, 4.0, 0)
    sp = Image.new("L", (D, D), 0); ds = ImageDraw.Draw(sp)
    for _ in range(4):   # spalled / missing stone pockets
        cx, cy_ = rng.uniform(80, 430), rng.uniform(80, 430); r0 = rng.uniform(18, 46)
        ds.polygon([(cx + r0*rng.uniform(0.6, 1.2)*np.cos(t), cy_ + r0*rng.uniform(0.6, 1.2)*np.sin(t)) for t in np.linspace(0, 2*np.pi, 9)[:-1]], fill=200)
    ck = np.asarray(im.filter(ImageFilter.GaussianBlur(0.8)), float)/255; spa = np.asarray(sp.filter(ImageFilter.GaussianBlur(1.5)), float)/255
    edge = np.clip(np.hypot(*np.gradient(spa))*6, 0, 1)
    a = np.clip(np.maximum(ck*0.95, spa*0.55) + edge*0.3, 0, 0.95)
    c = col((30, 28, 25))*(1 - spa[..., None]) + col((58, 54, 48))*spa[..., None]*(0.7 + 0.6*pnoise(34, D, 1.0, kmin=8)[..., None])
    return c, a
c, a = crack_decal(35); save("decal_crack", c, a)
# lath: plaster fallen off in an irregular patch -> riven oak laths (horizontal) with dark gaps, broken plaster lip around it
yy, xx = np.mgrid[0:D, 0:D]/(D - 1.0); rr = np.hypot(xx - 0.5, (yy - 0.5)*1.1)
blob = rr + 0.22*(pnoise(36, D, 1.8, kmin=2.0) - 0.5); inner = sm(-blob, -0.40, -0.36); lip = sm(-blob, -0.46, -0.40) - inner
lath = (np.arange(D)[:, None] % 24 < 17).repeat(D, 1).astype(float); lc = col((96, 74, 52))*(0.7 + 0.5*pnoise(37, D, 1.0, kx=8, kmin=4)[..., None])
c = lc*lath[..., None] + col((22, 18, 14))*(1 - lath[..., None]); c = c*(1 - lip[..., None]) + col((150, 144, 130))*lip[..., None]
save("decal_lath", c, np.clip(inner + lip*0.9, 0, 1))
print("textures ->", OUT, sorted(os.listdir(OUT)))
