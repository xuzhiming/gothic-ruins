# =====================================================================================
# build.py - procedural reconstruction of the ruined Gothic cathedral complex.
#   blender -b -P build.py            (env: PARAMS=params.json  OUTDIR=.  NO_EXPORT=1  SIL_ONLY=1)
# Every dimension comes from params.json (see params.md). Order of work:
#   1. plinth / plaza / terraces / monumental stairs / balustrades / bollards
#   2. cathedral: spaces first (nave, aisles, ambulatory, towers, parvis), then walls with
#      openings, piers/columns, buttresses + flyers, roofs (partly collapsed), spire, interior fittings
#   3. townhouses: per-house plan (front/back room x floors), then walls, floors with stair holes,
#      stairs, partitions + doors, roofs with holes, chimneys, dormers, timber framing
#   4. spaces.json (circulation graph: spaces, doors, stairs, open links) + .blend + .glb
# =====================================================================================
import bpy, json, math, os, sys, random, time
ROOT = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(ROOT, "src"))
import importlib, geom; importlib.reload(geom)
from geom import *
from mathutils import Vector
T0 = time.time()
P = json.load(open(os.environ.get("PARAMS", os.path.join(ROOT, "params.json"))))
OUT = os.environ.get("OUTDIR", ROOT); os.makedirs(OUT, exist_ok=True)
SIL_ONLY = bool(os.environ.get("SIL_ONLY"))
# ---- ruin / decay (gap #4): params.json "ruin" (documented in params.md). Separate seeded streams so the pre-ruin layouts stay put.
RU = P["ruin"] if P.get("ruin", {}).get("enabled") else None
geom.RUIN = RU; geom.RR = random.Random(RU["seed"] if RU else 0); geom.MOSS_TOPS = bool(RU and RU.get("moss_tops"))
RR = geom.RR; RRo = random.Random((RU or {}).get("seed", 0) + 1)
# ---- per-element random streams (gap #6). The ruin draws used to run as one sequence through the whole build, so a change in one
# element (e.g. the apse position) re-rolled every later element (nave roof holes, chimneys, rubble...). Now every element starts at a
# named pin: ruin_streams.json holds the stream states recorded at each pin in the approved build (DUMP_STREAMS=1 records them), so
# unchanged elements keep the approved layout exactly; a pin missing from the file gets its own seed from the element name.
PIN_FILE = os.path.join(ROOT, "ruin_streams.json"); DUMP_PINS = bool(os.environ.get("DUMP_STREAMS"))
STREAMS = {"RR": RR, "RRo": RRo}; PINS_USED = []
_PINS = {} if DUMP_PINS else (json.load(open(PIN_FILE)) if os.path.exists(PIN_FILE) else {})
def pin(name):
    PINS_USED.append(name)
    if DUMP_PINS: _PINS[name] = {k: [st.getstate()[0], list(st.getstate()[1]), None] for k, st in STREAMS.items()}; return
    rec = _PINS.get(name, {})
    for k, st in STREAMS.items():
        if k in rec: st.setstate((rec[k][0], tuple(rec[k][1]), None))
        else: st.seed(f"{(RU or {}).get('seed', 0)}:{name}:{k}")
SC = Scene()
geom.DECAL = {k: SC.B("Decal", "decal_" + k) for k in ("streak", "grime", "crack", "lath")} if RU else None
WXC = lambda **k: dict({"cracks": RU["weather"]["cracks_cathedral"]} if RU else {}, **k)   # cathedral wall weathering spec
SP = {"spaces": {}, "doors": [], "stairs": [], "lifts": [], "open_links": [], "entrance": "approach"}
LEAVES = []          # (name, Bucket, hinge Vector, props)
R2 = lambda v: [round(float(x), 3) for x in v]

def space(sid, probe, kind, **kw):
    SP["spaces"][sid] = {"probe": R2(probe), "z": round(probe[2], 3), "kind": kind, **kw}
def door_rec(did, a, b, center, normal, w, h, typ, check_wall=True, wall_probe_h=1.0, leaves=()):
    n = Vector((normal[0], normal[1], 0)).normalized()
    SP["doors"].append({"id": did, "a": a, "b": b, "center": R2(center), "normal": R2(n), "tangent": R2((-n.y, n.x, 0)),
                        "w": w, "h": h, "type": typ, "check_wall": check_wall, "wall_probe_h": wall_probe_h, "leaves": list(leaves)})
def stair_rec(sid, a, b, steps, riser, tread, entry, exit_, width, headroom_min=2.1):
    SP["stairs"].append({"id": sid, "a": a, "b": b, "steps": steps, "riser": round(riser, 4), "tread": round(tread, 4),
                         "entry": R2(entry), "exit": R2(exit_), "width": width, "headroom_min": headroom_min})
def open_link(a, b, path):
    SP["open_links"].append({"a": a, "b": b, "path": [R2(p) for p in path]})

def add_leaf(name, door_id, hinge, tvec, nvec, w, h, z0, thick=0.09, mat="timber", bars=False):
    """door leaf (closed) from hinge along tvec; swings toward +nvec. Origin of the object = hinge."""
    bk = Bucket("Leaf", mat); hinge = Vector(hinge); t = Vector(tvec).normalized(); n = Vector(nvec).normalized()
    c = hinge + t*(w/2) + Vector((0, 0, z0 + h/2 - hinge.z))
    if bars:   # iron gate leaf: frame + vertical bars + spear tips
        for zz in (z0 + 0.15, z0 + h*0.55, z0 + h - 0.1):
            obox(bk, hinge + t*(w/2) + Vector((0, 0, zz - hinge.z)), t, n, (0, 0, 1), w/2, 0.03, 0.04)
        k = max(2, int(w/0.14))
        for i in range(k + 1):
            p = hinge + t*(0.03 + (w - 0.06)*i/k)
            obox(bk, p + Vector((0, 0, z0 + h/2 - hinge.z)), t, n, (0, 0, 1), 0.018, 0.018, h/2)
            cone(bk, p.x, p.y, 0.05, z0 + h, z0 + h + 0.16, n=4)
    else:
        obox(bk, c, t, n, (0, 0, 1), w/2 - 0.01, thick/2, h/2 - 0.01)
        for zz in (0.25, 0.75):   # iron straps
            obox(bk, hinge + t*(w*0.45) + n*(-thick/2 - 0.012) + Vector((0, 0, z0 + h*zz - hinge.z)), t, n, (0, 0, 1), w*0.4, 0.012, 0.05)
    swing = 1.0 if Vector((0, 0, 1)).cross(t).dot(n) > 0 else -1.0
    LEAVES.append((name, bk, hinge, {"door_id": door_id, "swing": swing*math.radians(86), "role": "door_leaf"}))
    return name

ST = P["site"]; PZ = ST["plaza_z"]; TZ = ST["terrace_z"]
# =====================================================================================
# 1. plinth, plaza, terraces, stairs
# =====================================================================================
rub = SC.B("Plinth", "rubble"); cob = SC.B("Plaza", "cobble"); bst = SC.B("Balustrade", "stone")
DEB_st = SC.B("Debris", "stone"); DEB_rb = SC.B("Debris", "rubble"); DEB_sl = SC.B("Debris", "slate"); DEB_tb = SC.B("Debris", "timber"); DEB_br = SC.B("Debris", "brick")
for key, z in (("main", PZ), ("north_band", PZ), ("tongue", PZ), ("strip", TZ)):
    x0, x1, y0, y1 = ST[key]; box(rub, x0, x1, y0, y1, 0, z, top=cob)
tx0, tx1, ty0, ty1 = ST["terrace"]; ux = P["stairs_south"]["upper"]["x"][1]
for sg in (-1, 1):
    box(rub, sg*ux, sg*tx1, ty0, ty1, 0, TZ, top=cob)
box(rub, -ux, ux, ty0, P["stairs_south"]["upper"]["y_top"], 0, TZ)        # under the upper flight
ap = ST["approach"]; box(SC.B("Approach", "rubble"), ap[0], ap[1], ap[2], ap[3], -0.3, 0.0, top=SC.B("Approach", "cobble"))
base = SC.B("Base", "soil")
box(base, -31.8, 31.8, -51.4, 51.4, -3.2, 0.0, skip=(5,))
# monumental stairs (south): lower flight ground -> landing strip (TZ), upper flight -> plaza (PZ)
SS = P["stairs_south"]; stp = SC.B("Stairs", "stair_riser")   # gap #9: treads "stair", risers "stair_riser", stringers "stair_side"
STK = dict(top=SC.B("Stairs", "stair"), sides=SC.B("Stairs", "stair_side"))
lo, up = SS["lower"], SS["upper"]
c_lo, t_lo = stair(stp, lo["x"][0], lo["x"][1], lo["y_bot"], lo["y_top"], 0.0, lo["n"], TZ/lo["n"], "y", +1, base=0.0, **STK)
c_up, t_up = stair(stp, up["x"][0], up["x"][1], up["y_bot"], up["y_top"], TZ, up["n"], (PZ - TZ)/up["n"], "y", +1, base=0.0, **STK)
space("approach", (0, (ap[2] + ap[3])/2 + 1.0, 0.0), "outdoor")
space("landing", (0, (ST["strip"][2] + ST["strip"][3])/2, TZ), "outdoor")
space("plaza", (0, -12.0, PZ), "outdoor")
for sg, nm in ((-1, "terrace_W"), (1, "terrace_E")): space(nm, (sg*21.0, -37.0, TZ), "outdoor")
stair_rec("stairs_south_lower", "approach", "landing", c_lo[:-1], TZ/lo["n"], t_lo, (0, lo["y_bot"] - 1.0, 0), (0, lo["y_top"] + 1.2, TZ), lo["x"][1] - lo["x"][0], 2.1)
stair_rec("stairs_south_upper", "landing", "plaza", c_up[:-1], (PZ - TZ)/up["n"], t_up, (0, up["y_bot"] - 1.2, TZ), (0, up["y_top"] + 1.5, PZ), up["x"][1] - up["x"][0], 2.1)
open_link("landing", "terrace_W", [(0, -43.6, TZ), (-12, -43.6, TZ), (-21, -37, TZ)])
open_link("landing", "terrace_E", [(0, -43.6, TZ), (12, -43.6, TZ), (21, -37, TZ)])

BH = ST["balustrade_h"]
def balustrade(p0, p1, z, h=BH, bk=bst):
    p0, p1 = Vector((p0[0], p0[1], z)), Vector((p1[0], p1[1], z)); d = p1 - p0; L = d.length
    if L < 0.3: return
    beam(bk, p0 + Vector((0, 0, 0.14)), p1 + Vector((0, 0, 0.14)), 0.46, 0.28)
    BR = RU["balustrade"] if RU else None; k = max(1, int(L/1.6)); gaps = []
    for i in range(k):   # coping rail in pieces; ruin: some pieces fallen (lying on the base rail, as decor)
        f0, f1 = i/k, (i + 1)/k
        if BR and RR.random() < BR["rail_gap_p"]:
            gaps.append((f0, f1)); a = p0 + d*(f0 + 0.08/k) + Vector((0, 0, 0.36)); b = p0 + d*(f1 - 0.25/k) + Vector((0, 0, 0.36))
            sh = Vector((-d.y, d.x, 0))/L*RR.uniform(-0.12, 0.12); beam(DEB_st, a + sh, b - sh + Vector((0, 0, RR.uniform(0.0, 0.12))), 0.4, 0.15)
        else: beam(bk, p0 + d*f0 + Vector((0, 0, h - 0.08)), p0 + d*f1 + Vector((0, 0, h - 0.08)), 0.42, 0.16)
    ing = lambda f: any(a - 0.02 <= f <= b + 0.02 for a, b in gaps)
    n = max(1, int(L/0.62))
    for i in range(n):   # little arcade columns + round arch heads (ruin: some missing, some snapped under a lost rail)
        c = p0 + d*((i + 0.5)/n); hh = (h - 0.44)
        if BR and RR.random() < BR["baluster_missing"]: continue
        if BR and ing((i + 0.5)/n) and RR.random() < 0.6: hh *= RR.uniform(0.3, 0.75)
        obox(bk, c + Vector((0, 0, 0.28 + hh/2)), d/L, Vector((-d.y, d.x, 0))/L, (0, 0, 1), 0.07, 0.07, hh/2)
    for i in range(n + 1):
        if BR and ing(i/n): continue
        c = p0 + d*(i/n); obox(bk, c + Vector((0, 0, h - 0.24)), d/L, Vector((-d.y, d.x, 0))/L, (0, 0, 1), 0.12, 0.17, 0.08)
def post(x, y, z, w=ST["post_w"], h=ST["post_h"], bk=bst):
    box(bk, x - w/2, x + w/2, y - w/2, y + w/2, z, z + h)
    box(bk, x - w*0.62, x + w*0.62, y - w*0.62, y + w*0.62, z + h, z + h + 0.22)
    if RU and RR.random() < RU["balustrade"]["post_cap_lost"]:   # ruin: pyramid cap knocked off (lies at the foot, decor)
        cone(bk, x, y, w*0.55, z + h + 0.22, z + h + 0.38, n=4, rot=math.pi/4, r1=w*0.3)
        a = RR.uniform(0, 6.283); obox(DEB_st, (x + math.cos(a)*(w*0.5 + 0.35), y + math.sin(a)*(w*0.5 + 0.35), z + 0.14), (math.cos(a), math.sin(a), 0.3), (-math.sin(a), math.cos(a), 0), (0, 0, 1), w*0.32, w*0.3, 0.14)
    else: cone(bk, x, y, w*0.55, z + h + 0.22, z + h + 0.7, n=4, rot=math.pi/4)
