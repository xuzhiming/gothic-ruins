"""Automatic compare -> adjust -> rebuild loop.
   ROUNDS=4 python3 compare/compare_loop.py        (ROUNDS=0: just score the current params, no changes)
Each round: build (blender -b -P build.py, PARAMS=work/rN/params.json) -> metric ortho silhouettes (src/render_sil.py)
-> compare.py (IoU, skyline error, footprint) -> per-zone skyline errors -> change the parameters behind the zones with the
largest error (param -= gain * error, clamped) -> next round. A round whose objective gets worse is reverted (gain halved).
Every round's scores, zone errors and parameter changes are appended to compare_log.md."""
import json, os, subprocess, sys, copy, shutil, time, datetime
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
BL = os.environ.get("BLENDER", "blender"); ROUNDS = int(os.environ.get("ROUNDS", "4")); MPP = os.environ.get("LOOP_MPP", "0.2")
LOG = os.environ.get("COMPARE_LOG", os.path.join(ROOT, "compare_log.md")); WORK = os.path.join(HERE, "work"); os.makedirs(WORK, exist_ok=True)
# zone: (view, u0, u1, parameter path, statistic). u = horizontal metres in that view (south: +X, north: -X, west: -Y, east: +Y)
ZONES = [("south", -11.0, -4.0, "cathedral.tower_sw.spire_tip", "max"), ("north", 4.0, 11.0, "cathedral.tower_sw.spire_tip", "max"),
         ("south", -1.5, 1.5, "cathedral.facade_apex", "max"),
         ("south", 8.0, 10.5, "cathedral.tower_se.spire_tip", "max"), ("north", -10.5, -8.0, "cathedral.tower_se.spire_tip", "max"),
         ("west", -30.0, -14.0, "cathedral.nave_ridge", "mean"), ("east", 14.0, 30.0, "cathedral.nave_ridge", "mean"), ("north", -3.5, 3.5, "cathedral.nave_ridge", "mean"),
         ("south", -31.0, -21.0, "houses.eave_extra", "mean"), ("south", 21.0, 31.0, "houses.eave_extra", "mean"),
         ("north", -31.0, -21.0, "houses.eave_extra", "mean"), ("north", 21.0, 31.0, "houses.eave_extra", "mean"),
         ("west", -40.0, -33.0, "cathedral.apse.wall_top", "mean"), ("east", 33.0, 40.0, "cathedral.apse.wall_top", "mean"),
         ("south", 12.6, 15.2, "cathedral.pinnacle_h", "max"), ("south", -15.2, -13.8, "cathedral.pinnacle_h", "max")]
BOUNDS = {"cathedral.tower_sw.spire_tip": (34, 46), "cathedral.facade_apex": (27, 35), "cathedral.tower_se.spire_tip": (22, 32), "cathedral.nave_ridge": (25, 33),
          "houses.eave_extra": (-3, 3), "houses.corner.eave_extra": (-3, 3), "cathedral.pinnacle_h": (3.0, 9.0), "cathedral.apse.wall_top": (21.1, 27.0)}   # >= aisle_roof_top + 2.5 so the ambulatory roof stays under the apse clerestory
GAIN = {k: 0.8 for k in BOUNDS}
def get(p, path):
    for k in path.split("."): p = p[k]
    return p
def put(p, path, v):
    ks = path.split(".")
    for k in ks[:-1]: p = p[k]
    p[ks[-1]] = round(float(v), 3)
def run(cmd, env=None, log=None):
    r = subprocess.run(cmd, shell=True, env={**os.environ, **(env or {})}, capture_output=True, text=True)
    if log: open(log, "w").write(r.stdout + r.stderr)
    return r
def evaluate(params, tag):
    d = os.path.join(WORK, tag); os.makedirs(d, exist_ok=True); pf = os.path.join(d, "params.json"); json.dump(params, open(pf, "w"), indent=1)
    r = run(f'{BL} -b -P "{ROOT}/build.py"', {"PARAMS": pf, "OUTDIR": d, "NO_EXPORT": "1"}, os.path.join(d, "build.log"))
    if "BUILD OK" not in r.stdout: raise SystemExit(f"build failed, see {d}/build.log")
    run(f'{BL} -b "{d}/building.blend" -P "{ROOT}/src/render_sil.py" -- "{d}/sil" {MPP}', log=os.path.join(d, "sil.log"))
    run(f'PARAMS="{pf}" python3 "{HERE}/compare.py" "{d}/sil" "{d}/cmp"', log=os.path.join(d, "cmp.log"))
    S = json.load(open(os.path.join(d, "cmp", "scores.json")))
    zerr = []
    for (v, u0, u1, path, stat) in ZONES:
        u = np.array(S[v]["u"]); sm = np.array([np.nan if x is None else x for x in S[v]["skyline_model"]]); sr = np.array([np.nan if x is None else x for x in S[v]["skyline_ref"]])
        sel = (u >= u0) & (u <= u1)
        a, b = np.nan_to_num(sm[sel]), np.nan_to_num(sr[sel])
        e = float(a.max() - b.max()) if stat == "max" else float((a - b).mean())
        zerr.append({"view": v, "u": [u0, u1], "param": path, "stat": stat, "err_m": round(e, 2)})
    J = np.mean([S[v]["iou"] for v in ("south", "north", "west", "east")] + [S["top"]["footprint_iou"]]) - 0.01*np.mean([S[v]["skyline_mae_m"] for v in ("south", "north", "west", "east")])
    for v in ("south", "north", "west", "east"): S[v] = {k: S[v][k] for k in ("iou", "skyline_mae_m", "skyline_rmse_m", "height_model_m", "height_ref_m")}
    return S, zerr, float(J), d
