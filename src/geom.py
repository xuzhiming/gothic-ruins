"""Tiny mesh-building library for build.py (pure python + mathutils; no bpy.ops).
Faces are collected per (group, material) bucket with world-space triplanar UVs; buckets become Blender objects."""
import math, zlib, random
from mathutils import Vector
from mathutils.geometry import tessellate_polygon

TEX_M = {"stone": 3.0, "rubble": 4.0, "slate": 2.0, "brick": 2.0, "brick_red": 2.0, "stair": 2.0, "stair_riser": 2.0, "stair_side": 2.0, "plaster": 4.0, "plaster_b": 4.0, "plaster_c": 4.0, "timber": 1.5, "cobble": 4.0,
         "iron": 1.0, "glass": 2.0, "soil": 6.0, "plinth": 4.0, "stone_moss": 3.0, "rubble_moss": 4.0}
# ---- ruin state (set by build.py from params.json "ruin"): None = intact model
RUIN = None            # the params dict
RR = random.Random(0)  # ruin rng (separate stream: the pre-ruin seeded layouts - roof holes, patches, braces - are unchanged)
DECAL = None           # {"streak"|"grime"|"crack"|"lath": Bucket}  alpha-blended decals (role decor, non-colliding)
MOSS_TOPS = False      # stone / rubble faces looking up (n.z > 0.8) go to the *_moss material
MOSSY = ("stone", "rubble")

def newell(pts):
    n = Vector((0, 0, 0))
    for i in range(len(pts)):
        a, b = pts[i], pts[(i + 1) % len(pts)]
        n.x += (a.y - b.y)*(a.z + b.z); n.y += (a.z - b.z)*(a.x + b.x); n.z += (a.x - b.x)*(a.y + b.y)
    return n

