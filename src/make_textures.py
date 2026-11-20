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
TILE_M = {"stone": 3.0, "stone_moss": 3.0, "rubble": 4.0, "rubble_moss": 4.0, "slate": 2.0, "brick": 2.0, "brick_bare": 2.0, "plaster_edge": 1.0, "brick_red": 2.0, "stair": 2.0, "stair_riser": 2.0, "stair_side": 2.0,
          "cobble": 4.0, "timber": 1.5, "soil": 6.0, "iron": 1.0, "plaster": 4.0, "plaster_b": 4.0, "plaster_c": 4.0, "plaster_d": 8.0, "wframe": 1.0}   # = geom.TEX_M (tile size in metres)
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
    if name in M10_RAW:   # gap #10: wall recipes targeted at the ref elevations; optional fitted gain only
        kname = {"brick_bare": "brick", "plaster_edge": "plaster_d"}.get(name, name)   # gap #12: bare brick behind the plaster skin = same fitted brick gain
        if kname in WALL_K: rgb = l2s(np.clip(s2l(np.clip(rgb, 0, 1))*np.array(WALL_K[kname], float)[None, None], 0, 1))
        rgb = np.clip(rgb, 0, 1)
    elif name in CONTRAST: rgb = contrast(name, np.clip(rgb, 0, 1))
    if name in GRADE and name not in M10_RAW:   # gap #7: per-texture colour calibration against the reference renders (linear-light per-channel gain)
        rgb = l2s(np.clip(s2l(np.clip(rgb, 0, 1))*np.array(GRADE[name], float)[None, None], 0, 1))
    a = np.clip(rgb*255, 0, 255).astype(np.uint8)
    if alpha is not None: a = np.dstack([a, np.clip(alpha*255, 0, 255).astype(np.uint8)])
    Image.fromarray(a).save(os.path.join(OUT, name + ".png"))
def col(c): return np.array(c, float)/255
def save_normal(name, h, strength, res=512):
    """tangent-space normal map (OpenGL convention, +Y = up the texture) from a periodic height field (np.roll -> seamless)"""
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1))/2*strength; dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0))/2*strength
    n = np.dstack([-dx, dy, np.ones_like(h)]); n /= np.linalg.norm(n, axis=2, keepdims=True)
    Image.fromarray(np.clip((n*0.5 + 0.5)*255, 0, 255).astype(np.uint8)).resize((res, res), Image.LANCZOS).save(os.path.join(OUT, name + ".png"))
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
# ---------------- M10 (gap #10, wall textures replaced to match the original renderings ref/isometric.png + elevations, see
# compare/mat/wall_map.md). Recipes in M10_RAW are colour-targeted directly against the reference elevations (no grade.json gain /
# contrast: those were fitted to the old recipes) -- WALL_K below holds the per-texture linear gains from compare/wall/fit_wall.py.
M10_RAW = {"stone", "stone_moss", "rubble", "rubble_moss", "brick", "brick_bare", "plaster_edge", "plaster", "plaster_b", "plaster_c", "plaster_d", "timber"}
WALL_K_F = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "compare", "wall", "wall_gain.json")
WALL_K = {k: v for k, v in json.load(open(WALL_K_F)).items() if not k.startswith("_")} if os.path.exists(WALL_K_F) else {}
# ---------------- stone ashlar (cathedral, house ground floors): 1024 px over 3 m, 8 courses (0.375 m) x 4 blocks (0.75 m).
# ref (left_west / front_south cathedral): light warm-grey ashlar Lab ~(58, 1, 4) lit, clear darker joints, per-block tone steps,
# dark soot runoff, pale weathered arrises.
def stone(seed=1):
    n = 1024; bid, mort, d = blocks(n, 8, 4, 3, seed)
    pb = per_block(bid, seed + 1, 3)
    base = col((148, 142, 135))*(0.82 + 0.3*pb[..., :1]) + (pb - 0.5)*0.012
    tone = pnoise(seed + 2, n, 2.2, kmin=1.0); mott = pnoise(seed + 3, n, 1.4, kmin=4.0); grain = pnoise(seed + 4, n, 0.3, kmin=60.0)
    img = base*(0.86 + 0.14*tone[..., None] + 0.1*mott[..., None] + 0.07*grain[..., None])
    img *= (0.84 + 0.16*np.clip(d/8.0, 0, 1))[..., None]                     # worn, darker arrises along the joints
    ero = (pb[..., 1] < 0.05); pit = pnoise(seed + 5, n, 1.0, kmin=12.0)      # eroded / spalled blocks
    img = np.where(ero[..., None], img*(0.72 + 0.25*pit[..., None]), img)
    streak = pnoise(seed + 6, n, 1.8, kx=1.0, ky=5.0, kmin=2.0)               # soot / water runoff (long in v)
    s = sm(streak, 0.55, 0.95)*(0.4 + 0.6*tone)
    img = img*(1 - 0.38*s[..., None]) + col((58, 55, 50))*0.38*s[..., None]
    lich = sm(pnoise(seed + 7, n, 1.1, kmin=14.0), 0.88, 0.96)
    img = img*(1 - 0.4*lich[..., None]) + col((172, 168, 140))*0.4*lich[..., None]
    img[mort] = col((104, 99, 91))*(0.85 + 0.3*pnoise(seed + 8, n, 0.6, kmin=20)[mort][..., None])
    return img, mort