def cheek(xa, xb, yb, yt, zb, zt, h=1.0, bk=bst):
    """sloped solid cheek wall beside a flight (plan strip xa..xb, from (yb,zb) to (yt,zt))"""
    extrude(bk, [(yb, zb - 0.0 if zb > 0 else 0.0), (yt, zb if zb > 0 else 0.0), (yt, zt + h), (yb, zb + h)][0:0] or
            [(yb, 0.0), (yt, 0.0), (yt, zt + h), (yb, zb + h)], ((xa + xb)/2, 0, 0), (0, 1, 0), (0, 0, 1), abs(xb - xa))
tm = ST["main"]; tg = ST["tongue"]; strip = ST["strip"]; hx0 = P["houses"]["row_x"][0]
for sg in (-1, 1):
    balustrade((sg*tg[1], tm[2] + 0.25), (sg*hx0, tm[2] + 0.25), PZ)                      # plaza south edge (beside the tongue)
    balustrade((sg*(tg[1] - 0.25), tg[2]), (sg*(tg[1] - 0.25), tg[3]), PZ)                  # tongue sides
    balustrade((sg*(ux + 0.5), tg[2] + 0.25), (sg*tg[1], tg[2] + 0.25), PZ)                 # tongue south edge
    balustrade((sg*strip[1], ty0 + 0.25), (sg*tx1, ty0 + 0.25), TZ)                         # terrace south edge
    balustrade((sg*(tx1 - 0.25), ty0), (sg*(tx1 - 0.25), ty1), TZ)                          # terrace outer edge
    balustrade((sg*(lo["x"][1] + 0.5), strip[2] + 0.25), (sg*strip[1], strip[2] + 0.25), TZ)  # landing strip south edge
    balustrade((sg*(strip[1] - 0.25), strip[2]), (sg*(strip[1] - 0.25), strip[3]), TZ)      # strip ends
    cheek(sg*ux, sg*(ux + 0.5), up["y_bot"], up["y_top"], TZ, PZ)
    cheek(sg*lo["x"][1], sg*(lo["x"][1] + 0.5), lo["y_bot"], lo["y_top"], 0.0, TZ)
    for (x, y, z) in ((tg[1], tm[2], PZ), (hx0 - 0.3, tm[2], PZ), (tg[1], tg[2], PZ), (ux + 0.25, tg[2], PZ), (ux + 0.25, up["y_bot"], TZ),
                      (lo["x"][1] + 0.25, strip[2], TZ), (strip[1], strip[2], TZ), (strip[1], ty0, TZ), (tx1, ty0, TZ), (tx1, ty1, TZ),
                      (lo["x"][1] + 0.25, lo["y_bot"] + 0.3, 0.0)):
        post(sg*x, y, z)
    nb_ = ST["north_band"]
    balustrade((sg*(nb_[1] - 0.25), nb_[2]), (sg*(nb_[1] - 0.25), nb_[3]), PZ, h=ST["parapet_h"], bk=rub)
    balustrade((sg*10.2, nb_[3] - 0.25), (sg*(nb_[1]), nb_[3] - 0.25), PZ, h=ST["parapet_h"], bk=rub)

# bollards + chains (U: semicircle to the south + straight legs to y_end)
BO = P["bollards"]; bol = SC.B("Bollards", "stone"); iron = SC.B("Iron", "iron")
pts = []; r = BO["r"]
L_leg = BO["y_end"] - BO["cy"]; L_arc = math.pi*r; Ltot = 2*L_leg + L_arc; nbol = max(4, int(round(Ltot/BO["pitch"])))
def upath(s):
    if s < L_leg: return (-r, BO["y_end"] - s)
    s -= L_leg
    if s < L_arc: a = math.pi + s/r; return (BO["cx"] + r*math.cos(a), BO["cy"] + r*math.sin(a))
    s -= L_arc; return (r, BO["cy"] + s)
bpts = [upath(Ltot*i/nbol) for i in range(nbol + 1)]
for (x, y) in bpts:
    cyl(bol, x, y, BO["d"]/2, PZ, PZ + BO["h"], n=8); cone(bol, x, y, BO["d"]*0.62, PZ + BO["h"], PZ + BO["h"] + 0.18, n=8)
for (xa, ya), (xb, yb) in zip(bpts, bpts[1:]):
    seg = 6; prev = None
    for k in range(seg + 1):
        f = k/seg; p = Vector((xa + (xb - xa)*f, ya + (yb - ya)*f, PZ + BO["chain_z"] - BO["sag"]*4*f*(1 - f)))
        if prev is not None: beam(iron, prev, p, 0.05, 0.05)
        prev = p

# =====================================================================================
# 2. cathedral
# =====================================================================================
C = P["cathedral"]; ZC = PZ + C["podium_h"]; A = C["apse"]; cy = A["cy"]
geom.PINNACLE_SPIKES = bool(C.get("pinnacle_spikes", False))
nhw, ahw, wt = C["nave_hw"], C["aisle_hw"], C["wall_t"]; yF, yB, NB = C["y_front"], C["y_back"], C["bays"]
bay = (yB - yF)/NB; bayY = [yF + i*bay for i in range(NB + 1)]
cs = SC.B("Cathedral", "stone"); crub = SC.B("Cathedral", "rubble"); glass = SC.B("Glass", "glass"); cfr = SC.B("Tracery", "stone")
slate = SC.B("CathRoof", "slate"); ctim = SC.B("CathRoof", "timber"); fin = SC.B("Finials", "iron")
stc = C["steps"]; y_pod = stc["y0"] + (stc["n"] - 1)*stc["tread"]
# --- podium (raised base) + steps
PODX = ahw + 0.5 + C["buttress_out"] + 0.3
box(crub, -PODX, PODX, y_pod, yB + 0.7, PZ - 0.01, ZC, top=cs)
RPOD = A["r_pier"] + 0.9
box(crub, -RPOD, RPOD, yB, cy, PZ - 0.01, ZC, top=cs)
hp = [(RPOD*math.cos(math.pi*i/12), cy + RPOD*math.sin(math.pi*i/12)) for i in range(13)]
extrude(cs, hp, (0, 0, (PZ + ZC)/2), (1, 0, 0), (0, 1, 0), ZC - PZ)
c_cs, t_cs = stair(SC.B("Stairs", "stair_riser"), stc["x"][0], stc["x"][1], stc["y0"], stc["y0"] + stc["n"]*stc["tread"], PZ, stc["n"], C["podium_h"]/stc["n"], "y", +1, base=PZ - 0.01, **STK)
for sg in (-1, 1): cheek(sg*stc["x"][1], sg*(stc["x"][1] + 0.5), stc["y0"], y_pod, PZ, ZC, h=0.9)
space("parvis", (0, (y_pod + yF - wt/2)/2, ZC), "outdoor")
stair_rec("cathedral_steps", "plaza", "parvis", c_cs[:-1], C["podium_h"]/stc["n"], t_cs, (0, stc["y0"] - 1.2, PZ), (0, y_pod + 0.6, ZC), stc["x"][1] - stc["x"][0], 2.1)

# --- spaces (plan first)
space("nave", (0, 20.0, ZC), "cathedral"); space("aisle_W", (-(nhw + ahw)/2, 22.0, ZC), "cathedral"); space("aisle_E", ((nhw + ahw)/2, 22.0, ZC), "cathedral")
space("ambulatory", (0, cy + (A["r_in"] + A["r_amb"])/2, ZC), "cathedral")
space("tower_SW", (-(nhw + ahw)/2 - 0.2, (yF + bayY[1])/2, ZC), "cathedral"); space("tower_SE", ((nhw + ahw)/2 + 0.2, (yF + bayY[1])/2, ZC), "cathedral")

def lancet(s, w, sill, apex, k=0.9, mull=1):
    return {"s": s, "w": w, "sill": sill, "h": apex, "kind": "pointed", "k": k, "glass": True, "mull": mull}
NWT = C["nave_wall_top"]; AWT = C["aisle_wall_top"]
# --- facade (nave front wall) with portal (flat lintel + tympanum) and gable
fx = nhw + wt/2
fr = wall(cs, (-fx, yF), (fx, yF), ZC, NWT, wt, [{"s": fx, "w": C["portal_w"], "h": C["portal_h"] - 1.0, "kind": "flat"}], wx=WXC(side=1, top=False, ground=True))
gable(cs, (-fx, yF), (fx, yF), NWT, C["facade_apex"], wt)
pw = C["portal_w"]
for i, ex in enumerate((0.35, 0.75, 1.15)):      # archivolts (pointed rings) around the portal, stepping out
    relief_arch(cfr, (-fx, yF), (fx, yF), fx, pw + 2*ex, ZC, ZC + C["portal_h"] + 1.6 + ex*1.2, 0.0, -wt/2 - 0.05 - 0.12*i, k=0.85, ring=cfr)
relief_arch(glass, (-fx, yF), (fx, yF), fx, pw - 0.1, ZC + C["portal_h"] - 1.0, ZC + C["portal_h"] + 1.55, 0.06, -wt/2 - 0.03, k=0.85)   # tympanum
# wimperg (portal gable) frame
wg_b = ZC + C["portal_h"] + 0.8; wg_t = C["portal_gable_top"]
for sx in (-1, 1):
    beam(cfr, (sx*(pw/2 + 1.5), yF - wt/2 - 0.35, wg_b), (0, yF - wt/2 - 0.35, wg_t), 0.5, 0.45, up=(0, -1, 0))
pinnacle(cfr, 0, yF - wt/2 - 0.35, wg_t - 0.3, 0.35, 0.6, 1.4, fin)
for sx in (-1, 1): pinnacle(cfr, sx*(pw/2 + 1.6), yF - wt/2 - 0.4, ZC, 0.55, wg_b - ZC + 0.4, 2.0, fin)
# blind lancets either side of the portal, string course, rose window
for sx in (-1, 1):
    relief_arch(glass, (-fx, yF), (fx, yF), fx + sx*4.0, 1.3, ZC + 2.5, ZC + 9.5, 0.06, -wt/2 - 0.03, ring=cfr)
    relief_arch(glass, (-fx, yF), (fx, yF), fx + sx*4.0, 1.3, C["rose_z"] - 6.4, C["rose_z"] - 2.2, 0.06, -wt/2 - 0.03, ring=cfr)
beam(cfr, (-fx, yF - wt/2 - 0.12, C["rose_z"] - C["rose_r"] - 0.6), (fx, yF - wt/2 - 0.12, C["rose_z"] - C["rose_r"] - 0.6), 0.3, 0.3)
rz, rr = C["rose_z"], C["rose_r"]
for side, yy in ((-1, yF - wt/2 - 0.03), (1, yF + wt/2 + 0.03)):
    RO = RU["rose"] if RU else None
    lostw = set(RRo.sample(range(12), RO["glass_wedges_lost"])) if RO else set()
    for k in range(12):   # glass in 12 wedges; ruin: some lost -> the rose reads partly empty/dark
        if k in lostw: continue
        a0, a1 = 2*math.pi*k/12, 2*math.pi*(k + 1)/12
        extrude(glass, [(0, rz)] + [(rr*math.cos(a0 + (a1 - a0)*j/2), rz + rr*math.sin(a0 + (a1 - a0)*j/2)) for j in range(3)], (0, yy, 0), (1, 0, 0), (0, 0, 1), 0.06)
    lost_sp = set(RRo.sample(range(12), RO["spokes_lost"])) if RO else set(); lost_ir = set(RRo.sample(range(12), RO["inner_ring_lost"])) if RO else set()
    for k in range(24):   # outer moulding ring
        a0, a1 = 2*math.pi*k/24, 2*math.pi*(k + 1)/24
        beam(cfr, (rr*math.cos(a0), yy + side*0.1, rz + rr*math.sin(a0)), (rr*math.cos(a1), yy + side*0.1, rz + rr*math.sin(a1)), 0.32, 0.3, up=(0, 1, 0))
    for k in range(12):   # spokes + inner ring
        a = 2*math.pi*k/12
        if k in lost_sp: beam(cfr, (0.45*math.cos(a), yy + side*0.08, rz + 0.45*math.sin(a)), (rr*0.38*math.cos(a), yy + side*0.08, rz + rr*0.38*math.sin(a)), 0.12, 0.2, up=(0, 1, 0))
        else: beam(cfr, (0.45*math.cos(a), yy + side*0.08, rz + 0.45*math.sin(a)), (rr*math.cos(a), yy + side*0.08, rz + rr*math.sin(a)), 0.12, 0.2, up=(0, 1, 0))
        a1 = 2*math.pi*(k + 1)/12
        if k not in lost_ir: beam(cfr, (rr*0.62*math.cos(a), yy + side*0.08, rz + rr*0.62*math.sin(a)), (rr*0.62*math.cos(a1), yy + side*0.08, rz + rr*0.62*math.sin(a1)), 0.1, 0.18, up=(0, 1, 0))
extrude(cfr, ngon(0, rz, 0.5, 12), (0, yF - wt/2 - 0.12, 0), (1, 0, 0), (0, 0, 1), 0.2)
pinnacle(cfr, 0, yF, C["facade_apex"] - 0.2, 0.6, 0.8, C["facade_finial"], fin)
# facade buttresses + pinnacles
for sx in (-1, 1):
    box(cs, sx*(fx - 0.55), sx*(fx + 0.65), yF - wt/2 - 1.5, yF + wt/2, ZC, NWT + 1.5)
    pinnacle(cfr, sx*(fx + 0.05), yF - wt/2 - 0.75, NWT + 1.5, 1.0, 2.2, C["facade_pinnacle_top"] - NWT - 1.5 - 2.2, fin)
door_rec("portal", "parvis", "nave", (0, yF, ZC), (0, 1), pw, C["portal_h"] - 1.0, "ext_door",
         leaves=[add_leaf("DoorLeaf_portal_L", "portal", (-pw/2, yF, ZC), (1, 0, 0), (0, 1, 0), pw/2, C["portal_h"] - 1.02, ZC),
                 add_leaf("DoorLeaf_portal_R", "portal", (pw/2, yF, ZC), (-1, 0, 0), (0, 1, 0), pw/2, C["portal_h"] - 1.02, ZC)])

