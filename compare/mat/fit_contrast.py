"""gap #8: update grade.json "_contrast" (per texture [k_low, k_high]) from mat_TAG.json so our neutral-render L* IQR matches the
reference IQR: k_low *= (ref/ours)^P, k_high *= (ref/ours)^(P/2) (P = argv[2], default 1), clamp 0.3..6. Only the four materials of the brief."""
import json, os, sys
H = os.path.dirname(os.path.abspath(__file__)); R = json.load(open(os.path.join(H, f"mat_{sys.argv[1]}.json")))["materials"]
MAP = {"brick": ["brick"], "cobble": ["cobble"]}   # stone: fixed [0.7, 0.85], its render spread is shadow-dominated (compare_log M8)
KH = {"brick": 1.3, "stair": 1.5}   # cap the high band (per-brick strobing / blown slabs at close range)
gp = os.path.join(H, "grade.json"); G = json.load(open(gp)); C = G.get("_contrast", {})
for m, texs in MAP.items():
    P = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0; v = R[m]; r = v["contrast_ref_IQR_L"]/max(v["contrast_ours_IQR_L"], 0.5)
    for t in texs:
        kl, kh = C.get(t, [1.0, 1.0]); C[t] = [round(min(8, max(0.3, kl*r**P)), 3), round(min(KH.get(t, 3), max(0.3, kh*r**(P/2))), 3)]
G["_contrast"] = C; json.dump(G, open(gp, "w"), indent=1); print(C)