img, mort = stone(); save("stone", img)
_b, _m, _d = blocks(1024, 8, 4, 3, 1); save_normal("stone_n", np.clip(_d/6.0, 0, 1) + 0.15*pnoise(9, 1024, 1.2, kmin=6.0), 3.0)
save("stone_moss", moss_layer(img, 1024, 31, 0.34, joints=mort.astype(float)))
# ---------------- rubble / plinth masonry (terrace walls, house plinths, ruins): 512 px over 4 m. ref: big rough squared blocks
# (rows 0.5 m, blocks 0.5-1.0 m, random per-row offsets), light greige Lab ~(57, 2, 6), dark deep joints (62,60,55), weathered faces.
def rubble(seed=2):
    n = 512; rows = 8; rh = n//rows; rng = np.random.default_rng(seed)
    y = np.arange(n)[:, None].repeat(n, 1); x = np.arange(n)[None, :].repeat(n, 0)
    yw = (y + np.round(14*(pnoise(seed + 11, n, 2.2, kmin=2.0) - 0.5))).astype(int) % n    # wavy, uneven courses (periodic warp)
    xw = (x + np.round(10*(pnoise(seed + 12, n, 2.2, kmin=2.0) - 0.5))).astype(int) % n
    r = yw//rh; K = 8; cuts = np.full((rows, K), n*4)
    for i in range(rows):                                     # each course: 5-7 blocks with random joint positions (periodic in u)
        k_ = int(rng.integers(5, 8)); w_ = rng.uniform(0.65, 1.35, k_); cuts[i, :k_] = np.sort(np.round((rng.uniform(0, n) + np.cumsum(w_/w_.sum()*n)) % n))
    C = cuts[r]; valid = C < n*2; kk = (valid & (C <= xw[..., None])).sum(-1); nk = valid.sum(-1); bid = r*16 + kk % nk
    dist = np.where(valid, np.abs(((xw[..., None] - C) + n/2) % n - n/2), 1e9).min(-1)
    dy = np.minimum(yw % rh, rh - 1 - yw % rh); d = np.minimum(dist, dy)
    wob = 3.0*pnoise(seed + 9, n, 1.2, kmin=6.0); mort = d < 3 + wob
    pb = per_block(bid, seed + 1, 3)
    img = col((150, 139, 127))*(0.74 + 0.42*pb[..., :1]) + (pb - 0.5)*0.03
    img *= (0.76 + 0.34*pnoise(seed + 2, n, 1.5, kmin=2.0)[..., None])*(0.62 + 0.38*np.clip((d - 3)/16, 0, 1))[..., None]   # rounded, darker edges
    s = sm(pnoise(seed + 4, n, 1.7, kx=1.0, ky=5.0, kmin=2.0), 0.6, 0.95); img = img*(1 - 0.35*s[..., None]) + col((60, 56, 50))*0.35*s[..., None]
    lich = sm(pnoise(seed + 5, n, 1.3, kmin=8.0), 0.82, 0.93); img = img*(1 - 0.35*lich[..., None]) + col((120, 124, 88))*0.35*lich[..., None]
    img[mort] = col((56, 53, 48))*(0.8 + 0.4*pnoise(seed + 3, n, 0.5, kmin=20)[mort][..., None])
    h = np.sqrt(np.clip((d - 2)/14.0, 0, 1)) + 0.25*pnoise(42, n, 1.4, kmin=3.0)
    return img, mort, h
