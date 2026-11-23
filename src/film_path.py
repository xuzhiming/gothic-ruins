"""Camera paths for the final videos -> final/video/{walk,orbit}_path.json (per frame: eye, target, fov, door opening).
walk: the walk-test route (walk/trajectory.csv, recorded by walk/walk_test.py, collision-checked) approach -> south stairs -> plaza ->
cathedral steps -> portal -> nave -> apse | dissolve | portal (leaving) -> steps -> west street -> W3 door -> W3 ground floor.
Resampled by arc length, gaussian-smoothed (no jitter), speed profile: cruise V m/s, slower on stairs / near doors / in turns,
eased start/stop; heading = smoothed look-ahead; doors open with the preview rule (within 3.2 m, 2.4/s, smoothstep).
  python3 src/film_path.py [--fps 24] [--v 1.8]"""
import json, csv, os, sys, math, numpy as np
from scipy.ndimage import gaussian_filter1d
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); OUT = os.path.join(R, "final", "video"); os.makedirs(OUT, exist_ok=True)
arg = lambda k, d: float(sys.argv[sys.argv.index(k) + 1]) if k in sys.argv else d
FPS = int(arg("--fps", 24)); V = arg("--v", 2.5); ALAT = arg("--alat", 0.9); EYE = 1.65; DS = 0.05; OPEN = 4.5   # preview opens at 3.2 m; the film anticipates a little so leaves are open before the camera arrives
T = np.array([[float(r["x"]), float(r["y"]), float(r["z"])] for r in csv.DictReader(open(os.path.join(R, "walk", "trajectory.csv")))])
EV = json.load(open(os.path.join(R, "walk", "walk_result.json")))["events"]; IDX = {}; st = 0
for e in EV:
    d = np.linalg.norm(T[st:] - np.array(e["at"]), axis=1); IDX[e["shot"]] = st + int(np.argmin(d)); st = IDX[e["shot"]]
S = json.load(open(os.path.join(R, "spaces.json"))); DOORS = [d for d in S["doors"] if d.get("leaves")]
def dedup(P):
    keep = [0]
    for i in range(1, len(P)):
        if np.linalg.norm(P[i, :2] - P[keep[-1], :2]) > 0.02: keep.append(i)
    return P[keep]
def resample(P):
    P = dedup(P); s = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(P[:, :2], axis=0), axis=1))]); n = int(s[-1]/DS) + 1
    ss = np.linspace(0, s[-1], n); return np.stack([np.interp(ss, s, P[:, k]) for k in range(3)], 1), ss
def segment(P, look_bias=None, v=V):
    P, ss = resample(P); sm = P.copy()
    sm[:, 0] = gaussian_filter1d(P[:, 0], 0.6/DS, mode="nearest"); sm[:, 1] = gaussian_filter1d(P[:, 1], 0.6/DS, mode="nearest")
    sm[:, 2] = gaussian_filter1d(P[:, 2], 0.9/DS, mode="nearest")
    # speed profile
    hd = np.unwrap(np.arctan2(np.gradient(sm[:, 1]), np.gradient(sm[:, 0]))); kap = np.abs(gaussian_filter1d(np.gradient(hd)/DS, 0.5/DS))
    slope = np.abs(np.gradient(sm[:, 2])/DS); vv = np.minimum(V if v is None else v, np.sqrt(ALAT/np.maximum(kap, 1e-3)))
    vv = np.where(slope > 0.12, np.minimum(vv, 1.5), vv)
    for d in DOORS:
        dd = np.hypot(sm[:, 0] - d["center"][0], sm[:, 1] - d["center"][1]); vv = np.where((dd < 2.5) & (np.abs(sm[:, 2] - d["center"][2]) < 2), np.minimum(vv, 1.2), vv)
    vv = gaussian_filter1d(vv, 1.5/DS, mode="nearest"); ramp = np.minimum(1, np.minimum(ss, ss[-1] - ss)/2.5); vv = np.maximum(vv*np.sqrt(np.clip(ramp, 0, 1)), 0.12)
    t = np.concatenate([[0], np.cumsum(DS/vv[:-1])]); n = int(t[-1]*FPS) + 1; tf = np.arange(n)/FPS
    sf = np.interp(tf, t, ss); pos = np.stack([np.interp(sf, ss, sm[:, k]) for k in range(3)], 1)
    # heading: point 4 m ahead on the smoothed path, then smoothed in time (slow turns)
    ahead = np.stack([np.interp(np.minimum(sf + 4.0, ss[-1]), ss, sm[:, k]) for k in range(3)], 1)
    dirv = ahead - pos; dirv[:, 2] = (ahead[:, 2] - pos[:, 2])*0.5
    if look_bias is not None: dirv = look_bias(pos, sf/ss[-1], dirv)
    dirv[:, :2] /= np.maximum(np.linalg.norm(dirv[:, :2], axis=1, keepdims=True), 1e-6)
    for k in range(3): dirv[:, k] = gaussian_filter1d(dirv[:, k], 0.8*FPS, mode="nearest")
    nh = np.linalg.norm(dirv[:, :2], axis=1); dirv[:, 2] = np.clip(dirv[:, 2], -0.2*nh, 0.21*nh)   # pitch within about -11..+12 deg
    eye = pos + np.array([0, 0, EYE]); tgt = eye + dirv*np.array([6, 6, 6])
    return eye, tgt