pin("nave_walls")
# --- nave arcade walls (lower part with arcade openings, upper part with clerestory windows) incl. choir
ARC_H = C["arcade_open_h"]; LOW_TOP = ZC + ARC_H + 1.6
for sg, aisle in ((-1, "aisle_W"), (1, "aisle_E")):
    x = sg*nhw; tower = "tower_SW" if sg < 0 else "tower_SE"
    ops = []; opsU = []
    # bay 0 = tower bay: solid wall with a door
    ops.append({"s": bay/2, "w": 1.2, "h": 2.6, "kind": "pointed", "k": 0.7})
    door_rec(f"nave_{tower}", "nave", tower, (x, yF + bay/2, ZC), (sg, 0), 1.2, 2.6 - arch_rise(1.2, "pointed", 0.7), "door")
    for i in range(1, NB):
        s = bay*(i + 0.5); ops.append({"s": s, "w": bay - C["pier_w"], "h": ARC_H, "kind": "pointed", "k": 0.75})
        door_rec(f"arcade_{aisle}_{i}", "nave", aisle, (x, yF + s, ZC), (sg, 0), bay - C["pier_w"] - 0.4, ARC_H - arch_rise(bay - C["pier_w"], "pointed", 0.75), "opening")
    for i in range(0, NB):
        opsU.append(lancet(bay*(i + 0.5), 2.6, C["aisle_roof_top"] + 0.5 - LOW_TOP, NWT - 0.5 - LOW_TOP, mull=1))
    Lch = cy - yB; s = (yB - yF) + Lch/2
    wch = Lch - 1.4 if Lch >= 4.0 else Lch - 0.8   # short straight choir bay (apse pulled south, gap #6): thinner jambs keep the opening walkable
    ops.append({"s": s, "w": wch, "h": ARC_H, "kind": "pointed", "k": 0.75})
    door_rec(f"choir_ambulatory_{'W' if sg < 0 else 'E'}", "nave", "ambulatory", (x, yF + s, ZC), (sg, 0), wch - 0.4, ARC_H - arch_rise(wch, "pointed", 0.75), "opening")
    opsU.append(lancet(s, min(2.4, Lch - 1.4), C["aisle_roof_top"] + 0.5 - LOW_TOP, NWT - 0.5 - LOW_TOP, mull=1 if Lch - 1.4 >= 2.0 else 0))
    wall(cs, (x, yF), (x, cy), ZC, LOW_TOP, wt, ops, wx=WXC(top=False, ground=True))
    wall(cs, (x, yF), (x, cy), LOW_TOP, NWT, wt, opsU, glass, cfr, wx=WXC(top=True))
    # engaged shafts (columns) on the nave side of every pier + capitals
    for yy in bayY[1:] + [cy]:
        cyl(cs, x - sg*(wt/2 + 0.25), yy, 0.36, ZC, NWT - 0.4, n=10)
        box(cfr, x - sg*(wt/2 + 0.55), x - sg*(wt/2), yy - 0.5, yy + 0.5, ZC + ARC_H - 2.6, ZC + ARC_H - 2.2)
    beam(cfr, (x - sg*(wt/2 + 0.1), yF, LOW_TOP - 0.2), (x - sg*(wt/2 + 0.1), cy, LOW_TOP - 0.2), 0.25, 0.3)   # triforium string course
    # --- aisle outer wall with lancets (bay 0 is the tower base)
    xo = sg*ahw
    opsA = [lancet(bay*0.5, 1.2, 3.0, 6.4)] + [lancet(bay*(i + 0.5), 2.4, 2.6, 8.4, mull=1) for i in range(1, NB)]
    wall(cs, (xo, yF), (xo, yB), ZC, AWT, wt, opsA, glass, cfr, wx=WXC(ground=True))
    beam(cfr, (xo + sg*(wt/2 + 0.1), yF, ZC + 2.4), (xo + sg*(wt/2 + 0.1), yB, ZC + 2.4), 0.25, 0.25)
    nk = int((yB - yF)/2.0)
    for k in range(nk):   # eaves cornice in 2 m stones; ruin: some fallen (lying at the wall foot, decor)
        ya, yb_ = yF + (yB - yF)*k/nk, yF + (yB - yF)*(k + 1)/nk
        if RU and RR.random() < RU["cornice_gap_p"]:
            xx = xo + sg*(wt/2 + RR.uniform(0.5, 1.0)); beam(DEB_st, (xx, ya + 0.3, ZC + 0.16), (xx + sg*RR.uniform(-0.3, 0.3), yb_ - 0.3, ZC + 0.18), 0.35, 0.3)
        else: beam(cfr, (xo + sg*(wt/2 + 0.12), ya, AWT - 0.1), (xo + sg*(wt/2 + 0.12), yb_, AWT - 0.1), 0.35, 0.3)
    # aisle north end wall (gap toward the ambulatory between nave wall and ambulatory wall)
    xa = sg*(A["r_amb"] - wt/2)
    wall(cs, (xa, yB), (sg*(ahw + wt/2), yB), ZC, AWT, wt, [lancet(abs(ahw + wt/2 - abs(xa))/2, 1.6, 3.0, 8.0)], glass, cfr, wx=WXC(ground=True))
    gw = (A["r_amb"] - wt/2) - (nhw + wt/2)
    door_rec(f"{aisle}_ambulatory", aisle, "ambulatory", (sg*(nhw + wt/2 + gw/2), yB, ZC), (0, 1), gw - 0.3, 4.0, "opening", check_wall=False)
    # tower: front wall, north wall (door to the aisle), lower-tower roof slab
    AL = C["aisle_front_lancet"]
    wall(cs, (sg*(nhw + wt/2), yF), (sg*(ahw + wt/2), yF), ZC, AWT, wt, [lancet((ahw - nhw)/2, AL["w"], AL["sill"], AL["apex"], mull=1)], glass, cfr, wx=WXC(ground=True))
    tdx = (nhw + ahw)/2
    wall(cs, (sg*(nhw + wt/2), bayY[1]), (sg*(ahw - wt/2), bayY[1]), ZC, AWT, wt, [{"s": (ahw - nhw - wt)/2, "w": 1.2, "h": 2.6, "kind": "flat"}])
    door_rec(f"{tower}_{aisle}", tower, aisle, (sg*tdx, bayY[1], ZC), (0, 1), 1.2, 2.6, "door")
    box(SC.B("CathInterior", "timber"), sg*(nhw + wt/2), sg*(ahw - wt/2), yF + wt/2, bayY[1] - wt/2, ZC + 8.0, ZC + 8.3)
    box(cs, sg*(nhw - wt/2), sg*(ahw + wt/2), yF - wt/2, bayY[1] + wt/2, AWT - 0.4, AWT)
    # aisle buttresses (piers) + pinnacles, flying buttresses to the clerestory
    for i in range(0, NB + 1):
        yy = bayY[i]; bx0, bx1 = sg*(ahw + wt/2), sg*(ahw + wt/2 + C["buttress_out"])
        box(cs, bx0, bx1, yy - C["buttress_w"]/2, yy + C["buttress_w"]/2, ZC, C["buttress_top"])
        pinnacle(cfr, (bx0 + bx1)/2, yy, C["buttress_top"], 0.85, 1.8, C["pinnacle_h"] - 1.8, fin)
        if i >= 1:
            so, si = sg*(ahw + wt/2 + 0.2), sg*(nhw + wt/2)
            Lf = abs(so - si); zo, zi = C["flyer_z_out"], C["flyer_z_in"]
            prof = [(0, zo + 0.6), (Lf, zi + 0.6), (Lf, zi - 0.7)] + [(Lf*(1 - k/10), zo - 1.6 + (zi - 0.7 - (zo - 1.6))*math.sin(math.pi/2*(1 - k/10))) for k in range(1, 11)]
            extrude(cs, prof, (so, yy, 0), (-sg, 0, 0), (0, 0, 1), 0.65)
    # clerestory buttress strips + tall pinnacles at every bay line (where the flyers land), rising above the nave eave
    CP = C["clerestory_pinnacles"]
    for yy in bayY[1:]:
        xw = sg*(nhw + wt/2); xc = xw + sg*(CP["strip_d"]/2 + 0.1)
        box(cs, min(xw, xw + sg*CP["strip_d"]), max(xw, xw + sg*CP["strip_d"]), yy - CP["strip_w"]/2, yy + CP["strip_w"]/2, C["aisle_roof_top"] - 0.8, NWT + 0.2)
        pinnacle(cfr, xc, yy, NWT + 0.2, CP["w"], CP["shaft"], CP["top"] - NWT - 0.2 - CP["shaft"], fin)
pin("ambulatory")
# --- ambulatory walls (straight sides + half polygon), apse inner wall (arcade + clerestory)
ra, ri, nseg = A["r_amb"], A["r_in"], A["sides"]//2
for sg in (-1, 1):
    wall(cs, (sg*ra, yB), (sg*ra, cy), ZC, A["amb_top"], wt, [lancet((cy - yB)/2, min(1.8, cy - yB - 1.2), 2.8, 8.0)], glass, cfr, wx=WXC(ground=True))
for k in range(nseg):
    a0, a1 = math.pi*k/nseg, math.pi*(k + 1)/nseg
    p0, p1 = (ra*math.cos(a0), cy + ra*math.sin(a0)), (ra*math.cos(a1), cy + ra*math.sin(a1)); Ls = 2*ra*math.sin(math.pi/nseg/2)
    wall(cs, p0, p1, ZC, A["amb_top"], wt, [lancet(Ls/2, 1.7, 2.8, 8.2)], glass, cfr, wx=WXC(ground=True))
    q0, q1 = (ri*math.cos(a0), cy + ri*math.sin(a0)), (ri*math.cos(a1), cy + ri*math.sin(a1)); Li = 2*ri*math.sin(math.pi/nseg/2)
    wall(cs, q0, q1, ZC, LOW_TOP, wt, [{"s": Li/2, "w": Li - 1.0, "h": ARC_H - 1.0, "kind": "pointed", "k": 0.9}], wx=WXC(top=False, ground=True))
    s0, s1 = C["aisle_roof_top"] + 0.5 - LOW_TOP, A["wall_top"] - 0.5 - LOW_TOP
    wall(cs, q0, q1, LOW_TOP, A["wall_top"], wt, [lancet(Li/2, 1.3, s0, s1, mull=0)] if s1 - s0 > 1.2 else [], glass, cfr, wx=WXC())
    am = (a0 + a1)/2; ow = Li - 1.4
    door_rec(f"apse_arcade_{k}", "nave", "ambulatory", (ri*math.cos(am)*math.cos(math.pi/nseg/2), cy + ri*math.sin(am)*math.cos(math.pi/nseg/2), ZC), (math.cos(am), math.sin(am)), ow, ARC_H - 1.0 - arch_rise(Li - 1.0, "pointed", 0.9), "opening")
for k in range(nseg + 1):   # piers (columns) at polygon vertices, outer buttress piers + flyers
    a = math.pi*k/nseg
    cyl(cs, ri*math.cos(a), cy + ri*math.sin(a), 0.72, ZC, A["wall_top"], n=10)
    cyl(cs, ra*math.cos(a), cy + ra*math.sin(a), 0.62, ZC, A["amb_top"], n=8)
    rp = A["r_pier"]; e = Vector((math.cos(a), math.sin(a), 0)); tng = Vector((-math.sin(a), math.cos(a), 0))
    obox(cs, (rp*e.x, cy + rp*e.y, (ZC + C["buttress_top"])/2), e, tng, (0, 0, 1), 0.75, 0.55, (C["buttress_top"] - ZC)/2)
    pinnacle(cfr, rp*e.x, cy + rp*e.y, C["buttress_top"], 0.8, 1.8, C["pinnacle_h"] - 1.8, fin)
    CP = C["clerestory_pinnacles"]; rc = ri + wt/2 + CP["strip_d"]/2 + 0.1   # apse clerestory pinnacles at every polygon vertex
    obox(cs, (rc*e.x, cy + rc*e.y, (C["aisle_roof_top"] - 0.8 + A["wall_top"] + 0.2)/2), e, tng, (0, 0, 1), CP["strip_d"]/2 + 0.1, CP["strip_w"]/2, (A["wall_top"] + 1.0 - C["aisle_roof_top"])/2)
    pinnacle(cfr, rc*e.x, cy + rc*e.y, A["wall_top"] + 0.2, CP["w"], CP["shaft"], CP["top"] - A["wall_top"] - 0.2 - CP["shaft"], fin)
    Lf = rp - 0.75 - (ri + wt/2); zo, zi = C["flyer_z_out"], C["flyer_z_in"]
    prof = [(0, zo + 0.6), (Lf, zi + 0.6), (Lf, zi - 0.7)] + [(Lf*(1 - j/10), zo - 1.6 + (zi - 0.7 - (zo - 1.6))*math.sin(math.pi/2*(1 - j/10))) for j in range(1, 11)]
    o = Vector((0, cy, 0)) + e*(rp - 0.75)
    extrude(cs, prof, o, -e, (0, 0, 1), 0.6)