img, mort, h = rubble(); save("rubble", img); save_normal("rubble_n", h, 3.0); save("rubble_moss", moss_layer(img, 512, 41, 0.4, joints=mort.astype(float)))
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
# ---------------- brick (M10): 512 px over 2 m, 32 courses (6.25 cm) x 8 (25 cm). brick_red = chimney stacks (unchanged).
# brick = house walls (E3/E4 bodies, brick ground floors, patches): ref front_south E4 / iso east row -> soft salmon brick
# Lab ~(52, 7, 12) (much less saturated than before), pale lime mortar, per-brick tone, lime-wash / plaster residue (~12 %), soot.
bid, mort, d = blocks(512, 32, 8, 2, 4); pb = per_block(bid, 5, 3)
img = col((128, 84, 64))*(0.72 + 0.45*pb[..., :1]) + (pb - 0.5)*0.05
img *= (0.8 + 0.3*pnoise(14, 512, 1.6, kmin=2.0)[..., None])
s_ = sm(pnoise(15, 512, 1.6, kx=1.0, ky=6.0, kmin=3.0), 0.5, 0.95); img = img*(1 - 0.45*s_[..., None]) + col((40, 32, 28))*0.45*s_[..., None]
img[mort] = col((140, 132, 118))*(0.7 + 0.3*pnoise(16, 512, 0.5, kmin=20)[mort][..., None]); save("brick_red", img)
def brick_field(n, tile_m, seed, rgb, var=0.32):
    """salmon brick + pale mortar at true scale (6.25 cm courses, 25 cm bricks) for a tile of tile_m metres"""
    rows, cols = int(round(tile_m/0.0625)), int(round(tile_m/0.25)); bid, mort, d = blocks(n, rows, cols, max(1, n//rows//7), seed)
    pb = per_block(bid, seed + 1, 3)
    img = col(rgb)*(1 - var/2 + var*pb[..., :1]) + (pb - 0.5)*0.035
    img *= (0.86 + 0.22*pnoise(seed + 2, n, 1.6, kmin=2.0)[..., None])
    img[mort] = col((172, 162, 147))*(0.82 + 0.22*pnoise(seed + 3, n, 0.5, kmin=20)[mort][..., None])
    return img, mort, d
# gap #12 (M12): the lime plaster is the OUTER layer. Height: lime ~0.85 > brick face ~0.35 > joints ~0.12, a 2-4 px sloped break
# band; baked micro-AO: dark contact shadow on the brick just inside the break, lit thick lip on the plaster edge (the M11 rim
# darkened the plaster OUTSIDE the break = read as brick on top). Normals saved at 1024 px (M11: 512 px for 4-8 m tiles).
PLT = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "params.json")))["houses"]["plaster_layer"]["tex"]
from scipy import ndimage
def pdist(mask):
    """periodic euclidean distance (px) from every pixel to the nearest pixel NOT in mask (0 outside the mask)"""
    n = mask.shape[0]; t = np.tile(mask, (3, 3)); d = ndimage.distance_transform_edt(t); return d[n:2*n, n:2*n]