def table(S):
    rows = ["| view | IoU | skyline MAE (m) | skyline RMSE (m) | max height model / ref (m) |", "|---|---|---|---|---|"]
    for v in ("south", "north", "west", "east"):
        s = S[v]; rows.append(f"| {v} | {s['iou']:.3f} | {s['skyline_mae_m']:.2f} | {s['skyline_rmse_m']:.2f} | {s['height_model_m']:.1f} / {s['height_ref_m']:.1f} |")
    t = S["top"]; rows.append(f"| top (plan) | site {t['iou']:.3f} / building footprint {t['footprint_iou']:.3f} | outline dist {t['outline_dist_m']:.2f} | - | - |")
    return rows

P = json.load(open(os.path.join(ROOT, "params.json")))
if ROUNDS > 0 and not os.path.exists(os.path.join(ROOT, "params_initial.json")): shutil.copy(os.path.join(ROOT, "params.json"), os.path.join(ROOT, "params_initial.json"))
L = []
if not os.path.exists(LOG) or ROUNDS == 0:
    L += ["# compare_log.md - automatic silhouette comparison loop", "",
          "Scores: IoU of model vs reference silhouettes per orthographic view (reference panels aligned to metres, see params.md / compare/compare.py);",
          "skyline (top-edge) error = mean |z_model - z_ref| per column. Plan view: IoU of the site outline + IoU of building footprints read off the plan.",
          "Objective J = mean(4 elevation IoUs + footprint IoU) - 0.01 * mean skyline MAE. Zone errors are model minus reference (m).", ""]
S, Z, J, d = evaluate(P, "r0")
stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
L += [f"## Round 0 ({stamp}, baseline of current params.json)", ""] + table(S) + ["", f"J = {J:.4f}", ""]
L += ["Zone errors (largest first):", ""] + [f"- {z['view']} u[{z['u'][0]},{z['u'][1]}] -> `{z['param']}` ({z['stat']}): {z['err_m']:+.2f} m" for z in sorted(Z, key=lambda z: -abs(z["err_m"]))[:8]] + [""]
best = (copy.deepcopy(P), S, Z, J)
TABU = set()
for rnd in range(1, ROUNDS + 1):
    Pb, Sb, Zb, Jb = best
    agg = {}
    for z in Zb: agg.setdefault(z["param"], []).append(z["err_m"])
    cand = sorted(((k, float(np.mean(v))) for k, v in agg.items()), key=lambda kv: -abs(kv[1]))
    LOCK = Pb.get("compare_lock", [])   # design-intent params (visual fidelity) the optimiser must not touch
    cand = [(k, e) for k, e in cand if abs(e) > 0.3 and GAIN[k] > 0.05 and k not in TABU and not any(k == l or k.startswith(l + ".") for l in LOCK)][:3]
    TABU = set()
    if not cand: L += [f"## Round {rnd}", "", "All remaining zone errors <= 0.3 m (or their params exhausted) - converged, no change.", ""]; break
    L += [f"## Round {rnd}", "", f"Start J = {Jb:.4f}. The three params whose zones differ most are tried one at a time (new = old - gain x mean zone error);",
          "a trial is kept only if J improves, otherwise a 40% step is tried, otherwise the change is reverted, that param's gain is halved and it sits out the next round.", "",
          "| param | mean zone error (m) | old | trial | J trial | result |", "|---|---|---|---|---|---|"]
    acc_any = []
    for k, e in cand:
        old = get(best[0], k); lo, hi = BOUNDS[k]; kept = False
        for frac in (1.0, 0.4):
            new = round(min(hi, max(lo, old - frac*GAIN[k]*e)), 3)
            if abs(new - old) < 1e-3: continue
            Pn = copy.deepcopy(best[0]); put(Pn, k, new)
            Sn, Zn, Jn, d = evaluate(Pn, f"r{rnd}_{k.split('.')[-1]}_{int(frac*100)}")
            ok = Jn > best[3] + 1e-4
            L.append(f"| `{k}` | {e:+.2f} | {old} | {new} | {Jn:.4f} | {'**kept**' if ok else 'reverted'} |")
            print(f"round {rnd}: {k} {old}->{new} J {Jn:.4f} {'KEPT' if ok else 'rev'}", flush=True)
            if ok: best = (Pn, Sn, Zn, Jn); kept = True; acc_any.append(k); break
        if not kept: GAIN[k] *= 0.5; TABU.add(k)   # skip it next round so other zones get a turn
    L += ["", f"Scores after round {rnd} (best so far):", ""] + table(best[1]) + ["", f"J = {best[3]:.4f} (round start {Jb:.4f}); kept: {', '.join(acc_any) or 'none'}", ""]
    L += ["Zone errors after the round:", ""] + [f"- {z['view']} u[{z['u'][0]},{z['u'][1]}] -> `{z['param']}` ({z['stat']}): {z['err_m']:+.2f} m" for z in sorted(best[2], key=lambda z: -abs(z["err_m"]))[:8]] + [""]
Pf, Sf, Zf, Jf = best
if ROUNDS > 0:
    json.dump(Pf, open(os.path.join(ROOT, "params.json"), "w"), indent=1)
    L += ["## Result of this loop", "", "params.json updated with the best accepted round."] + [""] + table(Sf) + ["", f"J = {Jf:.4f}", ""]
open(LOG, "a" if (os.path.exists(LOG) and ROUNDS > 0) else "w").write("\n".join(L) + "\n")
print("LOOP DONE J=%.4f" % Jf, json.dumps({v: Sf[v]["iou"] for v in ("south", "north", "west", "east")}), "footprint", Sf["top"]["footprint_iou"])
