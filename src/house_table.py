"""Per-house table read off the drawings -> params.json["houses"]["list"] (+ houses_table.md).
Edit the TABLE below, then run:  python3 src/house_table.py   (run_all.sh does this before the build).

Sources (see houses_table.md for the per-field notes):
  top_plan     : number of houses per row (5 + 5), party-wall positions -> widths, chimney positions (rear/street side,
                 near which party wall), cross-gable valleys on the street side, roof holes.
  left_west    : REAR faces of the west row (eaves heights relative to each other, ridge rise -> pitch, rear dormers,
                 window counts, timber pattern, ground-floor material); the west gable of the NW corner house.
  right_east   : rear faces of the east row (same), the east gable of the NE corner house.
  front_south  : south gable ends of W4 / E4 (W4 plaster with brick patches; E4 brick with a half-timbered gable,
                 two round arches on the ground floor), gable steepness (~50 deg).
  back_north   : corner houses NW / NE (2 storeys, half-timber on both floors, dormer + roof hole, rubble end walls).
  isometric    : street faces: big street cross gables, jetties (upper floors overhang), pentice roofs over doors, setbacks.
Elevations and plan disagree on house count (west elevation shows 4 row houses, east 5, plan 5 + 5): the plan wins for
count/width; the elevation houses were mapped in order (north -> south) and their relative eave/ridge/pitch carried over.
Roof pitch: the ridge rise above the eave is consistent between the views (front ~4.5 m, rear elevations 2.8-5.1 m), the house
depth is not (plan 11 m vs ~7.8 m implied by the front elevation), so pitch = atan(measured rise / half the plan depth).
Seeded randomness only for: timber brace placement, plaster-patch layout, roof hole pattern (seed per house)."""
import json, os
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# index runs north -> south in each row (v = 0 at the north party wall). w in plan px (x 0.11 m/px), rescaled to the row length.
# fields: id, w_px, eave_dz (m, relative), pitch (deg), gf, upper, timber (pattern or None), jetty (m per storey), setback (m),
#         cross [(v_frac, half_width_m)], dormers (street, v_frac), rear_dormers, chimneys [(v_frac, u_frac of depth)],
#         win (per storey, street side), win_w, rear_win, door (v_frac), door_kind, gf_arch (arched GF windows), shop (wide GF window),
#         holes (roof hole fraction), patches (brick patches on plaster), pentice, src,
#         tone = lime-plaster tone A off-white / B grey / C warm beige (refs show all three; assignment by eye from the iso/elevations)
TABLE = [
 # ---------------- west row (street on its east side) ----------------
 dict(id="W0", tone="A", w_px=115, eave_dz=0.0, pitch=33, gf="plaster", upper="plaster", timber="grid", jetty=0.30, setback=0.0,
      cross=[(0.56, 3.2)], dormers=[], rear_dormers=[0.45], chimneys=[(0.05, 0.80), (0.30, 0.86)], win=[3, 4, 4], win_w=0.95, rear_win=4,
      door=0.35, door_kind="flat", gf_arch=False, shop=True, holes=0.12, patches=0, pentice=True,
      src="plan 115 px; west elev. house 1: 4 windows/storey, half-timber on all storeys, damaged rear dormer, shop window; 2 chimneys at the N end (plan)"),
 dict(id="W1", tone="C", w_px=104, eave_dz=-0.8, pitch=42, gf="brick", upper="plaster", timber="braced", jetty=0.0, setback=0.35,
      cross=[(0.50, 4.5)], dormers=[], rear_dormers=[0.5], chimneys=[(0.93, 0.85)], win=[2, 3, 3], win_w=0.9, rear_win=3,
      door=0.45, door_kind="round", gf_arch=False, shop=False, holes=0.15, patches=0, pentice=False,
      src="plan 104 px; west elev. house 2: eave ~0.8 m lower, highest ridge rise (5.1 m), 3 windows, round-arched door, chimney at S end; iso: big street gable"),
 dict(id="W2", tone="B", w_px=92, eave_dz=0.2, pitch=37, gf="stone", upper="plaster", timber="x", jetty=0.45, setback=0.0,
      cross=[(0.50, 3.8)], dormers=[], rear_dormers=[0.3, 0.7], chimneys=[(0.08, 0.82)], win=[2, 3, 3], win_w=0.9, rear_win=3,
      door=0.5, door_kind="round", gf_arch=False, shop=False, holes=0.10, patches=0, pentice=True,
      src="plan 92 px, big chimney at the N party wall; west elev. house 3: X-braced half-timber, 2 rear dormers; iso: deep jetty"),
 dict(id="W3", tone="A", w_px=108, eave_dz=-0.3, pitch=36, gf="brick", upper="plaster", timber="grid", jetty=0.30, setback=0.2,
      cross=[], dormers=[0.30, 0.72], rear_dormers=[], chimneys=[(0.12, 0.75)], win=[3, 4, 4], win_w=0.95, rear_win=4,
      door=0.43, door_kind="flat", gf_arch=False, shop=False, holes=0.22, patches=4, pentice=False,
      src="plan 108 px, large roof hole; west elev. house 4 (hole with rafters): brick-patched ground floor, 4 windows; no street gable -> 2 dormers"),
 dict(id="W4", tone="A", w_px=150, eave_dz=0.3, pitch=40, gf="plaster", upper="plaster", timber=None, jetty=0.0, setback=0.0,
      cross=[(0.30, 3.0)], dormers=[0.70], rear_dormers=[0.4], chimneys=[(0.08, 0.85), (0.78, 0.22)], win=[3, 4, 4], win_w=1.0, rear_win=4,
      door=0.55, door_kind="round", gf_arch=False, shop=False, holes=0.18, patches=14, pentice=False,
      src="plan 150 px incl. the south gable; front elev.: south gable plaster with large brick patches, 3 storeys + attic (gable reads ~50 deg at the front elevation's narrower depth = 40 deg on the 11 m plan depth)"),
 # ---------------- east row (street on its west side) ----------------
 dict(id="E0", tone="C", w_px=119, eave_dz=0.0, pitch=31, gf="brick", upper="plaster", timber="grid", jetty=0.30, setback=0.0,
      cross=[(0.50, 3.4)], dormers=[], rear_dormers=[0.5], chimneys=[(0.05, 0.85)], win=[3, 3, 3], win_w=0.95, rear_win=3,
      door=0.4, door_kind="flat", gf_arch=False, shop=False, holes=0.12, patches=0, pentice=True,
      src="plan 119 px, chimney at the N end (rear); east elev. house 5 (north): half-timber, 3 windows, dormer"),
 dict(id="E1", tone="B", w_px=96, eave_dz=-0.5, pitch=30, gf="stone", upper="plaster", timber="braced", jetty=0.45, setback=0.3,
      cross=[], dormers=[0.5], rear_dormers=[0.5], chimneys=[(0.10, 0.90)], win=[2, 3, 3], win_w=0.85, rear_win=3,
      door=0.5, door_kind="round", gf_arch=False, shop=False, holes=0.20, patches=0, pentice=False,
      src="plan 96 px; east elev. house 4: big roof hole, brick infill, lower eave"),
 dict(id="E2", tone="A", w_px=92, eave_dz=0.3, pitch=34, gf="brick", upper="plaster", timber="x", jetty=0.30, setback=0.0,
      cross=[(0.45, 4.2)], dormers=[], rear_dormers=[0.5], chimneys=[(0.55, 0.85)], win=[2, 2, 3], win_w=0.9, rear_win=2,
      door=0.6, door_kind="round", gf_arch=True, shop=False, holes=0.10, patches=0, pentice=True,
      src="plan 92 px; east elev. house 3: X-braced half-timber, arched ground-floor windows, tallest ridge"),
 dict(id="E3", tone="A", w_px=97, eave_dz=0.0, pitch=29, gf="brick", upper="brick", timber="grid", jetty=0.0, setback=0.15,
      cross=[], dormers=[0.5], rear_dormers=[], chimneys=[(0.10, 0.20), (0.15, 0.85)], win=[3, 3, 3], win_w=0.95, rear_win=3,
      door=0.45, door_kind="flat", gf_arch=False, shop=True, holes=0.22, patches=0, pentice=False,
      src="plan 97 px, 2 chimneys at the N party wall (street + rear side); east elev. house 2: brick infill, rear roof hole"),
 dict(id="E4", tone="A", w_px=165, eave_dz=0.2, pitch=35, gf="brick", upper="brick", timber=None, jetty=0.0, setback=0.0,
      cross=[(0.30, 3.0)], dormers=[0.65], rear_dormers=[0.5], chimneys=[(0.08, 0.85), (0.50, 0.85)], win=[3, 4, 4], win_w=1.0, rear_win=4,
      door=0.55, door_kind="round", gf_arch=True, shop=False, holes=0.15, patches=0, pentice=False, gable_timber=True,
      src="plan 165 px incl. south gable, 2 rear chimneys; front elev.: brick lower storeys, half-timbered gable, round-arched ground floor"),
]
CORNER = [
 dict(id="NW", tone="A", eave_dz=0.0, pitch=40, gf="plaster", upper="plaster", timber="braced", jetty=0.30, setback=0.0,
      cross=[], dormers=[0.62], rear_dormers=[0.55], chimneys=[(0.08, 0.80), (0.88, 0.80), (0.28, 0.40)], win=[3, 4], win_w=0.95, rear_win=4,
      door=0.45, door_kind="flat", gf_arch=False, shop=False, holes=0.18, patches=8, pentice=False, rubble_end="v0",
      src="plan: 3 chimneys, street dormer; north elev.: 2 storeys half-timber, dormer + hole, rubble W end; west elev.: plaster gable with brick patches"),
 dict(id="NE", tone="B", eave_dz=0.0, pitch=40, gf="plaster", upper="plaster", timber="grid", jetty=0.30, setback=0.0,
      cross=[], dormers=[0.4], rear_dormers=[0.45], chimneys=[(0.12, 0.80), (0.82, 0.75)], win=[3, 4], win_w=0.95, rear_win=4,
      door=0.45, door_kind="flat", gf_arch=False, shop=False, holes=0.2, patches=8, pentice=False, rubble_end="v1",
      src="plan: chimneys at both ends; north elev.: 2 storeys half-timber, dormer + hole, rubble E end; east elev.: plaster gable with brick patches"),
]
P = json.load(open(os.path.join(R, "params.json"))); HS = P["houses"]
L = HS["row_y"][1] - HS["row_y"][0]; out = []
for row in ("W", "E"):
    hs = [h for h in TABLE if h["id"][0] == row]; tot = sum(h["w_px"] for h in hs)
    for h in hs:
        h = dict(h); h["w"] = round(L*h["w_px"]/tot, 3); h["row"] = row; h["floors"] = HS["floors_row"]; out.append(h)