# --- roofs (partly collapsed): helper for a rectangular slope with holes + rafters
ROOF_HOLES = {}   # keyed cathedral slopes: missing-tile cells (column, row) -> ruin_log.json (layout check across builds)
def roof_slope(sl, tim, E0, E1, R0, R1, rng, frac, cell=1.3, thick=0.18, exposed=None, purlins=True, sag=0.0, key=None, fixed_cell=False):
    """E0,E1 eave corners; R0,R1 ridge corners (R0 above E0). exposed(a_world_point)->True removes all tiles there.
    Ruin (own rng stream RRo; note the tile-hole stream itself shifts where new exposed areas skip draws): rafters under holes partly missing or snapped, purlins
    missing, loose/slipped slates in the holes; sag (m) bows the slope down mid-length (and the ridge by 40 % of it).
    key: element name -> pins (key, key/rafters, key/loose) so the slope's draws do not depend on earlier elements.
    fixed_cell: columns exactly `cell` wide from E0 (last one partial) so shortening the slope keeps the holes of the remaining columns."""
    if key: pin(key)
    E0, E1, R0, R1 = map(Vector, (E0, E1, R0, R1)); ea = E1 - E0; eb = R0 - E0; La, Lb = ea.length, eb.length
    ua, ub = ea/La, eb/Lb; n = ua.cross(ub).normalized()
    if n.z < 0: n = -n
    sl.uvframe = (E0, ua, ub)   # slate courses parallel to the eave (texture v runs up the slope)
    na, nbb = max(1, int(La/cell)), max(1, int(Lb/cell))
    if fixed_cell: na = max(1, math.ceil(La/cell - 1e-6))
    da, db = (cell if fixed_cell else La/na), Lb/nbb; holes_cols = set(); loose = []
    aw = lambda i: min(da, La - da*i)   # column width (only the last fixed-cell column is narrower)
    RB = RU["roof"] if RU else None
    def sv(a, b):   # sag offset at slope coords (a along eave, b up the slope)
        if not sag: return Vector((0, 0, 0))
        return -n*(sag*math.sin(math.pi*min(max(a/La, 0), 1))*(0.4 + 0.6*math.sin(math.pi*min(max(b/Lb, 0), 1))))
    for i in range(na):
        run = None
        for j in range(nbb + 1):
            c = E0 + ua*(da*i + aw(i)/2) + ub*(db*(j + 0.5))
            hole = j < nbb and ((exposed is not None and exposed(c)) or (rng.random() < frac and 0 < j < nbb - 1))
            if j < nbb and not hole:
                run = j if run is None else run
            else:
                if hole:
                    holes_cols.add(i)
                    if key: ROOF_HOLES.setdefault(key, []).append((i, j))
                    if RB and RRo.random() < RB["loose_slate_p"]: loose.append((i, j))
                if run is not None:
                    a0, a1, b0, b1 = da*i, da*i + aw(i), db*run, db*j
                    cc = E0 + ua*((a0 + a1)/2) + ub*((b0 + b1)/2) - n*(thick/2) + sv((a0 + a1)/2, (b0 + b1)/2)
                    obox(sl, cc, ua, ub, n, (a1 - a0)/2 + 0.005, (b1 - b0)/2, thick/2)
                    run = None
    # rafters under every column that has a hole (and purlins there)
    if key: pin(key + "/rafters")
    for i in sorted(holes_cols):
        for f in (0.0, 0.5):
            a = da*i + aw(i)*f + 0.1
            pe, pr = E0 + ua*a - n*(thick + 0.1) + sv(a, 0), R0 + ua*a - n*(thick + 0.1) + sv(a, Lb)
            if RB:
                r = RRo.random()
                if r < RB["rafter_missing"]: continue
                if r < RB["rafter_missing"] + RB["rafter_broken"]:   # snapped: keep the eave or the ridge end
                    k = RRo.uniform(0.3, 0.8)
                    if RRo.random() < 0.5: pr = pe + (pr - pe)*k
                    else: pe = pr + (pe - pr)*k
            beam(tim, pe, pr, 0.14, 0.2, up=n)
        if purlins:
            for fb in (0.2, 0.45, 0.7, 0.92):
                if RB and RRo.random() < RB["purlin_missing"]: continue
                beam(tim, E0 + ua*(da*i) + ub*(Lb*fb) - n*(thick + 0.32) + sv(da*i, Lb*fb), E0 + ua*(da*i + aw(i)) + ub*(Lb*fb) - n*(thick + 0.32) + sv(da*i + aw(i), Lb*fb), 0.16, 0.22, up=n)
    if key: pin(key + "/loose")
    for (i, j) in loose:   # slipped slates hanging in the hole / lying on the rafters
        c = E0 + ua*(da*i + aw(i)*RRo.uniform(0.2, 0.8)) + ub*(db*(j + RRo.uniform(0.1, 0.9))) - n*(thick + 0.02) + sv(da*(i + 0.5), db*(j + 0.5))
        t = RRo.uniform(-0.6, 0.6); u2 = (ua*math.cos(t) + ub*math.sin(t)).normalized(); v2 = n.cross(u2).normalized()
        obox(sl, c, u2, v2, (n + u2*RRo.uniform(-0.3, 0.3)).normalized(), RRo.uniform(0.12, 0.2), RRo.uniform(0.18, 0.3), 0.012)
    sl.uvframe = None
    if sag:
        k = 6
        for q in range(k): beam(tim, R0 - n*0.2 + ua*(La*q/k) + sv(La*q/k, Lb), R0 - n*0.2 + ua*(La*(q + 1)/k) + sv(La*(q + 1)/k, Lb), 0.28, 0.3, up=n)
    else: beam(tim, R0 - n*0.2, R1 - n*0.2, 0.28, 0.3, up=n)   # ridge beam
def ragged(lo, hi, key, coord):
    """exposed() predicate for a band lo..hi with a ragged, row-dependent edge (ruin.roof.ragged_cells x 1.3 m)"""
    rc = (RU["roof"]["ragged_cells"] if RU else 0)*1.3
    def f(c):
        g = random.Random(int(round(c.z*3.0))*7919 + key); x = coord(c)
        return lo + g.uniform(-rc, rc) <= x <= hi + g.uniform(-rc, rc)
    return f
rng = random.Random(C["roof_holes"]["seed"]); RH = C["roof_holes"]; STREAMS["roof"] = rng
ov = 0.5; ze = NWT - 0.15; zr = C["nave_ridge"]; ex0, ex1 = RH["nave_east_exposed"]
for sg in (-1, 1):
    Ex = sg*(nhw + wt/2 + ov); zeo = ze - ov*(zr - ze)/(nhw + wt/2)
    exposed = ragged(ex0, ex1, 11, lambda c: c.y) if sg > 0 else (ragged(*RU["roof"]["nave_west_exposed"], 12, lambda c: c.y) if RU else None)
    E0, E1, R0, R1 = (Ex, yF - 0.6, zeo), (Ex, cy, zeo), (0, yF - 0.6, zr), (0, cy, zr)
    SD = "W" if sg < 0 else "E"
    roof_slope(slate, ctim, E0, E1, R0, R1, rng, RH["hole_frac"], exposed=exposed, key="roof_nave_" + SD, fixed_cell=True)
    # aisle lean-to roofs (from tower bay to the aisle end), ambulatory straight parts
    zA0, zA1 = AWT - 0.1, C["aisle_roof_top"]
    roof_slope(slate, ctim, (sg*(ahw + wt/2 + 0.4), bayY[1] + wt/2, zA0 - 0.25), (sg*(ahw + wt/2 + 0.4), yB + wt/2, zA0 - 0.25),
               (sg*(nhw + wt/2), bayY[1] + wt/2, zA1), (sg*(nhw + wt/2), yB + wt/2, zA1), rng, RH["hole_frac"]*1.3, exposed=(lambda c: RRo.random() < RU["roof"]["aisle_hole_frac"] - RH["hole_frac"]*1.3) if RU else None, key="roof_aisle_" + SD)
    roof_slope(slate, ctim, (sg*(ra + wt/2 + 0.4), yB + wt/2, zA0 - 0.25), (sg*(ra + wt/2 + 0.4), cy, zA0 - 0.25),
               (sg*(nhw + wt/2), yB + wt/2, zA1), (sg*(nhw + wt/2), cy, zA1), rng, 0.0, key="roof_amb_" + SD)
# apse half-cone roof + ambulatory ring roof facets
def thick_tri(bk, a, b, c, t=0.2):
    a, b, c = Vector(a), Vector(b), Vector(c); n = (b - a).cross(c - a).normalized()
    if n.z < 0: b, c = c, b; n = -n
    bk.face([a, b, c]); bk.face([a - n*t, c - n*t, b - n*t])
    for p, q in ((a, b), (b, c), (c, a)): bk.face([p - n*t, q - n*t, q, p])
rr_ = ri + wt/2 + ov; apex = (0, cy, zr)
for k in range(nseg):
    a0, a1 = math.pi*k/nseg, math.pi*(k + 1)/nseg
    thick_tri(slate, (rr_*math.cos(a0), cy + rr_*math.sin(a0), zeo), (rr_*math.cos(a1), cy + rr_*math.sin(a1), zeo), apex)
    ro, ri2 = ra + wt/2 + 0.4, ri + wt/2
    q = [(ro*math.cos(a0), cy + ro*math.sin(a0), AWT - 0.35), (ro*math.cos(a1), cy + ro*math.sin(a1), AWT - 0.35),
         (ri2*math.cos(a1), cy + ri2*math.sin(a1), C["aisle_roof_top"]), (ri2*math.cos(a0), cy + ri2*math.sin(a0), C["aisle_roof_top"])]
    thick_tri(slate, q[0], q[1], q[2]); thick_tri(slate, q[0], q[2], q[3])
pin("apse_roof_finials")
pinnacle(cfr, 0, cy, zr - 0.3, 0.5, 0.5, A["finial"], fin)
pinnacle(cfr, 0, cy + rr_ - 0.3, zeo - 0.5, 0.7, 1.4, 3.0, fin)
pin("towers")
# --- towers (upper parts) + spire
def tower_walls(x0, x1, y0, y1, z0, z1, tw, tiers):
    """square stage of walls; `tiers` stacked rows of paired tall lancets (0 = blind), one wall band per tier + string course"""
    ps = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]; n = max(1, tiers); th = (z1 - z0)/n
    for t in range(n):
        za, zb_ = z0 + t*th, z0 + (t + 1)*th
        for (pa, pb) in zip(ps, ps[1:] + ps[:1]):
            L = math.dist(pa, pb)
            ops = [lancet(L/2 - 0.75, 0.85, 0.8, th - 0.6, mull=0), lancet(L/2 + 0.75, 0.85, 0.8, th - 0.6, mull=0)] if tiers else []
            wall(cs, pa, pb, za, zb_, tw, ops, glass, cfr, wx=WXC(top=(t == n - 1)))
        if t:   # string course between tiers
            for (pa, pb) in zip(ps, ps[1:] + ps[:1]): beam(cfr, (pa[0], pa[1], za), (pb[0], pb[1], za), tw + 0.25, 0.2)
    return ps
def upper_tower(tw_, x0, x1, y0, y1):
    """lower stage (full footprint, angle buttresses + pinnacles) -> set-back belfry stage (tall paired lancets,
    corner buttresses + tall pinnacles) -> spire. All heights from params."""
    zb, ztop, bw = tw_["belfry_z0"], tw_["top"], tw_["belfry_w"]
    ps = tower_walls(x0, x1, y0, y1, AWT, zb, 0.8, tw_.get("stage_tiers", 0))
    box(cs, x0 - 0.6, x1 + 0.6, y0 - 0.6, y1 + 0.6, AWT - 0.3, AWT + 0.1)
    box(cs, x0 - 0.3, x1 + 0.3, y0 - 0.3, y1 + 0.3, zb - 0.35, zb)   # stage roof / gallery floor
    for (x, y) in ps:   # angle buttresses + stage pinnacles
        box(cs, x - 0.45, x + 0.45, y - 0.45, y + 0.45, AWT, zb - 0.3)
        pinnacle(cfr, x, y, zb - 0.3, 0.75, 1.3, tw_["stage_pinnacle_top"] - zb + 0.3 - 1.3, fin)
    cxs, cys = (x0 + x1)/2, (y0 + y1)/2; h = bw/2
    bx0, bx1, by0, by1 = cxs - h, cxs + h, cys - h, cys + h
    bps = tower_walls(bx0, bx1, by0, by1, zb, ztop, 0.6, tw_["belfry_tiers"])
    for (xa, ya, xb, yb) in ((bx0, by0, bx1, by0), (bx0, by1, bx1, by1)): beam(cfr, (xa, ya, ztop), (xb, yb, ztop), 0.3, 0.35)
    for (xa, ya, xb, yb) in ((bx0, by0, bx0, by1), (bx1, by0, bx1, by1)): beam(cfr, (xa, ya, ztop), (xb, yb, ztop), 0.3, 0.35)
    for (x, y) in bps:   # belfry corner buttresses + tall pinnacles around the spire base
        box(cs, x - 0.42, x + 0.42, y - 0.42, y + 0.42, zb, ztop + 0.2)
        pinnacle(cfr, x, y, ztop + 0.2, 0.66, 1.0, tw_["corner_pinnacle_top"] - ztop - 0.2 - 1.0, fin)
    return cxs, cys
for key, sg in (("tower_sw", -1), ("tower_se", 1)):
    tw_ = C[key]
    xs = sorted([tw_["x"][0], tw_["x"][1]]); x0, x1 = xs[0] + 0.5*(1 if sg < 0 else 0.4), xs[1] - 0.5*(0.4 if sg < 0 else 1)
    y0, y1 = tw_["y"][0] + 0.3, tw_["y"][1] - 0.5
    cxs, cys = upper_tower(tw_, x0, x1, y0, y1)
    rs = tw_["spire_r"]
    cone(slate, cxs, cys, rs, tw_["top"], tw_["spire_tip"], n=8, rot=math.pi/8)
    if key == "tower_sw":
        for k in range(4):   # spire lucarnes (scaled to the spire radius)
            a = math.pi/2*k; lx, ly = cxs + 0.62*rs*math.cos(a), cys + 0.62*rs*math.sin(a); lw = 0.2*rs
            box(cs, lx - lw, lx + lw, ly - lw, ly + lw, tw_["top"], tw_["top"] + 2.0)
            cone(slate, lx, ly, lw*1.5, tw_["top"] + 2.0, tw_["top"] + 3.3, n=4, rot=math.pi/4)
        cx_, z_ = tw_["spire_tip"] - 0.15, tw_["cross"]
        box(fin, cxs - 0.07, cxs + 0.07, cys - 0.07, cys + 0.07, cx_, cx_ + z_)
        box(fin, cxs - 0.32, cxs + 0.32, cys - 0.06, cys + 0.06, cx_ + z_*0.62, cx_ + z_*0.75)
    else:
        cyl(fin, cxs, cys, 0.08, tw_["spire_tip"] - 0.2, tw_["spire_tip"] + 0.8, n=6)

