"""Score a parameter variant without touching params.json:  python3 compare/experiment.py TAG 'python statements on P' [MPP]
builds into compare/work/exp_TAG, renders metric silhouettes, runs compare.py + diag_side.py, prints all view scores."""
import json, os, subprocess, sys, copy
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); BL = os.environ.get("BLENDER", "blender")
tag, code = sys.argv[1], sys.argv[2]; mpp = sys.argv[3] if len(sys.argv) > 3 else "0.1"
P = json.load(open(os.path.join(ROOT, "params.json"))); C = P["cathedral"]; H = P["houses"]; exec(code)
d = os.path.join(HERE, "work", "exp_" + tag); os.makedirs(d, exist_ok=True); pf = os.path.join(d, "params.json"); json.dump(P, open(pf, "w"), indent=1)
sh = lambda c, env={}: subprocess.run(c, shell=True, capture_output=True, text=True, env={**os.environ, **env})
r = sh(f'{BL} -b -P "{ROOT}/build.py"', {"PARAMS": pf, "OUTDIR": d, "NO_EXPORT": "1"})
if "BUILD OK" not in r.stdout: print(r.stdout[-3000:], r.stderr[-2000:]); sys.exit(1)
sh(f'{BL} -b "{d}/building.blend" -P "{ROOT}/src/render_sil.py" -- "{d}/sil" {mpp} --shaded')
r = sh(f'python3 "{HERE}/compare.py" "{d}/sil" "{d}/cmp" --sbs', {"PARAMS": pf}); print(tag, r.stdout.strip().splitlines()[-1])
r = sh(f'python3 "{HERE}/diag_side.py" "{d}/sil" "{d}/diag" {tag}', {"PARAMS": pf}); print("\n".join(l for l in r.stdout.splitlines() if "IoU" in l))