for h in CORNER:
    h = dict(h); h["row"] = "N"; h["floors"] = HS["corner"]["floors"]; out.append(h)
for h in out: h["cross"] = [list(c) for c in h["cross"]]; h["chimneys"] = [list(c) for c in h["chimneys"]]
HS["list"] = out
HS["_list_doc"] = "per-house look + shell parameters, generated by src/house_table.py from the hand-read table (do not edit here)"
json.dump(P, open(os.path.join(R, "params.json"), "w"), indent=1)
md = ["# houses_table.md - per-house parameters (generated by src/house_table.py)", "", __doc__.strip(), "",
      "| id | tone | w (m) | storeys | eave dz | pitch | GF / upper | timber | jetty | setback | street gables | dormers st/rear | chimneys | windows | holes | patches | source |",
      "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
for h in out:
    md.append(f"| {h['id']} | {h.get('tone', 'A')} | {h.get('w', '-')} | {h['floors']} | {h['eave_dz']:+.1f} | {h['pitch']} | {h['gf']} / {h['upper']}{' + timber gable' if h.get('gable_timber') else ''} | {h['timber'] or '-'} | "
              f"{h['jetty']} | {h['setback']} | {len(h['cross'])} | {len(h['dormers'])}/{len(h['rear_dormers'])} | {len(h['chimneys'])} | {'-'.join(map(str, h['win']))} | {h['holes']} | {h['patches']} | {h['src']} |")
open(os.path.join(R, "houses_table.md"), "w").write("\n".join(md) + "\n"); print("houses:", len(out))