pin("interior")
# --- interior fittings: pews, altar, fallen beams, floor slabs in the towers
cint = SC.B("CathInterior", "timber"); calt = SC.B("CathInterior", "stone")
# ruin: nave rubble heaps (under the collapsed east slope + the west-slope hole) are planned here so the pews they buried are
# left out; some other pews are missing or knocked askew (seeded)
NAVE_PILES = []
if RU:
    _r = random.Random(RU["seed"] + 2)
    for k in range(RU["rubble"]["nave_piles"]):
        west = k == RU["rubble"]["nave_piles"] - 1
        NAVE_PILES.append((-_r.uniform(2.4, 2.55) if west else _r.uniform(2.4, 2.55), _r.uniform(30.5, 33.5) if west else 14.5 + k*5.2 + _r.uniform(-0.8, 0.8)))
for yy in [11.5 + 1.3*k for k in range(14)]:
    for sx in (-1, 1):
        xa, xb = sx*1.4, sx*(nhw - wt/2 - 1.4)
        if any(abs(px - (xa + xb)/2) < 2.0 and abs(py - (yy + 0.25)) < 1.5 for px, py in NAVE_PILES): continue
        if RU and RR.random() < RU["rubble"]["pews_missing"]: continue
        if RU and RR.random() < RU["rubble"]["pews_askew"]:   # shoved askew: rotated about its inner end
            a = RR.uniform(-0.35, 0.35); L_ = abs(xb - xa); cx_, cy2 = (xa + xb)/2, yy + 0.25
            ex_ = Vector((math.cos(a)*sx, math.sin(a), 0)); ey_ = Vector((-math.sin(a)*sx, math.cos(a), 0))
            obox(cint, (cx_, cy2 - 0.04, ZC + 0.225), ex_, ey_, (0, 0, 1), L_/2, 0.21, 0.225); obox(cint, (cx_ + ey_.x*0.21, cy2 + ey_.y*0.21, ZC + 0.475), ex_, ey_, (0, 0, 1), L_/2, 0.04, 0.475)
            continue
        box(cint, xa, xb, yy, yy + 0.42, ZC, ZC + 0.45); box(cint, xa, xb, yy + 0.42, yy + 0.5, ZC, ZC + 0.95)
box(calt, -1.4, 1.4, cy + 0.6, cy + 2.6, ZC, ZC + 0.16); box(calt, -1.1, 1.1, cy + 1.0, cy + 2.1, ZC + 0.16, ZC + 1.15)
for (a, b) in (((2.2, 15.0, ZC + 0.5), (4.0, 22.0, ZC + 1.3)), ((3.6, 18.5, ZC + 0.5), (2.0, 25.0, ZC + 0.9))):
    beam(cint, a, b, 0.3, 0.35)

pin("gates")
# --- iron gates + fences in front of the cathedral steps (yards beside the steps)
G = C["gate"]; gy = G["y"]
for sg, yard in ((-1, "yard_W"), (1, "yard_E")):
    xa, xb = sg*(G["x_posts"][0] + 0.25), sg*G["x_posts"][1]
    post(xa, gy, PZ, w=G["post_w"], h=G["post_h"]); post(xb, gy, PZ, w=G["post_w"], h=G["post_h"])
    gc = (xa + xb)/2; gwid = G["gate_w"]
    lo_x, hi_x = sorted((xa + sg*G["post_w"]/2, xb - sg*G["post_w"]/2))
    g0, g1 = gc - gwid/2, gc + gwid/2
    for (u0, u1) in ((lo_x, g0), (g1, hi_x)):   # stone kerb wall + bars
        box(bst, u0, u1, gy - 0.2, gy + 0.2, PZ, PZ + 0.5)
        nbar = int((u1 - u0)/0.15)
        for i in range(nbar + 1):
            xx = u0 + (u1 - u0)*i/nbar; box(iron, xx - 0.02, xx + 0.02, gy - 0.02, gy + 0.02, PZ + 0.5, PZ + G["h"])
            cone(iron, xx, gy, 0.05, PZ + G["h"], PZ + G["h"] + 0.15, n=4)
        for zz in (PZ + 0.9, PZ + G["h"] - 0.15): box(iron, u0, u1, gy - 0.03, gy + 0.03, zz - 0.03, zz + 0.03)
    # side fence from the outer post back to the podium front
    box(bst, xb - 0.2, xb + 0.2, gy + G["post_w"]/2, y_pod, PZ, PZ + 0.5)
    nbar = int((y_pod - gy - G["post_w"]/2)/0.15)
    for i in range(nbar + 1):
        yy = gy + G["post_w"]/2 + (y_pod - gy - G["post_w"]/2)*i/nbar; box(iron, xb - 0.02, xb + 0.02, yy - 0.02, yy + 0.02, PZ + 0.5, PZ + G["h"])
    space(yard, ((xa + xb)/2, (gy + y_pod)/2, PZ), "outdoor")
    lw = gwid/2
    door_rec(f"gate_{yard}", "plaza", yard, (gc, gy, PZ), (0, 1), gwid, G["h"] - 0.2, "gate", wall_probe_h=0.3,
             leaves=[add_leaf(f"DoorLeaf_gate_{yard}_a", f"gate_{yard}", (g0, gy, PZ), (1, 0, 0), (0, 1, 0), lw, G["h"] - 0.1, PZ + 0.02, mat="iron", bars=True),
                     add_leaf(f"DoorLeaf_gate_{yard}_b", f"gate_{yard}", (g1, gy, PZ), (-1, 0, 0), (0, 1, 0), lw, G["h"] - 0.1, PZ + 0.02, mat="iron", bars=True)])

# =====================================================================================
# 3. townhouses
# =====================================================================================
HS = P["houses"]; SH = HS["storey_h"]; HT = HS["wall_t"]; PT = HS["part_t"]; SL = HS["slab_t"]
class Frame:
    """local house coords: u = depth from the street face (inward), v = along the street, z absolute"""
    def __init__(s, kind, a, b):
        s.kind, s.a, s.b = kind, a, b
    def M(s, u, v, z=0.0):
        if s.kind == "W": return Vector((-s.a - u, s.b - v, z))
        if s.kind == "E": return Vector((s.a + u, s.b - v, z))
        if s.kind == "N": return Vector((s.b + v, s.a + u, z))   # street face is the south face at y=a
    def box(s, bk, u0, u1, v0, v1, z0, z1, top=None):
        p, q = s.M(u0, v0, z0), s.M(u1, v1, z1); box(bk, p.x, q.x, p.y, q.y, z0, z1, top=top)
    def p2(s, u, v): m = s.M(u, v); return (m.x, m.y)
    def v_of(s, p): return (s.b - p.y) if s.kind in ("W", "E") else (p.x - s.b)
    def axis_v(s):   # world axis and sign of +v
        return {"W": ("y", -1), "E": ("y", -1), "N": ("x", +1)}[s.kind]
    def dir(s, du, dv):
        a, b = s.M(du, dv), s.M(0, 0); d = a - b; return Vector((d.x, d.y, 0)).normalized()

def windows_row(L, n, skip=None, w=0.95, sill=0.9, top=2.25, pad=1.2, kind="flat", skip_d=1.4):
    if n <= 0: return []
    xs = [pad + (L - 2*pad)*(i + 0.5)/n for i in range(n)]
    if skip is not None: xs = [x for x in xs if abs(x - skip) > skip_d]
    return [{"s": x, "w": w, "sill": sill, "h": top + (0.3 if kind == "round" else 0), "kind": kind, "glass": True, "mull": 1} for x in xs]

class Mirror:
    """the same house frame seen from the rear (u -> D - u); used to build rear dormers with the street-dormer code"""
    def __init__(s, fr, D): s.fr, s.D = fr, D
    def M(s, u, v, z=0.0): return s.fr.M(s.D - u, v, z)
    def box(s, bk, u0, u1, v0, v1, z0, z1, top=None): s.fr.box(bk, s.D - u1, s.D - u0, v0, v1, z0, z1, top=top)
    def p2(s, u, v): return s.fr.p2(s.D - u, v)
    def dir(s, du, dv): return s.fr.dir(-du, dv)

def patch_face(bk, p0, p1, z0, z1, nrm, n, rng, avoid=()):
    """brick patches where the plaster has fallen off (seeded layout), kept clear of the openings in `avoid`"""
    if n <= 0 or z1 - z0 < 1.2: return
    p0, p1 = Vector((p0[0], p0[1], 0)), Vector((p1[0], p1[1], 0)); d = p1 - p0; L = d.length; S = d/L
    N = Vector((nrm[0], nrm[1], 0)).normalized(); placed = 0
    for _ in range(n*6):
        if placed >= n: break
        w, h = rng.uniform(0.6, 2.0), rng.uniform(0.5, min(1.5, z1 - z0 - 0.3))
        if L < w + 0.5: continue
        s, zc = rng.uniform(w/2 + 0.2, L - w/2 - 0.2), rng.uniform(z0 + h/2 + 0.1, z1 - h/2 - 0.1)
        we, he = w*1.3, h*1.3   # ragged pieces reach ~0.64 x the core size
        if any(abs(s - a["s"]) < (we + a["w"])/2 + 0.15 and zc + he/2 > z0 + a.get("sill", 0) - 0.15 and zc - he/2 < z0 + a["h"] + 0.15 for a in avoid): continue
        if s - we/2 < 0.1 or s + we/2 > L - 0.1 or zc - he/2 < z0 + 0.05 or zc + he/2 > z1 - 0.05: continue
        c = p0 + S*s + N*0.03; obox(bk, (c.x, c.y, zc), S, N, (0, 0, 1), w/2*0.7, 0.02, h/2*0.75)
        for _k in range(3):   # ragged outline: a few overlapping smaller pieces around the core
            ds, dz = rng.uniform(-w/2, w/2)*0.6, rng.uniform(-h/2, h/2)*0.6; c2 = c + S*ds - N*(0.006 + 0.004*_k)   # stepped back: no coplanar faces
            obox(bk, (c2.x, c2.y, zc + dz), S, N, (0, 0, 1), w*rng.uniform(0.18, 0.34), 0.02 - 0.002*_k, h*rng.uniform(0.18, 0.34))
        placed += 1

def timber_face(tim, fr, uu, W, z0, z1, pattern, rng, ops, out=-1):
    """half-timber frame on a street/rear face at depth uu: sole/sill/head rails, posts at the ends and at every window
    jamb, braces in the window-free panels: grid = none, braced = single diagonals (seeded), x = St Andrew's crosses"""
    nv = fr.dir(1, 0)*out
    for zz in (z0 + 0.08, z0 + 0.85, z1 - 0.14):
        beam(tim, fr.M(uu, 0.05, zz), fr.M(uu, W - 0.05, zz), 0.07, 0.16, up=(0, 0, 1))
    xs = {0.15, W - 0.15}
    for o in ops: xs |= {o["s"] - o["w"]/2 - 0.09, o["s"] + o["w"]/2 + 0.09}
    xs = sorted(xs); full = [xs[0]]
    for a, b in zip(xs, xs[1:]):   # extra posts so no panel is wider than ~1.7 m
        k = int((b - a)/1.7)
        full += [a + (b - a)*(j + 1)/(k + 1) for j in range(k)] + [b]
    for vv in full: beam(tim, fr.M(uu, vv, z0), fr.M(uu, vv, z1), 0.15, 0.07, up=fr.dir(1, 0))
    if pattern in (None, "grid"): return
    for i, (a, b) in enumerate(zip(full, full[1:])):
        if b - a < 0.6 or any(o["s"] - o["w"]/2 - 0.1 < (a + b)/2 < o["s"] + o["w"]/2 + 0.1 for o in ops): continue
        if pattern == "braced" and rng.random() < 0.6 and not (RU and RR.random() < RU["brace_missing"]):
            if i % 2: beam(tim, fr.M(uu, a, z0 + 0.12), fr.M(uu, b, z0 + 0.82), 0.12, 0.07, up=fr.dir(1, 0))
            else: beam(tim, fr.M(uu, a, z0 + 0.82), fr.M(uu, b, z0 + 0.12), 0.12, 0.07, up=fr.dir(1, 0))
        if pattern == "x" and i % 2 == 0 and not (RU and RR.random() < RU["brace_missing"]):
            beam(tim, fr.M(uu, a, z0 + 0.9), fr.M(uu, b, z1 - 0.2), 0.12, 0.07, up=fr.dir(1, 0))
            beam(tim, fr.M(uu, a, z1 - 0.2), fr.M(uu, b, z0 + 0.9), 0.12, 0.07, up=fr.dir(1, 0))