class Bucket:
    def __init__(self, group, mat):
        self.group, self.mat = group, mat; self.v = []; self.f = []; self.uv = []; self.s = TEX_M.get(mat, 2.0)
        # world-scale planar UVs (continuous across storeys / coplanar faces, same texel density everywhere); plaster gets a
        # deterministic per-group offset so neighbouring houses do not show the same tile phase
        h = zlib.crc32(group.encode()) if mat.startswith("plaster") else 0
        self.o = ((h % 997)/997.0, ((h // 997) % 991)/991.0)
    top = None
    uvframe = None   # (origin, u_dir, v_dir): slope-aligned world-scale UVs (roof slates: courses parallel to the eave), set by roof_slope
    def face(self, pts):
        pts = [Vector(p) for p in pts]
        n = newell(pts)
        if n.length < 1e-12: return
        if self.top is not None and n.z > 0.8*n.length: return self.top.face(pts)
        ax = max(range(3), key=lambda i: abs(n[i])); s = self.s
        b = len(self.v); self.v.extend(pts); self.f.append(tuple(range(b, b + len(pts))))
        if self.uvframe is not None:
            o, ua, ub = self.uvframe
            for p in pts: self.uv.append(((p - o).dot(ua)/s, (p - o).dot(ub)/s))
            return
        for p in pts:
            ox, oy = self.o
            if ax == 2: self.uv.append((p.x/s + ox, p.y/s + oy))
            elif ax == 0: self.uv.append((p.y/s + ox, p.z/s + oy))
            else: self.uv.append((p.x/s + ox, p.z/s + oy))
    def face_uv(self, pts, uvs):
        b = len(self.v); self.v.extend(Vector(p) for p in pts); self.f.append(tuple(range(b, b + len(pts)))); self.uv.extend(uvs)
    def nfaces(self): return len(self.f)

class Scene:
    def __init__(self): self.b = {}
    def B(self, group, mat):
        k = (group, mat)
        if k not in self.b:
            self.b[k] = Bucket(group, mat)
            if MOSS_TOPS and mat in MOSSY: self.b[k].top = self.B(group, mat + "_moss")
        return self.b[k]

# ---------------- primitives (all take a Bucket first) ----------------
BOX_FACES = [(0, 4, 6, 2), (1, 3, 7, 5), (0, 1, 5, 4), (2, 6, 7, 3), (0, 2, 3, 1), (4, 5, 7, 6)]
def obox(bk, c, ex, ey, ez, hx, hy, hz, skip=()):
    c = Vector(c); ex, ey, ez = Vector(ex), Vector(ey), Vector(ez)
    if ex.cross(ey).dot(ez) < 0: ez = -ez          # keep a right-handed frame -> outward face winding
    P = [c + ex*(hx if i & 1 else -hx) + ey*(hy if i & 2 else -hy) + ez*(hz if i & 4 else -hz) for i in range(8)]
    for k, f in enumerate(BOX_FACES):
        if k in skip: continue
        bk.face([P[i] for i in f])
def box(bk, x0, x1, y0, y1, z0, z1, skip=(), top=None):
    """axis aligned box; top=Bucket puts the +Z face in another bucket (e.g. cobble top on rubble block)"""
    if x1 < x0: x0, x1 = x1, x0
    if y1 < y0: y0, y1 = y1, y0
    if z1 < z0: z0, z1 = z1, z0
    if x1 - x0 < 1e-6 or y1 - y0 < 1e-6 or z1 - z0 < 1e-6: return
    c = ((x0 + x1)/2, (y0 + y1)/2, (z0 + z1)/2)
    sk = set(skip) | ({5} if top is not None else set())
    obox(bk, c, (1, 0, 0), (0, 1, 0), (0, 0, 1), (x1 - x0)/2, (y1 - y0)/2, (z1 - z0)/2, skip=sk)
    if top is not None and 5 not in skip:
        top.face([(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)])
def beam(bk, p0, p1, w, h, up=(0, 0, 1)):
    """box from p0 to p1 (centre line), width w (horizontal-ish), height h (along up projected)"""
    p0, p1 = Vector(p0), Vector(p1); d = p1 - p0; L = d.length
    if L < 1e-6: return
    ex = d/L; u = Vector(up)
    ey = u.cross(ex)
    if ey.length < 1e-6: ey = Vector((0, 1, 0)).cross(ex)
    ey.normalize(); ez = ex.cross(ey).normalized()
    obox(bk, (p0 + p1)/2, ex, ey, ez, L/2, w/2, h/2)
def ccw(poly):
    a = sum(poly[i][0]*poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0]*poly[i][1] for i in range(len(poly)))
    return poly if a > 0 else poly[::-1]
def dedupe(poly, eps=1e-5):
    out = []
    for p in poly:
        if not out or (abs(p[0] - out[-1][0]) > eps or abs(p[1] - out[-1][1]) > eps): out.append(p)
    if len(out) > 1 and abs(out[0][0] - out[-1][0]) < eps and abs(out[0][1] - out[-1][1]) < eps: out.pop()
    return out
def extrude(bk, poly, o, S, T, d, off=0.0, caps=True, sides=True, back=None):
    """extrude 2-D polygon (s,t) in plane (o; S,T) along N=S x T from off-d/2 .. off+d/2"""
    poly = ccw(dedupe(poly))
    if len(poly) < 3: return
    o, S, T = Vector(o), Vector(S), Vector(T); N = S.cross(T).normalized()
    F = [o + S*s + T*t + N*(off + d/2) for s, t in poly]; Bk = [o + S*s + T*t + N*(off - d/2) for s, t in poly]
    if caps:
        tris = tessellate_polygon([F])
        for tri in tris:
            a, b, c = F[tri[0]], F[tri[1]], F[tri[2]]
            if (b - a).cross(c - a).dot(N) < 0: tri = (tri[0], tri[2], tri[1])
            bk.face([F[i] for i in tri])
            bb = back or bk
            bb.face([Bk[tri[0]], Bk[tri[2]], Bk[tri[1]]])
    if sides:
        n = len(poly)
        for i in range(n):
            j = (i + 1) % n; bk.face([Bk[i], Bk[j], F[j], F[i]])
def prism(bk, poly, z0, z1, top=None):
    """vertical extrusion of plan polygon (x,y)"""
    extrude(bk, poly, (0, 0, (z0 + z1)/2), (1, 0, 0), (0, 1, 0), z1 - z0)
def ngon(cx, cy, r, n, rot=0.0):
    return [(cx + r*math.cos(rot + 2*math.pi*i/n), cy + r*math.sin(rot + 2*math.pi*i/n)) for i in range(n)]
def cyl(bk, cx, cy, r, z0, z1, n=8, rot=None):
    prism(bk, ngon(cx, cy, r, n, math.pi/n if rot is None else rot), z0, z1)
def cone(bk, cx, cy, r, z0, z1, n=8, rot=None, r1=0.0):
    rot = math.pi/n if rot is None else rot
    B0 = [Vector((x, y, z0)) for x, y in ngon(cx, cy, r, n, rot)]
    if r1 <= 1e-6:
        apex = Vector((cx, cy, z1))
        for i in range(n): bk.face([B0[i], B0[(i + 1) % n], apex])
    else:
        T0 = [Vector((x, y, z1)) for x, y in ngon(cx, cy, r1, n, rot)]
        for i in range(n): bk.face([B0[i], B0[(i + 1) % n], T0[(i + 1) % n], T0[i]])
        bk.face(T0)
    bk.face(B0[::-1])
PINNACLE_SPIKES = False   # set from params (cathedral.pinnacle_spikes) by build.py
def pinnacle(bk, cx, cy, z0, w, shaft_h, spire_h, finial=None):
    """square shaft + gabletted cap + octagonal spirelet (+ finial ball). Ruin: a share of pinnacles is snapped off
    (spirelet cut to 25-60 %, finial lost, a tilted broken stump on top) and some lose corner pinnaclets."""
    broken = RUIN is not None and RR.random() < RUIN["pinnacles"]["broken_frac"]
    chipped = RUIN is not None and RR.random() < RUIN["pinnacles"]["chipped_frac"]
    if broken:
        f = RR.uniform(*RUIN["pinnacles"]["broken_keep"]); zt = z0 + shaft_h + 0.18 + spire_h*f; rr = w*0.45*(1 - f)
        box(bk, cx - w/2, cx + w/2, cy - w/2, cy + w/2, z0, z0 + shaft_h)
        box(bk, cx - w*0.6, cx + w*0.6, cy - w*0.6, cy + w*0.6, z0 + shaft_h, z0 + shaft_h + 0.18)
        cone(bk, cx, cy, w*0.45, z0 + shaft_h + 0.18, zt, n=8, r1=rr)
        a = RR.uniform(0, math.pi); t = RR.uniform(0.25, 0.5)
        obox(bk, (cx, cy, zt + rr*0.3), (math.cos(a), math.sin(a), t), (-math.sin(a), math.cos(a), 0), (0, 0, 1), rr*0.8, rr*0.7, rr*0.35)
        return
    if chipped: PS = PINNACLE_SPIKES; globals()["PINNACLE_SPIKES"] = False
    box(bk, cx - w/2, cx + w/2, cy - w/2, cy + w/2, z0, z0 + shaft_h)
    box(bk, cx - w*0.6, cx + w*0.6, cy - w*0.6, cy + w*0.6, z0 + shaft_h, z0 + shaft_h + 0.18)
    cone(bk, cx, cy, w*0.45, z0 + shaft_h + 0.18, z0 + shaft_h + spire_h, n=8)
    if PINNACLE_SPIKES and spire_h > 1.2:   # four corner pinnaclets + a crocket band (reads as Gothic, adds slenderness)
        zt = z0 + shaft_h + 0.18
        for sx in (-1, 1):
            for sy in (-1, 1):
                cone(bk, cx + sx*w*0.48, cy + sy*w*0.48, w*0.13, zt, zt + spire_h*0.36, n=4, rot=math.pi/4)
        for f in (0.33, 0.62):
            zc = zt + (spire_h - 0.18)*f; rc = w*0.45*(1 - f)
            box(bk, cx - rc - 0.05, cx + rc + 0.05, cy - 0.04, cy + 0.04, zc - 0.06, zc + 0.06)
            box(bk, cx - 0.04, cx + 0.04, cy - rc - 0.05, cy + rc + 0.05, zc - 0.06, zc + 0.06)
    if chipped:
        globals()["PINNACLE_SPIKES"] = PS
        if PS and spire_h > 1.2:   # only two of the four corner pinnaclets survive
            zt = z0 + shaft_h + 0.18
            for sx, sy in ((-1, -1), (1, 1)): cone(bk, cx + sx*w*0.48, cy + sy*w*0.48, w*0.13, zt, zt + spire_h*0.36, n=4, rot=math.pi/4)
        finial = None
    if finial: cyl(finial, cx, cy, w*0.12, z0 + shaft_h + spire_h - 0.1, z0 + shaft_h + spire_h + 0.25, n=6)

# ---------------- arches ----------------
def arch_curve(x0, x1, spring, kind="pointed", k=1.0, n=10):
    """points from left spring to right spring over the arch (inclusive). pointed: radius = k*span"""
    w = x1 - x0; mid = (x0 + x1)/2
    if kind == "flat": return [(x0, spring), (x1, spring)]
    if kind == "round":
        r = w/2; return [(mid - r*math.cos(math.pi*i/n), spring + r*math.sin(math.pi*i/n)) for i in range(n + 1)]
    r = max(k*w, w/2 + 1e-4); cxL = x0 + r
    ta = math.acos((mid - cxL)/r)
    left = [(cxL + r*math.cos(math.pi + (ta - math.pi)*i/n), spring + r*math.sin(math.pi + (ta - math.pi)*i/n)) for i in range(n + 1)]
    left = [(x, spring + abs(y - spring)) for x, y in left]
    right = [(2*mid - x, y) for x, y in reversed(left[:-1])]
    return left + right
def arch_rise(w, kind="pointed", k=1.0):
    if kind == "flat": return 0.0
    if kind == "round": return w/2
    r = max(k*w, w/2 + 1e-4); return math.sqrt(r*r - (r - w/2)**2)
# ---------------- walls with openings ----------------
def decal(bk, o, S, T, N, s0, s1, za, zb, dn, flip, u0=0.0, us=None, uv01=False):
    """one alpha decal quad on a wall face: s0..s1 along S, za..zb (relative to o.z) at normal offset dn.
    u tiles along the wall (us m per texture repeat) unless uv01 (whole texture once). v = 0 bottom .. 1 top."""
    P = [o + S*s0 + T*za + N*dn, o + S*s1 + T*za + N*dn, o + S*s1 + T*zb + N*dn, o + S*s0 + T*zb + N*dn]
    if uv01: uv = [(0, 0), (1, 0), (1, 1), (0, 1)]
    else:
        us = us or (s1 - s0); uv = [(u0, 0), (u0 + (s1 - s0)/us, 0), (u0 + (s1 - s0)/us, 1), (u0, 1)]
    if flip: P = P[::-1]; uv = uv[::-1]
    bk.face_uv(P, uv)
def wall_decals(o, S, T, N, L, H, t, off, ops, wx):
    """weathering decals on one or both faces of a wall: soot/runoff streaks under every sill and from the wall top, ground
    grime band (broken at doors, kept below sills), cracks / spalled stones and (plaster) fallen-off patches showing lath.
    Nothing is placed over an opening."""
    W = RUIN["weather"]; side = wx.get("side", 0)
    if "out" in wx: side = 1 if N.dot(Vector((wx["out"][0], wx["out"][1], 0))) > 0 else -1
    def hits(a, b, za, zb, pad=0.05):
        return any(a < q["s"] + q["w"]/2 + pad and b > q["s"] - q["w"]/2 - pad and zb > q.get("sill", 0.0) - pad and za < q["h"] + pad for q in ops)
    for sd in ([side] if side else [1, -1]):
        jit = lambda: RR.uniform(0, 0.003)
        for q in ops:   # streaks below sills
            sill = q.get("sill", 0.0)
            if sill > 0.35 and RR.random() < W["sill_streak_p"]:
                a, b = q["s"] - q["w"]*0.6, q["s"] + q["w"]*0.6; zb_ = sill; za_ = max(0.02, sill - RR.uniform(*W["sill_streak_len"]))
                if not hits(a, b, za_, zb_ - 0.02, 0.0): decal(DECAL["streak"], o, S, T, N, a, b, za_, zb_, off + sd*(t/2 + 0.012 + jit()), sd < 0, RR.random(), 1.5)
        if wx.get("top", True):   # runoff from the wall top / cornice
            for _ in range(int(L*W["top_streaks_per_m"] + RR.random())):
                w_ = RR.uniform(0.8, 2.4); s_ = RR.uniform(w_/2, max(w_/2, L - w_/2)); a, b = s_ - w_/2, s_ + w_/2
                zb_ = H - 0.02; za_ = max(0.05, zb_ - RR.uniform(*W["top_streak_len"]))
                lim = [q["h"] for q in ops if a < q["s"] + q["w"]/2 and b > q["s"] - q["w"]/2]
                if lim: za_ = max(za_, max(lim) + 0.08)
                if zb_ - za_ > 0.5: decal(DECAL["streak"], o, S, T, N, a, b, za_, zb_, off + sd*(t/2 + 0.014 + jit()), sd < 0, RR.random(), 1.5)
        if wx.get("ground"):   # grime / splash band, cut at doors, kept under sills
            cuts = sorted([(q["s"] - q["w"]/2, q["s"] + q["w"]/2, q.get("sill", 0.0)) for q in ops], key=lambda c: c[0])
            hb = RR.uniform(*W["ground_band_h"]); xs = [0.0]
            for a, b, sl in cuts: xs += [max(0.0, a), min(L, b)]
            xs.append(L); xs = sorted(set(round(x, 4) for x in xs))
            for a, b in zip(xs, xs[1:]):
                if b - a < 0.05: continue
                m = (a + b)/2; under = [sl for (ca, cb, sl) in cuts if ca - 1e-4 <= m <= cb + 1e-4]
                h_ = hb if not under else min(hb, min(under) - 0.03)
                if h_ > 0.15: decal(DECAL["grime"], o, S, T, N, a, b, 0.0, h_, off + sd*(t/2 + 0.016 + jit()), sd < 0, a/3.0, 3.0)
        for kind, dens in (("crack", wx.get("cracks", 0.0)), ("lath", wx.get("lath", 0.0))):
            area = L*H; n = int(area*dens + RR.random())
            for _ in range(n*4):
                if n <= 0: break
                sz = RR.uniform(*W[kind + "_size"]); s_ = RR.uniform(sz/2, max(sz/2, L - sz/2)); z_ = RR.uniform(0.3, max(0.3, H - sz - 0.2))
                if s_ - sz/2 < 0 or s_ + sz/2 > L or z_ + sz > H or hits(s_ - sz/2, s_ + sz/2, z_, z_ + sz): continue
                decal(DECAL[kind], o, S, T, N, s_ - sz/2, s_ + sz/2, z_, z_ + sz, off + sd*(t/2 + (0.02 if kind == "crack" else 0.01) + jit()), sd < 0, uv01=True); n -= 1
def wall(bk, p0, p1, z0, z1, t, openings=(), glass=None, frame=None, off=0.0, wx=None):
    """straight wall p0->p1 (plan points), z0..z1, thickness t centred on the line (+off along normal).
    openings: dicts {s: centre along wall (m from p0), w, sill (above z0), h (apex above z0), kind, k, glass(bool), mull(int)}
    returns list of opening frames (for door records)."""
    p0, p1 = Vector((p0[0], p0[1], 0)), Vector((p1[0], p1[1], 0)); d = p1 - p0; L = d.length; S = d/L; T = Vector((0, 0, 1))
    o = p0 + Vector((0, 0, z0)); H = z1 - z0
    ops = sorted(openings, key=lambda q: q["s"]); cur = 0.0
    for q in ops:
        a, b = q["s"] - q["w"]/2, q["s"] + q["w"]/2
        if a > cur + 1e-4: extrude(bk, [(cur, 0), (a, 0), (a, H), (cur, H)], o, S, T, t, off)
        kind = q.get("kind", "pointed"); k = q.get("k", 1.0)
        sill = q.get("sill", 0.0); top = min(q["h"], H)
        if sill > 1e-4: extrude(bk, [(a, 0), (b, 0), (b, sill), (a, sill)], o, S, T, t, off)
        rise = arch_rise(b - a, kind, k); spring = top - rise
        if top < H - 1e-4:
            curve = arch_curve(a, b, spring, kind, k)
            # polygon: right spring -> over the arch back to left spring -> top-left -> top-right
            poly = ([(a, spring), (b, spring), (b, H), (a, H)] if kind == "flat" else [curve[-1], (b, H), (a, H)] + curve[:-1])
            extrude(bk, poly, o, S, T, t, off)
        lost = RUIN is not None and RR.random() < RUIN["glass"]["missing_cathedral" if frame is not None and frame.group == "Tracery" else "missing_house"]
        if q.get("glass") and glass is not None:
            outline = [(a, sill)] + [(b, sill)] + ([(b, spring), (a, spring)] if kind == "flat" else list(reversed(arch_curve(a, b, spring, kind, k))))
            if not lost: extrude(glass, outline, o, S, T, 0.05, off)   # ruin: pane lost -> dark empty opening
            if frame is not None:
                m = q.get("mull", 1)
                for i in range(1, m + 1):
                    sx = a + (b - a)*i/(m + 1)
                    if lost and RR.random() < RUIN["glass"]["mullion_lost_if_pane_lost"]: continue   # broken tracery
                    extrude(frame, [(sx - 0.06, sill), (sx + 0.06, sill), (sx + 0.06, spring + rise*0.6), (sx - 0.06, spring + rise*0.6)], o, S, T, 0.14, off)
                if q.get("transom", True) and spring - sill > 1.2 and not (lost and RR.random() < 0.5):
                    zt = sill + (spring - sill)*0.55
                    extrude(frame, [(a, zt - 0.05), (b, zt - 0.05), (b, zt + 0.05), (a, zt + 0.05)], o, S, T, 0.14, off)
        cur = b
    if cur < L - 1e-4: extrude(bk, [(cur, 0), (L, 0), (L, H), (cur, H)], o, S, T, t, off)
    N = S.cross(T)
    if wx and RUIN is not None and DECAL is not None: wall_decals(o, S, T, N, L, H, t, off, ops, wx)
    return {"S": S, "N": N, "o": o, "L": L}
def gable(bk, p0, p1, z0, z_apex, t, off=0.0):
    """triangular gable wall on top of a wall p0->p1 at z0, apex at mid"""
    p0, p1 = Vector((p0[0], p0[1], 0)), Vector((p1[0], p1[1], 0)); d = p1 - p0; L = d.length
    extrude(bk, [(0, 0), (L, 0), (L/2, z_apex - z0)], p0 + Vector((0, 0, z0)), d/L, (0, 0, 1), t, off)
def relief_arch(bk, p0, p1, s, w, z_sill, z_apex, depth, out, kind="pointed", k=1.0, ring=None):
    """decorative (blind) window/arch panel on a wall face: panel of thickness depth, centred `out` m along the normal"""
    p0, p1 = Vector((p0[0], p0[1], 0)), Vector((p1[0], p1[1], 0)); d = p1 - p0; L = d.length; S = d/L
    a, b = s - w/2, s + w/2; rise = arch_rise(w, kind, k); spring = z_apex - rise
    outline = [(a, z_sill), (b, z_sill)] + list(reversed(arch_curve(a, b, spring, kind, k)))
    if depth > 0: extrude(bk, outline, p0, S, (0, 0, 1), depth, out)
    if ring is not None:   # moulded frame ring 0.2 m wide
        oc = arch_curve(a - 0.22, b + 0.22, spring, kind, k*(w/(w + 0.44)) if kind == "pointed" else k)
        # frame as thin strips along the outline
        pts = [(a - 0.22, z_sill - 0.15)] + oc + [(b + 0.22, z_sill - 0.15)]
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            ex = Vector((x1 - x0, y1 - y0)); 
            if ex.length < 1e-6: continue
            nn = Vector((-ex.y, ex.x)).normalized()*0.11
            q = [(x0 - nn.x, y0 - nn.y), (x1 - nn.x, y1 - nn.y), (x1 + nn.x, y1 + nn.y), (x0 + nn.x, y0 + nn.y)]
            extrude(ring, q, p0, S, (0, 0, 1), depth + 0.12, out + 0.04)

# ---------------- stairs ----------------
def stair(bk, x0, x1, y0, y1, z0, n, riser, axis, direction, top=None, base=None, sides=None):
    """flight of n risers inside plan rect (x0..x1, y0..y1). axis 'x' or 'y' = run direction; direction +1/-1
    = ascending toward + or - along the axis. The n-th riser lands on the upper floor at the far end
    (n-1 step blocks are built; the last tread is the landing). Solid down to `base` (default z0).
    Returns list of tread centres (n-1 blocks + landing start) and tread depth."""
    base = z0 if base is None else base
    L = (x1 - x0) if axis == "x" else (y1 - y0); t = L/n
    cents = []
    for k in range(n):
        ztop = z0 + (k + 1)*riser
        if direction > 0: a, b = k*t, (k + 1)*t
        else: a, b = L - (k + 1)*t, L - k*t
        if k < n - 1:
            bb = (x0 + a, x0 + b, y0, y1) if axis == "x" else (x0, x1, y0 + a, y0 + b)
            if sides is None:
                box(bk, *bb, base, ztop, top=top)
            else:   # gap #9: per-step aligned UVs. Tread = one 0.4 m texture row per tread (front edge of the row = nosing),
                    # riser = one row per riser height (top of row under the nosing, bottom = grime corner); stringer sides world UV
                run = Vector((1, 0, 0)) if axis == "x" else Vector((0, 1, 0)); acr = Vector((0, 1, 0)) if axis == "x" else Vector((1, 0, 0))
                j = k % 5; nos = (x0 + a if direction > 0 else x0 + b) if axis == "x" else (y0 + a if direction > 0 else y0 + b)
                lat = ((k*0.37) % 1.0)*2.0
                o = run*nos + acr*(-lat); dirn = run*direction
                top.uvframe = (o - dirn*(j*t), acr, dirn*(0.4/t))
                bk.uvframe = (o + Vector((0, 0, ztop - riser - j*riser)) + acr*(-0.61*k), acr, Vector((0, 0, 0.4/riser)))
                fr_ = (2, 3) if axis == "y" else (0, 1); sd = (0, 1) if axis == "y" else (2, 3)
                box(bk, *bb, base, ztop, skip=sd + (4,), top=top); box(sides, *bb, base, ztop, skip=fr_ + (5,))
                top.uvframe = None; bk.uvframe = None
        cx = (x0 + x1)/2 if axis == "y" else x0 + (a + b)/2; cy = (y0 + y1)/2 if axis == "x" else y0 + (a + b)/2
        cents.append([round(cx, 3), round(cy, 3), round(ztop, 3)])
    return cents, t