def bias_A(pos, u, d):   # on the plaza look partly at the facade / rose window, in the nave lift the gaze toward the vaults
    out = d.copy(); face = np.array([0.0, 3.9, 19.0])
    for i, p in enumerate(pos):
        if -33.5 < p[1] < -4.0 and p[2] > 3.5:
            w = 0.55*min(1, (p[1] + 33.5)/6, (-4.0 - p[1])/4 + 0.4); f = face - (p + [0, 0, EYE]); f /= np.linalg.norm(f[:2])
            out[i] = (1 - w)*d[i]/max(np.linalg.norm(d[i, :2]), 1e-6) + w*f
        elif p[1] > 6 and p[2] > 6.0: out[i, 2] += 0.25
    return out
def doors(eye):
    tv = {d["id"]: 0.0 for d in DOORS}; res = []
    for e in eye:
        feet = e - [0, 0, EYE]
        for d in DOORS:
            near = math.hypot(feet[0] - d["center"][0], feet[1] - d["center"][1]) < OPEN and abs(feet[2] - d["center"][2]) < 2.0
            tv[d["id"]] = min(1, max(0, tv[d["id"]] + (1 if near else -1)*2.4/FPS))
        res.append({k: round(v, 3) for k, v in tv.items() if v > 0})
    return res
segs = []
A = T[:IDX["06_apse"] + 1]; segs.append(("A", segment(A, bias_A)))
i0 = IDX["09_leaving"]; ib = next(i for i in range(i0, len(T)) if T[i, 1] < -4.3 and T[i, 2] < 4.3)
j = IDX["10_gate_yard_E"] + int(np.argmin(np.linalg.norm(T[IDX["10_gate_yard_E"]:IDX["11_street_W"], :2] - [-17.7, -4.5], axis=1)))
mid = np.array([[x, -4.5, 4.2] for x in np.linspace(T[ib, 0] - 1.0, -16.5, 30)])
B = np.concatenate([T[i0:ib + 1], mid, T[j:IDX["12_house_W3_GF"] + 1]]); segs.append(("B", segment(B)))
total = 0
for name, (eye, tgt) in segs:
    fr = [{"eye": [round(float(v), 3) for v in e], "target": [round(float(v), 3) for v in t], "fov": 50} for e, t in zip(eye, tgt)]
    for f, dt in zip(fr, doors(eye)): f["doors"] = dt
    json.dump({"fps": FPS, "frames": fr}, open(os.path.join(OUT, f"walk_{name}_path.json"), "w")); total += len(fr)/FPS
    L = float(np.linalg.norm(np.diff(eye[:, :2], axis=0), axis=1).sum()); print(f"walk {name}: {len(fr)} frames {len(fr)/FPS:.1f} s, {L:.1f} m, mean {L/(len(fr)/FPS):.2f} m/s")
# orbit: 18 s, one revolution, radius 92 m, 52 m up, looking at the crossing
n = 18*FPS; fr = []
for k in range(n):
    a = math.radians(-112) + 2*math.pi*k/n*(1 - 0.0); a = math.radians(-112) + 2*math.pi*(0.5 - 0.5*math.cos(math.pi*k/n))  # eased
    fr.append({"eye": [round(92*math.cos(a), 3), round(92*math.sin(a) + 2, 3), 52.0], "target": [0.0, 2.0, 6.0], "fov": 42, "doors": {}})
json.dump({"fps": FPS, "frames": fr}, open(os.path.join(OUT, "orbit_path.json"), "w")); print("orbit", n, "frames", n/FPS, "s; walk total", round(total, 1), "s")
