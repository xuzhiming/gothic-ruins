"""Update compare/mat/grade.json from a material round: per texture, linear-light per-channel gain *= (ref / ours)^0.85 (damped),
using the medians of mat_TAG.json. Run after iterate.sh TAG; repeat until dE stops improving."""
import json, os, sys, numpy as np
H = os.path.dirname(os.path.abspath(__file__)); R = json.load(open(os.path.join(H, f"mat_{sys.argv[1]}.json")))["materials"]
MAP = {"stone_cathedral": ["stone", "stone_moss"], "slate": ["slate"], "plaster": ["plaster", "plaster_b", "plaster_c"], "brick": ["brick"],
       "chimney": ["brick_red"], "timber": ["timber"], "stone_plinth": ["rubble", "rubble_moss"], "plinth_rock": ["soil"], "cobble": ["cobble"],
       "stair": ["stair", "stair_riser", "stair_side"], "iron": ["iron"]}
gp = os.path.join(H, "grade.json"); G = json.load(open(gp)) if os.path.exists(gp) else {}
lin = lambda v: (np.array(v, float)/255.0)**2.2
for m, texs in MAP.items():
    v = R.get(m)
    if not v or not v["ours"]: continue
    f = np.clip((lin(v["ref"]["rgb"])/np.maximum(lin(v["ours"]["rgb"]), 1e-4))**0.85, 0.5, 2.0)
    for t in texs: G[t] = [round(float(a*b), 4) for a, b in zip(G.get(t, [1, 1, 1]), f)]
G["_doc"] = "per-texture linear-light RGB gains fitted against the reference colour samples (compare/mat/fit_grade.py); applied by make_textures.save"
json.dump(G, open(gp, "w"), indent=1); print({k: v for k, v in G.items() if not k.startswith("_")})