def layered(m, bd, grain, base_img, brick_img, bmort):
    """lime layer over brick: m = brick exposed. returns albedo, height"""
    T = PLT; din = pdist(m); dout = pdist(~m)          # px into the brick / px into the plaster from the break
    hb = np.where(bmort, T["h_joint"], T["h_brick"] + 0.06*np.clip(bd/2.0 - 0.5, 0, 1))
    ramp = np.clip(1.0 - din/T["band_px"], 0, 1)       # sloped break band on the brick side (plaster edge slopes down to brick)
    h = np.where(m, hb + (T["h_lime"] - hb)*ramp**1.5, T["h_lime"]) + 0.04*grain
    ao = 1.0 - T["contact_k"]*np.exp(-np.maximum(din - T["band_px"]*0.6, 0)/T["contact_px"])   # contact shadow just inside the break
    img = np.where(m[..., None], brick_img*np.where(m, ao, 1.0)[..., None], base_img)
    edge = m & (ramp > 0.25)                            # broken plaster edge (fresh lime section) on the slope
    img = np.where(edge[..., None], base_img*T["edge_gain"]*(0.9 + 0.1*ramp)[..., None], img)
    lip = (~m) & (dout < T["lip_px"])                   # lit thick outer lip
    img = np.where(lip[..., None], np.clip(base_img*T["lip_gain"], 0, 1), img)
    return img, h
img, mort, d = brick_field(512, 2.0, 4, (156, 124, 105), var=0.4)
save_normal("brick_clean_n", np.where(mort, PLT["h_joint"], PLT["h_brick"] + 0.06*np.clip(d/2.0 - 0.5, 0, 1)) + 0.04*pnoise(24, 512, 0.4, kmin=40.0), PLT["slope_gain"])   # gap #12: bare bond (chimney brick_red)
# gap #12: lime residue = sharp-edged sheets lying ON the brick (height above the brick face, lit lip, contact shadow on the brick
# around them), not soft grey stains embedded in the bond (M11: smoothstep 0.52-0.62 and a height below the joint relief)
bare = img.copy()
lf = pnoise(23, 512, 1.9, kmin=1.5) + 0.06*pnoise(25, 512, 1.0, kmin=12.0); lime = lf > np.quantile(lf, PLT["residue_thr"])
lime = ndimage.binary_opening(np.tile(lime, (3, 3)), iterations=2)[512:1024, 512:1024]
grain = pnoise(24, 512, 0.4, kmin=40.0)
lt = col((182, 172, 160))[None, None]*(0.94 + 0.12*pnoise(26, 512, 1.4, kmin=4.0))[..., None]
img, hh = layered(~lime, d, grain, lt, img, mort)
s_ = sm(pnoise(15, 512, 1.6, kx=1.0, ky=6.0, kmin=3.0), 0.55, 0.95); img = img*(1 - 0.4*s_[..., None]) + col((60, 50, 44))*0.4*s_[..., None]
save("brick", img)
bare = bare*(1 - 0.4*s_[..., None]) + col((60, 50, 44))*0.4*s_[..., None]; save("brick_bare", bare)   # gap #12: brick seen through the skin holes
save_normal("brick_n", hh, PLT["slope_gain"], res=512)
# ---------------- plaster (M10): 1024 px over 4 m. Weathered lime render with large spalls exposing salmon brick (true scale) and a
# dark rim at the break, vertical runoff streaks, damp clouds. Tones (ref zones, compare/mat/wall_map.md):
#   A cream (iso W gable / fs W4 upper)            plaster_d  cream, heavy spalls (fs W4 / lw NW gable: big brick-showing areas)
#   B grey-beige half-timber infill (lw row)       C warm tan infill (iso east row)
def plaster(name, base, seed, cover, dirt=0.3, streaks=0.45, n=1024, tile=4.0):
    tone = pnoise(seed, n, 2.4, kmin=1.0); mott = pnoise(seed + 1, n, 1.6, kmin=3.0); grain = pnoise(seed + 2, n, 0.4, kmin=40.0)
    lum = 1.0 + 0.12*(tone - 0.5) + 0.08*(mott - 0.5) + 0.06*(grain - 0.5)
    img = col(base)[None, None]*lum[..., None]
    g = sm(pnoise(seed + 3, n, 1.7, kx=1.0, ky=7.0, kmin=4.0), 0.5, 0.95)
    img = img*(1 - streaks*g[..., None]) + col((92, 84, 74))*streaks*g[..., None]                 # runoff streaks
    dc = sm(pnoise(seed + 5, n, 2.0, kmin=1.5), 0.55, 0.9); img = img*(1 - dirt*dc[..., None])  # damp / dirt clouds
    sp = 0.88*pnoise(seed + 6, n, 2.6, kmin=2.0) + 0.12*pnoise(seed + 7, n, 1.6, kmin=10.0)       # ragged-edged spalls
    thr = np.quantile(sp, 1 - cover); m = sp > thr
    br, bm, bd = brick_field(n, tile, seed + 8, (160, 124, 104))
    br *= (0.82 + 0.2*pnoise(seed + 9, n, 1.5, kmin=3.0))[..., None]
    img, h = layered(m, bd, grain, img, br, bm)
    save(name, img); save_normal(name + "_n", h, PLT["slope_gain"], res=PLT["normal_res"])