MATS = {"plaster": "plaster", "brick": "brick", "stone": "stone"}
def dormer(G, fr, ud, vd, ze, tp, hsl, hgl, tim, rng, timber, PL="plaster"):
    zs = ze + ud*tp; hd = 1.6; ub = ud + hd/tp + 0.2; wd = 0.85
    fr.box(SC.B(G, PL), ud, ub, vd - wd, vd + wd, zs - 0.4, zs + hd)
    a = fr.M(ud - 0.02, vd - 0.5, 0); b = fr.M(ud - 0.02, vd + 0.5, 0)
    extrude(hgl, [(0, zs + 0.15), (1.0, zs + 0.15), (1.0, zs + 1.25), (0, zs + 1.25)], Vector((a.x, a.y, 0)), Vector((b.x - a.x, b.y - a.y, 0)).normalized(), (0, 0, 1), 0.06)
    for sgn in (-1, 1):
        E0, E1 = fr.M(ud - 0.25, vd + sgn*(wd + 0.25), zs + hd - 0.1), fr.M(ub, vd + sgn*(wd + 0.25), zs + hd - 0.1)
        R0, R1 = fr.M(ud - 0.25, vd, zs + hd + 0.75), fr.M(ub, vd, zs + hd + 0.75)
        if sgn > 0: E0, E1, R0, R1 = E1, E0, R1, R0
        roof_slope(hsl, tim, E0, E1, R0, R1, rng, 0.0, cell=2.0, thick=0.12, purlins=False)
    gable(SC.B(G, PL), fr.p2(ud, vd - wd), fr.p2(ud, vd + wd), zs + hd, zs + hd + 0.7, 0.12)
    if timber:
        for k in (-1, 1): beam(tim, fr.M(ud - 0.08, vd + k*(wd - 0.05), zs - 0.3), fr.M(ud - 0.08, vd + k*(wd - 0.05), zs + hd), 0.1, 0.06, up=fr.dir(1, 0))