# gap #12: fresh broken section of the lime coat (break edges of the skin holes / residue sheets): paler, no spalls, 1 m tile
n = 256; g1 = pnoise(541, n, 0.5, kmin=30.0); g2 = pnoise(542, n, 1.6, kmin=3.0)
g3 = sm(pnoise(543, n, 1.8, kmin=2.0), 0.45, 0.9)   # M12b: aged warm grey-white section (not bright white), light grime
save("plaster_edge", col(tuple(PLT["edge_rgb"]))[None, None]*(0.92 + 0.08*g1 + 0.06*g2 - 0.08*g3)[..., None])
plaster("plaster",   (190, 181, 168), 501, 0.12)
plaster("plaster_b", (160, 147, 134), 511, 0.18, dirt=0.2)
plaster("plaster_c", (170, 150, 131), 521, 0.22, dirt=0.2)
plaster("plaster_d", (202, 193, 184), 531, 0.44, dirt=0.18, streaks=0.3, n=2048, tile=8.0)   # 8 m tile (2048 px, same 256 px/m): big spalls without visible repeats
# ---------------- timber (M10): weathered grey-brown oak, ref lw row / iso (82,77,71)-(115,106,97): lighter + greyer than before
n = 512; gr = pnoise(8, n, 1.2, kx=10.0, ky=1.0, kmin=2.0); fine = pnoise(9, n, 0.6, kx=12.0, ky=1.0, kmin=10.0)
img = col((78, 68, 58))*(0.7 + 0.3*gr[..., None] + 0.14*fine[..., None])
sil = pnoise(10, n, 2.0, kmin=1.0); img = img*(1 - 0.4*sil[..., None]) + col((96, 90, 82))*0.4*sil[..., None]   # silvering
img = np.where((fine < 0.1)[..., None], img*0.55, img); save("timber", img)
# ---------------- window frames (gap #11): pale weathered painted oak (ref cross windows: light grey-cream casings / bars ~(176,170,160)),
# 256 px over 1 m, grain along u, flaking paint showing grey wood, grime
n = 256; gr = pnoise(61, n, 1.2, kx=10.0, ky=1.0, kmin=2.0); fl = pnoise(62, n, 1.8, kmin=3.0); gm = pnoise(63, n, 1.6, kmin=1.5)
img = col((178, 172, 161))*(0.9 + 0.1*gr[..., None]); peel = sm(fl, 0.72, 0.8)
img = img*(1 - peel[..., None]) + col((118, 110, 98))*(0.85 + 0.3*gr[..., None])*peel[..., None]
img *= (0.88 + 0.12*gm)[..., None]; save("wframe", img)
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