def house(h, fr, D, street, ext_v0=False, ext_v1=False, seed=0):
    """one townhouse from its per-house spec h (params.json houses.list). Plan first (front/back room per storey),
    then shell: per-storey walls (jettied upper storeys), slabs with stair holes, partition + door, timber framing,
    dog-leg stairs, street door + leaf, roof (gables, street cross gables, dormers both sides, chimneys), patches."""
    hid = h["id"]; W = h["w"]; floors = h["floors"]; rng = random.Random(1000 + seed); pin("house_" + hid)
    G = f"House_{hid}"
    PL = {"A": "plaster", "B": "plaster_b", "C": "plaster_c"}[h.get("tone", "A")]   # per-house lime-plaster tone
    mat_of = lambda k: PL if MATS[k] == "plaster" else MATS[k]
    gfm, upm = SC.B(G, mat_of(h["gf"])), SC.B(G, mat_of(h["upper"])); plas = SC.B(G, PL); brk = SC.B(G, "brick")
    tim = SC.B(G, "timber"); hsl = SC.B(G, "slate"); hgl = SC.B("Glass", "glass"); chim = SC.B("Chimneys", "brick_red")
    jet = h["jetty"]; uface = [(-jet*f if f >= 1 else 0.0) for f in range(floors)]; uf = uface[-1]
    zf = [PZ + f*SH for f in range(floors)]
    ze = PZ + floors*SH + 0.3 + h["eave_dz"] + (HS["eave_extra"] if floors == HS["floors_row"] else HS["corner"]["eave_extra"])
    st = HS["stair"]; n = st["riser_n"]; rz = SH/n; tr = st["tread"]; v0 = st["v0"]
    pu = HS["partition_u"]; dv = min(max(h["door"]*W, 1.4), W - 1.4); pdv = HS["partition_door_v"]
    timber = h["timber"]
    # ---- plan: spaces first
    for f in range(floors):
        space(f"{hid}_F{f}_front", fr.M(1.5, W/2, zf[f]), "house", house=hid, floor=f)
        space(f"{hid}_F{f}_back", fr.M((pu + D)/2, W/2, zf[f]), "house", house=hid, floor=f)
    # ---- outer walls per storey
    for f in range(floors):
        z0 = zf[f]; z1 = (zf[f] + SH) if f < floors - 1 else ze; u0 = uface[f]
        mat = gfm if f == 0 else upm
        if f == 0:
            gk = "round" if h["gf_arch"] else "flat"
            wins = windows_row(W, h["win"][0], skip=dv, sill=1.0, w=h["win_w"], kind=gk, skip_d=1.5)
            if h["shop"] and wins:   # one wide shop window (3 lights) instead of the window furthest from the door
                k = max(range(len(wins)), key=lambda i: abs(wins[i]["s"] - dv)); wins[k].update({"w": 2.1, "mull": 2, "sill": 0.8})
                if any(abs(wins[k]["s"] - o["s"]) < 1.7 for o in wins if o is not wins[k]) or abs(wins[k]["s"] - dv) < 2.0 or wins[k]["s"] < 1.3 or wins[k]["s"] > W - 1.3:
                    wins[k].update({"w": h["win_w"], "mull": 1, "sill": 1.0})
            ops = [{"s": dv, "w": HS["door_w"], "h": HS["door_h"] + (0.35 if h["door_kind"] == "round" else 0), "kind": h["door_kind"]}] + wins
        else:
            ops = windows_row(W, h["win"][f], w=h["win_w"])
        isp = MATS[h["gf"] if f == 0 else h["upper"]] == "plaster"
        wxh = lambda out: ({"out": (out.x, out.y), "ground": f == 0, "top": f == floors - 1, "cracks": RU["weather"]["cracks_house"],
                            "lath": RU["weather"]["lath_house"] if isp else 0.0} if RU else None)
        wall(mat, fr.p2(u0 + HT/2, 0), fr.p2(u0 + HT/2, W), z0, z1, HT, ops, hgl, tim, wx=wxh(fr.dir(-1, 0)))   # street face
        rops = windows_row(W, h["rear_win"] - (1 if f == 0 else 0), w=h["win_w"])
        wall(mat, fr.p2(D - HT/2, W), fr.p2(D - HT/2, 0), z0, z1, HT, rops, hgl, tim, wx=wxh(fr.dir(1, 0)))      # rear face
        for vv, ext in ((0.15, ext_v0), (W - 0.15, ext_v1)):
            wall(mat, fr.p2(u0 + HT, vv), fr.p2(D - HT, vv), z0, z1, 0.3, windows_row(D - HT - u0 - HT, 2) if ext else [], hgl, tim,
                 wx=wxh(fr.dir(0, -1 if vv < 1 else 1)) if ext else None)
        # brick patches on plaster (street face, exposed end faces)
        if h["patches"] and MATS[h["gf"] if f == 0 else h["upper"]] == "plaster":
            patch_face(brk, fr.p2(u0, W), fr.p2(u0, 0), z0, z1, fr.dir(-1, 0), max(1, h["patches"]//(floors + 1)), rng, [dict(o, s=W - o["s"]) for o in ops])
            for vv, ext in ((0.0, ext_v0), (W, ext_v1)):
                if ext:
                    a, b = (fr.p2(u0 + HT, vv), fr.p2(D - HT, vv)) if vv == 0.0 else (fr.p2(D - HT, vv), fr.p2(u0 + HT, vv))
                    patch_face(brk, a, b, z0, z1, fr.dir(0, -1 if vv == 0.0 else 1), max(1, h["patches"]//(floors + 1)), rng,
                               [{"s": s_, "w": 0.95, "sill": 0.9, "h": 2.25} for s_ in ([o["s"] for o in windows_row(D - 2*HT - u0, 2)] if vv == 0.0 else [D - 2*HT - u0 - o["s"] for o in windows_row(D - 2*HT - u0, 2)])])
        if f >= 1:   # floor slab (reaching out under the jetty) with the stair hole of the flight arriving from below
            lane = st["u1"] if (f - 1) % 2 == 0 else st["u2"]
            hv0, hv1 = (v0, v0 + (n - 1)*tr) if (f - 1) % 2 == 0 else (v0 + tr, v0 + n*tr)
            u0i, u1i, va, vb = u0 + 0.05, D - HT, 0.3, W - 0.3
            for (a0, a1, b0, b1) in ((u0i, lane[0], va, vb), (lane[1], u1i, va, vb), (lane[0], lane[1], va, hv0), (lane[0], lane[1], hv1, vb)):
                if a1 - a0 > 0.01 and b1 - b0 > 0.01: fr.box(tim, a0, a1, b0, b1, z0 - SL, z0)
            if u0 < uface[f - 1] - 0.01:   # jetty: bressummer + projecting joist ends
                beam(tim, fr.M(u0 + 0.12, 0.0, z0 - SL - 0.1), fr.M(u0 + 0.12, W, z0 - SL - 0.1), 0.24, 0.22, up=(0, 0, 1))
                for j in range(int(W/0.7)):
                    vv = 0.35 + j*0.7; fr.box(tim, u0, uface[f - 1] + 0.3, vv - 0.08, vv + 0.08, z0 - SL - 0.32, z0 - SL)
            # guard rails around the hole
            if (f - 1) % 2 == 0:
                fr.box(tim, lane[0], lane[1], hv0 - 0.06, hv0, z0, z0 + 1.0)
            else:
                fr.box(tim, lane[0] - 0.06, lane[0], hv0, hv1, z0, z0 + 1.0); fr.box(tim, lane[1], lane[1] + 0.06, hv0, hv1, z0, z0 + 1.0)
                fr.box(tim, lane[0], lane[1], hv1, hv1 + 0.06, z0, z0 + 1.0)
        # partition with door (front room | back room)
        wall(plas, fr.p2(pu, 0.3), fr.p2(pu, W - 0.3), z0, min(z0 + SH - (SL if f < floors - 1 else 0), ze + 0.4), PT,
             [{"s": pdv - 0.3, "w": 0.9, "h": 2.1, "kind": "flat"}])
        c = fr.M(pu, pdv, z0)
        door_rec(f"{hid}_F{f}_part", f"{hid}_F{f}_front", f"{hid}_F{f}_back", c, fr.dir(1, 0), 0.9, 2.1, "door",
                 leaves=[add_leaf(f"DoorLeaf_{hid}_F{f}_part", f"{hid}_F{f}_part", fr.M(pu, pdv - 0.45, z0), fr.dir(0, 1), fr.dir(1, 0),
                                  0.88, 2.07, z0 + 0.01, thick=0.05)])
        # half-timber framing (plaster storeys only; ground floor too when it is plaster)
        if timber and MATS[h["gf"] if f == 0 else h["upper"]] == "plaster":
            timber_face(tim, fr, u0 - 0.03, W, z0, z1, timber, rng, [dict(o) for o in ops] if f else [o for o in ops], out=-1)
            timber_face(tim, fr, D + 0.03, W, z0, z1, timber, rng, rops, out=1)
    # ---- stairs
    ax, sgv = fr.axis_v()
    for f in range(floors - 1):
        lane = st["u1"] if f % 2 == 0 else st["u2"]
        if f % 2 == 0: va, vb, dvv = v0, v0 + n*tr, +1
        else: va, vb, dvv = v0, v0 + n*tr, -1
        p, q = fr.M(lane[0], va), fr.M(lane[1], vb)
        x0, x1, y0, y1 = min(p.x, q.x), max(p.x, q.x), min(p.y, q.y), max(p.y, q.y)
        cents, tt = stair(tim, x0, x1, y0, y1, zf[f], n, rz, ax, dvv*sgv, base=zf[f])
        um = (lane[0] + lane[1])/2
        if f % 2 == 0: ent, exi = fr.M(um, v0 - 0.6, zf[f]), fr.M(um, v0 + n*tr + 0.45, zf[f + 1])
        else: ent, exi = fr.M(um, v0 + n*tr + 0.45, zf[f]), fr.M(um, v0 - 0.5, zf[f + 1])
        stair_rec(f"{hid}_stair_{f}{f + 1}", f"{hid}_F{f}_front", f"{hid}_F{f + 1}_front", cents[:-1], rz, tt, ent, exi, lane[1] - lane[0])
        if f % 2 == 1:   # sloped balustrade panels along both sides of the second flight
            for uu in (lane[0] - 0.03, lane[1] + 0.03):
                a0, a1 = fr.M(uu, v0 + n*tr), fr.M(uu, v0)
                d = Vector((a1.x - a0.x, a1.y - a0.y, 0)); Lr = d.length
                extrude(tim, [(0, zf[f] + 0.05), (Lr, zf[f + 1] - rz + 0.05), (Lr, zf[f + 1] + 0.9), (0, zf[f] + 1.0)], Vector((a0.x, a0.y, 0)), d/Lr, (0, 0, 1), 0.05)
    # ---- street door leaf (+ optional pentice roof on brackets above it)
    dc = fr.M(HT/2, dv, PZ); tvec = fr.dir(0, 1); nvec = fr.dir(1, 0)
    hinge = dc - tvec*(HS["door_w"]/2)
    door_rec(f"{hid}_door", street, f"{hid}_F0_front", dc, nvec, HS["door_w"], HS["door_h"], "ext_door",
             leaves=[add_leaf(f"DoorLeaf_{hid}", f"{hid}_door", hinge, tvec, nvec, HS["door_w"], HS["door_h"] - 0.02, PZ + 0.01)])
    if h["pentice"]:
        zp = PZ + HS["door_h"] + 0.75; pw_ = HS["door_w"] + 1.0
        E0, E1 = fr.M(-0.95, dv - pw_/2, zp - 0.35), fr.M(-0.95, dv + pw_/2, zp - 0.35); R0, R1 = fr.M(0.0, dv - pw_/2, zp), fr.M(0.0, dv + pw_/2, zp)
        roof_slope(hsl, tim, E0, E1, R0, R1, rng, 0.0, cell=1.0, thick=0.08, purlins=False)
        for k in (-1, 1): beam(tim, fr.M(0.0, dv + k*(pw_/2 - 0.15), zp - 0.9), fr.M(-0.85, dv + k*(pw_/2 - 0.15), zp - 0.32), 0.1, 0.1)
    # ---- roof (gable, ridge along v over the top storey), end gables, street cross gables, dormers, chimneys
    tp = math.tan(math.radians(h["pitch"])); ov_ = HS["overhang"]; hd_ = (D - uf)/2; ur = uf + hd_
    zr_ = ze + hd_*tp; zeo_ = ze - ov_*tp
    HR = (RU["houses"].get(hid, {}) if RU else {})
    for ue in (uf - ov_, D + ov_):
        E0, E1 = fr.M(ue, -0.15, zeo_), fr.M(ue, W + 0.15, zeo_); R0, R1 = fr.M(ur, -0.15, zr_), fr.M(ur, W + 0.15, zr_)
        ex_ = None
        if "collapse" in HR and ue < ur:   # ruin: collapsed street-slope section (rafters / purlins exposed, partly broken)
            ex_ = ragged(HR["collapse"][0]*W, HR["collapse"][1]*W, 100 + seed, fr.v_of)
        roof_slope(hsl, tim, E0, E1, R0, R1, rng, h["holes"], cell=1.1, thick=0.16, exposed=ex_, sag=HR.get("sag", 0.0))
    for vv, ext in ((0.15, ext_v0), (W - 0.15, ext_v1)):
        gm = upm if (ext and not h.get("gable_timber")) else plas
        gable(gm, fr.p2(uf, vv), fr.p2(D, vv), ze, zr_ - 0.12, 0.3)
        if ext:   # attic window in the exposed end gable (+ timber framing on a half-timbered gable)
            a = fr.M(ur - 0.5, vv + (-0.17 if vv < 1 else 0.17), 0); b = fr.M(ur + 0.5, vv + (-0.17 if vv < 1 else 0.17), 0)
            extrude(hgl, [(0, ze + 1.0), (1.0, ze + 1.0), (1.0, ze + 2.1), (0, ze + 2.1)], Vector((a.x, a.y, 0)), Vector((b.x - a.x, b.y - a.y, 0)).normalized(), (0, 0, 1), 0.06)
            if h.get("gable_timber") or (timber and MATS[h["upper"]] == "plaster"):
                vo = vv + (-0.19 if vv < 1 else 0.19)
                beam(tim, fr.M(uf + 0.1, vo, ze + 0.05), fr.M(D - 0.1, vo, ze + 0.05), 0.16, 0.08, up=(0, 0, 1))
                for uu in (uf + hd_*0.35, ur - 0.8, ur + 0.8, D - hd_*0.35):
                    ztop = ze + (min(uu - uf, D - uu))*tp - 0.2
                    beam(tim, fr.M(uu, vo, ze), fr.M(uu, vo, ztop), 0.14, 0.08, up=fr.dir(0, 1))
                beam(tim, fr.M(uf + 0.2, vo, ze + 0.1), fr.M(ur, vo, zr_ - 0.3), 0.14, 0.08, up=fr.dir(0, 1))
                beam(tim, fr.M(D - 0.2, vo, ze + 0.1), fr.M(ur, vo, zr_ - 0.3), 0.14, 0.08, up=fr.dir(0, 1))
    for (vfrac, hw0) in h["cross"]:
        hw = min(hw0, W/2 - 0.6, hd_ - 0.3); vc = min(max(vfrac*W, hw + 0.3), W - hw - 0.3); za = ze + hw*tp
        for sgn in (-1, 1):
            E0, E1 = fr.M(uf - ov_, vc + sgn*(hw + 0.2), ze - 0.2*tp), fr.M(uf + hw + 0.6, vc + sgn*(hw + 0.2), ze - 0.2*tp)
            R0, R1 = fr.M(uf - ov_, vc, za), fr.M(uf + hw + 0.6, vc, za)
            if sgn > 0: E0, E1, R0, R1 = E1, E0, R1, R0
            roof_slope(hsl, tim, E0, E1, R0, R1, rng, h["holes"]*0.8, cell=1.1, thick=0.14)
        gable(upm if MATS[h["upper"]] != "plaster" else plas, fr.p2(uf + HT/2, vc - hw), fr.p2(uf + HT/2, vc + hw), ze, za - 0.1, HT)
        nwin = 2 if hw > 3.5 else 1
        for k in range(nwin):
            vw = vc + (0 if nwin == 1 else (-0.8 if k == 0 else 0.8))
            a = fr.M(uf - 0.02, vw - 0.5, 0); b = fr.M(uf - 0.02, vw + 0.5, 0)
            extrude(hgl, [(0, ze + 0.4), (1.0, ze + 0.4), (1.0, ze + 1.6), (0, ze + 1.6)], Vector((a.x, a.y, 0)), Vector((b.x - a.x, b.y - a.y, 0)).normalized(), (0, 0, 1), 0.06)
        if timber and MATS[h["upper"]] == "plaster":
            for k in (-1, 1):
                beam(tim, fr.M(uf - 0.04, vc + k*hw, ze), fr.M(uf - 0.04, vc, za - 0.1), 0.16, 0.08, up=fr.dir(1, 0))
                beam(tim, fr.M(uf - 0.04, vc + k*hw*0.55, ze), fr.M(uf - 0.04, vc + k*hw*0.55, ze + hw*0.45*tp), 0.12, 0.07, up=fr.dir(1, 0))
            beam(tim, fr.M(uf - 0.04, vc - hw, ze + 0.05), fr.M(uf - 0.04, vc + hw, ze + 0.05), 0.08, 0.18, up=(0, 0, 1))
            beam(tim, fr.M(uf - 0.04, vc - hw*0.5, ze + hw*0.5*tp), fr.M(uf - 0.04, vc + hw*0.5, ze + hw*0.5*tp), 0.08, 0.14, up=(0, 0, 1))
    for vfrac in h["dormers"]:
        dormer(G, fr, uf + 0.9, min(max(vfrac*W, 1.3), W - 1.3), ze, tp, hsl, hgl, tim, rng, timber, PL)
    mfr = Mirror(fr, D)
    for vfrac in h["rear_dormers"]:
        dormer(G, mfr, 0.9, min(max(vfrac*W, 1.3), W - 1.3), ze, tp, hsl, hgl, tim, rng, timber, PL)
    ch = HS["chimney"]
    for (vfrac, ufrac) in h["chimneys"]:
        vv = min(max(vfrac*W, ch["w"]/2 + 0.3), W - ch["w"]/2 - 0.3); uc = uf + ufrac*(D - uf) - ch["d"]/2
        uc = min(max(uc, uf + 0.4), D - ch["d"] - 0.4)
        top = zr_ + ch["above_ridge"] + rng.uniform(-0.4, 0.5)
        if RU and RR.random() < RU["chimney_collapse_frac"]:   # ruin: stack collapsed to a jagged stump, cap + pots gone
            zs_ = ze + (zr_ - ze)*RR.uniform(0.55, 0.9); zb_ = max(ze - 1.0, zf[-1] + 2.3)
            fr.box(chim, uc, uc + ch["d"], vv - ch["w"]/2, vv + ch["w"]/2, zb_, zs_)
            fr.box(chim, uc, uc + ch["d"]*RR.uniform(0.4, 0.7), vv - ch["w"]/2, vv + ch["w"]*RR.uniform(-0.2, 0.3), zs_, zs_ + RR.uniform(0.3, 0.7))
            for _ in ((-0.35, 0.35) if ch["d"] > 1.2 else (0.0,)): rng.uniform(0.4, 0.7)   # keep the house rng stream in step
            continue
        fr.box(chim, uc, uc + ch["d"], vv - ch["w"]/2, vv + ch["w"]/2, max(ze - 1.0, zf[-1] + 2.3), top)
        fr.box(SC.B("Chimneys", "stone"), uc - 0.08, uc + ch["d"] + 0.08, vv - ch["w"]/2 - 0.08, vv + ch["w"]/2 + 0.08, top - 0.35, top - 0.15)   # stone cap course
        cc = fr.M(uc + ch["d"]/2, vv)
        for k in ((-0.35, 0.35) if ch["d"] > 1.2 else (0.0,)):
            q = cc + fr.dir(1, 0)*k; cyl(chim, q.x, q.y, 0.17, top, top + rng.uniform(0.4, 0.7), n=8)
    # rubble end wall (ruined masonry mass against the outer gable of a corner house)
    if h.get("rubble_end"):
        rub = SC.B(G, "rubble"); vv = -0.9 if h["rubble_end"] == "v0" else W + 0.9
        for j in range(6):
            uu = 0.4 + j*(D - 0.8)/6; zt = PZ + rng.uniform(2.2, 6.5)*(1 - abs(j - 2.5)/4)
            fr.box(rub, uu, uu + (D - 0.8)/6 + 0.05, min(vv, vv + (0.9 if vv < 0 else -0.9)), max(vv, vv + (0.9 if vv < 0 else -0.9)), PZ, max(PZ + 1.2, zt))
    # street-face plinth course (gap at the street door)
    dv0, dv1 = dv - HS["door_w"]/2, dv + HS["door_w"]/2
    fr.box(SC.B(G, "stone"), -0.08, HT, 0.0, dv0, PZ, PZ + 0.35); fr.box(SC.B(G, "stone"), -0.08, HT, dv1, W, PZ, PZ + 0.35)
    return ze, zr_

hx0, hx1 = HS["row_x"]; ry0, ry1 = HS["row_y"]; Dh = hx1 - hx0
HL = {h["id"]: h for h in HS["list"]}
for side in ("W", "E"):
    street = "street_W" if side == "W" else "street_E"; hs = [h for h in HS["list"] if h["row"] == side]; vs = 0.0
    for i, h in enumerate(hs):
        fr = Frame(side, hx0 + h["setback"], ry1 - vs)
        house(h, fr, Dh - h["setback"], street, ext_v0=(i == 0), ext_v1=(i == len(hs) - 1), seed=i + (10 if side == "E" else 0))
        vs += h["w"]
cn = HS["corner"]
for nm, x0 in (("NW", -cn["x"][1]), ("NE", cn["x"][0])):
    fr = Frame("N", cn["y"][0], x0); h = dict(HL[nm], w=cn["x"][1] - cn["x"][0])
    house(h, fr, cn["y"][1] - cn["y"][0], "north_W" if nm == "NW" else "north_E", ext_v0=True, ext_v1=True, seed=40 + (nm == "NE"))
pin("streets")
# outdoor street spaces + open links (paths checked for floor continuity and clearance)
sx_ = (hx0 + ahw + wt/2 + C["buttress_out"])/2
for sg, nm in ((-1, "W"), (1, "E")):
    space(f"street_{nm}", (sg*sx_, 10.0, PZ), "outdoor"); space(f"north_{nm}", (sg*12.5, 44.0, PZ), "outdoor")
    open_link("plaza", f"street_{nm}", [(0, -12, PZ), (0, -4.5, PZ), (sg*sx_, -4.5, PZ), (sg*sx_, 10.0, PZ)])
    open_link(f"street_{nm}", f"north_{nm}", [(sg*sx_, 10.0, PZ), (sg*sx_, yB + 0.9, PZ), (sg*12.5, yB + 1.1, PZ), (sg*12.5, 44.0, PZ)])

# =====================================================================================
# 3b. ruin: rubble piles + fallen rafters (colliding, only where the circulation keep-out test allows), debris (decor)
# =====================================================================================
def _sd(p, a, b):
    ax, ay, bx, by = a[0], a[1], b[0], b[1]; dx, dy = bx - ax, by - ay; L2 = dx*dx + dy*dy
    t = 0.0 if L2 < 1e-9 else max(0.0, min(1.0, ((p[0] - ax)*dx + (p[1] - ay)*dy)/L2))
    return math.hypot(p[0] - ax - t*dx, p[1] - ay - t*dy)
def clear_spot(x, y, z, r):
    """True if a colliding obstacle of plan radius r at (x,y,z) keeps clear of every door/opening ray corridor, stair flight,
    space probe, outdoor link path and walk-test corridor (ruin.keepout_paths)"""
    for d in SP["doors"]:
        c, n_, t_ = d["center"], d["normal"], d["tangent"]
        if abs(c[2] - z) > 2.5: continue
        dx, dy = x - c[0], y - c[1]; sl, ql = dx*t_[0] + dy*t_[1], dx*n_[0] + dy*n_[1]
        if abs(sl) < d["w"]/2 + 0.4 + r and abs(ql) < (1.5 if d["type"] == "opening" else 1.2) + 0.4 + r: return False
    for st in SP["stairs"]:
        pts = st["steps"] + [st["entry"], st["exit"]]
        if min(abs(p[2] - z) for p in pts) > 2.5: continue
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]; m = st["width"]/2 + 0.8 + r
        if min(xs) - m < x < max(xs) + m and min(ys) - m < y < max(ys) + m: return False
    for sp in SP["spaces"].values():
        if abs(sp["z"] - z) < 2.5 and math.hypot(x - sp["probe"][0], y - sp["probe"][1]) < 1.2 + r: return False
    for ln in SP["open_links"]:
        for a, b in zip(ln["path"], ln["path"][1:]):
            if abs(a[2] - z) < 2.5 and _sd((x, y), a, b) < 1.0 + r: return False
    KO = RU["keepout_paths"]
    for line in KO["lines"]:
        for a, b in zip(line, line[1:]):
            if _sd((x, y), a, b) < KO["r"] + r: return False
    rg = dict(KO["ring"], c=(0.0, cy))   # ambulatory ring follows the apse centre
    if y > rg["c"][1] - 1.0 and abs(math.hypot(x - rg["c"][0], y - rg["c"][1]) - rg["r"]) < rg["w"] + r: return False
    return True
def chips(n, x0, x1, y0, y1, z, mats, size=(0.06, 0.28), pred=None):
    """decor debris: small tilted stone / slate / brick / timber pieces (role decor -> no collision, never blocks a path)"""
    k = 0
    for _ in range(n*3):
        if k >= n: break
        x, y = RR.uniform(x0, x1), RR.uniform(y0, y1)
        if pred and not pred(x, y): continue
        bk = RR.choice(mats); sz = RR.uniform(*size); a = RR.uniform(0, 6.283)
        hz = 0.012 if bk is DEB_sl else min(0.06, sz*RR.uniform(0.2, 0.45))
        tl = RR.uniform(-0.25, 0.25)
        obox(bk, (x, y, z + hz*0.8), (math.cos(a), math.sin(a), tl), (-math.sin(a), math.cos(a), 0), (0, 0, 1), sz/2, sz*RR.uniform(0.3, 0.5), hz)
        k += 1
def rubble_pile(cx, cy_, z, r, h, mats, nb=26):
    """heap of fallen ashlar / rubble blocks: low irregular mound + tumbled blocks, highest in the middle"""
    prism(DEB_pile, ngon(cx, cy_, r*0.75, 7, RR.uniform(0, 1)), z, z + h*0.35)
    prism(DEB_pile, ngon(cx + RR.uniform(-0.2, 0.2), cy_ + RR.uniform(-0.2, 0.2), r*0.45, 6, RR.uniform(0, 1)), z, z + h*0.6)
    for _ in range(nb):
        a, rr = RR.uniform(0, 6.283), r*math.sqrt(RR.random())*0.95; hx = RR.uniform(0.15, 0.4); f = 1 - (rr/r)**2
        zc = z + max(hx*0.5, h*f*RR.uniform(0.45, 0.95)); b = RR.uniform(0, 6.283)
        obox(RR.choice(mats), (cx + rr*math.cos(a), cy_ + rr*math.sin(a), zc), (math.cos(b), math.sin(b), RR.uniform(-0.4, 0.4)), (-math.sin(b), math.cos(b), RR.uniform(-0.3, 0.3)), (0, 0, 1), hx, hx*RR.uniform(0.5, 0.9), hx*RR.uniform(0.4, 0.7))
    chips(RU["debris"]["per_pile"], cx - r*1.6, cx + r*1.6, cy_ - r*1.6, cy_ + r*1.6, z, [DEB_st, DEB_rb, DEB_sl], pred=lambda x, y: math.hypot(x - cx, y - cy_) > r*0.8)
RUIN_LOG = {"piles": [], "rafters": 0, "rejected": 0, "roof_holes": ROOF_HOLES}
if RU:
    DEB_pile = SC.B("Ruin", "rubble"); RSt = SC.B("Ruin", "stone"); RTb = SC.B("Ruin", "timber")
    RB_ = RU["rubble"]; KR = RB_["keepout_r"]
    def place(n, gen, r, h, mats, tag):
        k = 0
        for _ in range(n*40):
            if k >= n: break
            x, y, z = gen()
            if not clear_spot(x, y, z, r + 0.15): RUIN_LOG["rejected"] += 1; continue
            if any(math.hypot(x - p[0], y - p[1]) < r + p[3] + 0.4 for p in RUIN_LOG["piles"]): continue
            rubble_pile(x, y, z, r, h, mats); RUIN_LOG["piles"].append((round(x, 2), round(y, 2), round(z, 2), r, tag)); k += 1
    pin("rubble_nave")
    # inside the nave under the collapsed east slope (ref: rubble inside the nave), west slope hole, aisles against the outer wall
    for (px, py) in NAVE_PILES:
        if clear_spot(px, py, ZC, 0.9): rubble_pile(px, py, ZC, 0.9, 1.6, [RSt, RSt, DEB_pile], nb=40); RUIN_LOG["piles"].append((round(px, 2), round(py, 2), ZC, 0.9, "nave"))
        else: RUIN_LOG["rejected"] += 1
    pin("rubble_aisle"); place(RB_["aisle_piles"], lambda: (RR.choice((-1, 1))*RR.uniform(11.2, 11.9), RR.uniform(12.0, 34.0), ZC), 0.65, 1.0, [RSt, DEB_pile], "aisle")
    # at the wall bases outside: podium strip between the aisle buttresses, round the apse between the buttress piers
    pin("rubble_exterior"); place(RB_["exterior_piles"], lambda: (RR.choice((-1, 1))*RR.uniform(13.9, 14.6), RR.uniform(5.0, 35.0), ZC), 0.6, 0.9, [RSt, DEB_pile], "aisle base")
    def apse_gen():
        k = RR.randrange(6); a = math.pi*(k + 0.5)/6; rr = RR.uniform(9.1, 9.4); return (rr*math.cos(a), cy + rr*math.sin(a), ZC)
    pin("rubble_apse"); place(RB_["apse_piles"], apse_gen, 0.55, 0.8, [RSt, DEB_pile], "apse base")
    # fallen rafters / tie-beams from the collapsed roof, lying across the pews (east side) - cleared like the piles
    pin("rubble_rafters"); k = 0
    for _ in range(200):
        if k >= RB_["fallen_rafters"]: break
        x0_, y0_ = RR.uniform(1.8, 4.2), RR.uniform(12.0, 30.0); a = RR.uniform(-1.2, 1.2) + math.pi/2; L = RR.uniform(3.0, 5.5)
        x1_, y1_ = x0_ + math.cos(a)*L*0.3, y0_ + math.sin(a)*L
        pts = [(x0_ + (x1_ - x0_)*f, y0_ + (y1_ - y0_)*f) for f in (0, 0.25, 0.5, 0.75, 1)]
        if not all(clear_spot(px, py, ZC, 0.35) for px, py in pts) or not all(1.7 < px < 4.6 for px, _ in pts): continue
        beam(RTb, (x0_, y0_, ZC + RR.uniform(0.15, 0.3)), (x1_, y1_, ZC + RR.uniform(0.7, 1.4)), 0.24, 0.3, up=(RR.uniform(-0.3, 0.3), 0.0, 1.0)); k += 1
    RUIN_LOG["rafters"] = k
    D_ = RU["debris"]; pin("debris")
    chips(D_["nave"], -5.0, 5.0, 8.0, 37.0, ZC, [DEB_st, DEB_sl, DEB_sl, DEB_sl, DEB_tb, DEB_rb], size=(0.05, 0.3))
    chips(D_["wall_base"]//2, -15.2, 15.2, 4.0, 36.0, ZC, [DEB_st, DEB_rb], pred=lambda x, y: 13.6 < abs(x) < 15.3)
    chips(D_["wall_base"]//2, -hx0, hx0, ry0, ry1, PZ, [DEB_br, DEB_sl, DEB_rb, DEB_tb], pred=lambda x, y: hx0 - 1.1 < abs(x) < hx0 - 0.1)
    chips(D_["plaza"], -16.0, 16.0, -33.0, -6.0, PZ, [DEB_st, DEB_sl, DEB_rb])
    pin("debris_stairs")
    for st_id in ("cathedral_steps", "stairs_south_upper", "stairs_south_lower"):   # chips + cracked / spalled treads near the step ends
        st = next(q for q in SP["stairs"] if q["id"] == st_id); hw = st["width"]/2
        for p in RR.sample(st["steps"], min(len(st["steps"]), D_["stairs"]//3)):
            sx = RR.choice((-1, 1))*RR.uniform(hw - 1.2, hw - 0.25)
            chips(2, p[0] + sx - 0.3, p[0] + sx + 0.3, p[1] - 0.1, p[1] + 0.1, p[2], [DEB_st])
            if RR.random() < 0.6:
                cx_, sz = p[0] + RR.uniform(-hw + 0.6, hw - 0.6), RR.uniform(0.5, 0.9)
                geom.DECAL["crack"].face_uv([(cx_ - sz/2, p[1] - 0.14, p[2] + 0.006), (cx_ + sz/2, p[1] - 0.14, p[2] + 0.006), (cx_ + sz/2, p[1] + 0.14, p[2] + 0.006), (cx_ - sz/2, p[1] + 0.14, p[2] + 0.006)],
                                            [(0, 0.3), (1, 0.3), (1, 0.62), (0, 0.62)])
    print("ruin:", {k: (len(v) if isinstance(v, list) else v) for k, v in RUIN_LOG.items()})
    json.dump(RUIN_LOG, open(os.path.join(OUT, "ruin_log.json"), "w"), indent=0)

if DUMP_PINS: json.dump(_PINS, open(PIN_FILE, "w")); print("ruin streams recorded:", len(_PINS), "pins ->", PIN_FILE)
else: print("ruin pins:", len(PINS_USED), "used,", len([p for p in PINS_USED if p not in _PINS]), "seeded by name")
# =====================================================================================
# 4. materials, objects, spaces.json, export
# =====================================================================================
for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
for m in list(bpy.data.meshes): bpy.data.meshes.remove(m)
MATS = {}
MPROPS = {"brick_red": (0.9, 0.0), "stair": (0.9, 0.0), "stair_riser": (0.92, 0.0), "stair_side": (0.9, 0.0), "stone": (0.85, 0.0), "rubble": (0.95, 0.0), "slate": (0.6, 0.0), "brick": (0.9, 0.0), "plaster": (0.92, 0.0), "plaster_b": (0.92, 0.0), "plaster_c": (0.92, 0.0), "timber": (0.8, 0.0),
          "cobble": (0.9, 0.0), "iron": (0.62, 0.55), "glass": (0.3, 0.2), "soil": (1.0, 0.0), "stone_moss": (0.92, 0.0), "rubble_moss": (0.97, 0.0),
          "decal_streak": (0.95, 0.0), "decal_grime": (0.97, 0.0), "decal_crack": (0.95, 0.0), "decal_lath": (0.9, 0.0)}
NMAP = {"stone": "stone_n", "stone_moss": "stone_n", "slate": "slate_n", "brick": "brick_n", "brick_red": "brick_n", "cobble": "cobble_n",
        "stair": "stair_n", "stair_riser": "stair_riser_n", "stair_side": "stair_side_n", "rubble": "rubble_n", "rubble_moss": "rubble_n", "soil": "soil_n"}
NSTR = {"slate": 0.9, "cobble": 1.0, "stair": 0.9, "soil": 1.0}
def material(name):
    if name in MATS: return MATS[name]
    m = bpy.data.materials.new(name.capitalize()); m.use_nodes = True
    nt = m.node_tree; bsdf = nt.nodes["Principled BSDF"]
    img = bpy.data.images.load(os.path.join(ROOT, "tex", name + ".png")); tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = img
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value, bsdf.inputs["Metallic"].default_value = MPROPS[name]
    nm = NMAP.get(name)   # tangent-space normal map (gap #7) from the texture's own height field -> glTF normalTexture
    if nm and os.path.exists(os.path.join(ROOT, "tex", nm + ".png")):
        ni = bpy.data.images.load(os.path.join(ROOT, "tex", nm + ".png")); ni.colorspace_settings.name = "Non-Color"
        nt_ = nt.nodes.new("ShaderNodeTexImage"); nt_.image = ni; nmn = nt.nodes.new("ShaderNodeNormalMap"); nmn.inputs["Strength"].default_value = NSTR.get(name, 0.8)
        nt.links.new(nt_.outputs["Color"], nmn.inputs["Color"]); nt.links.new(nmn.outputs["Normal"], bsdf.inputs["Normal"])
    if name.startswith("decal_"):   # alpha-blended decal (glTF alphaMode BLEND); no shadow casting
        nt.links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"]); m.surface_render_method = "BLENDED"
        try: m.use_transparent_shadow = True
        except Exception: pass
    MATS[name] = m; return m
col = bpy.context.scene.collection
def make_obj(name, bk, origin=None, props=None):
    if not bk.f: return None
    me = bpy.data.meshes.new(name)
    verts = [tuple(v - origin) if origin is not None else tuple(v) for v in bk.v]
    me.from_pydata(verts, [], bk.f)
    uvl = me.uv_layers.new(name="UVMap")
    flat = [c for uv in bk.uv for c in uv]; uvl.data.foreach_set("uv", flat)
    me.materials.append(material(bk.mat)); me.validate(clean_customdata=False); me.update()
    ob = bpy.data.objects.new(name, me); col.objects.link(ob)
    if origin is not None: ob.location = origin
    for k, v in (props or {}).items(): ob[k] = v
    return ob
ROLE = {"Approach": "approach", "Base": "base", "Glass": "glass", "Decal": "decor", "Debris": "decor"}
nf = 0
for (g, m), bk in sorted(SC.b.items()):
    ob = make_obj(f"{g}_{m}", bk, props={"role": ROLE.get(g, "solid"), "group": g}); nf += bk.nfaces()
for (name, bk, hinge, props) in LEAVES:   # hinge empty (rotated by the viewer) + child mesh in hinge-local coords
    emp = bpy.data.objects.new(name, None); col.objects.link(emp); emp.location = Vector(hinge); emp.empty_display_size = 0.3
    for k, v in props.items(): emp[k] = v
    ch = make_obj(name + "_mesh", bk, origin=Vector(hinge), props={"role": "door_leaf_mesh"}); ch.location = (0, 0, 0); ch.parent = emp; nf += bk.nfaces()
print(f"objects: {len(bpy.data.objects)}  faces: {nf}  leaves: {len(LEAVES)}  spaces: {len(SP['spaces'])}  doors: {len(SP['doors'])}  stairs: {len(SP['stairs'])}  t={time.time() - T0:.1f}s")
SP["meta"] = {"plaza_z": PZ, "cathedral_floor_z": ZC, "params": os.path.basename(os.environ.get("PARAMS", "params.json"))}
json.dump(SP, open(os.path.join(OUT, "spaces.json"), "w"), indent=0)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "building.blend"))
if not os.environ.get("NO_EXPORT"):
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "building.glb"), export_format="GLB", export_extras=True, export_yup=True, export_apply=False)
print(f"BUILD OK t={time.time() - T0:.1f}s")
