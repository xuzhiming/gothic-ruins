"""Writes params.md from params.json: every parameter, its value and where it comes from.
M = measured off a drawing panel (px x mpp), I = inferred / assumed (convention, hidden in drawings, or needed for circulation), T = tuned by compare_loop."""
import json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = json.load(open(os.path.join(ROOT, "params.json"))); P0p = os.path.join(ROOT, "params_initial.json")
P0 = json.load(open(P0p)) if os.path.exists(P0p) else P
SRC = {  # prefix -> (tag, note); longest prefix wins
 "ref_scale": ("I", "alignment of the drawing panels to metres, fixed (see Scale below)"),
 "site.main": ("M", "plan: plinth/plaza outer edge, px bbox x 0.11 m/px"), "site.north_band": ("M", "plan: narrower band behind the choir"),
 "site.tongue": ("M", "plan: plaza tongue above the upper stair"), "site.terrace": ("M", "plan: intermediate terrace"), "site.strip": ("M", "plan: lower landing strip"),
 "site.approach": ("I", "forecourt below the drawings' bottom edge (start of the route)"),
 "site.plaza_z": ("M", "south elevation: plinth top above ground line (2 x 13 risers ~ 0.16 m)"), "site.terrace_z": ("M", "south elevation: terrace level"),
 "site.parapet_h": ("I", "typical"), "site.balustrade_h": ("I", "typical guard height"), "site.post": ("M", "iso: stair cheek posts, ~1 m square"), "site.plinth_course": ("I", "base course on house fronts"),
 "stairs_south": ("M", "plan: stair widths/lengths; riser count read from the south elevation (13 + 13)"),
 "bollards": ("M", "plan: arc of bollards with chains around the plaza (centre, radius, end), pitch counted on the iso view"),
 "cathedral.podium_h": ("M", "south elevation: cathedral floor above plaza"), "cathedral.steps": ("M", "plan/iso: 15 steps up to the portal"),
 "cathedral.nave_hw": ("M", "plan: nave width 11 m"), "cathedral.aisle_hw": ("M", "plan: outer aisle walls 26 m"), "cathedral.y_front": ("M", "plan: facade line"), "cathedral.y_back": ("M", "plan: start of choir"),
 "cathedral.bays": ("M", "plan/side elevation: 5 nave bays"), "cathedral.wall_t": ("I", "masonry thickness"),
 "cathedral.aisle_wall_top": ("M", "side elevations"), "cathedral.nave_wall_top": ("M", "side elevations (clerestory top)"), "cathedral.nave_ridge": ("M", "side elevations"),
 "cathedral.aisle_roof_top": ("M", "front elevation"), "cathedral.facade_apex": ("M", "front elevation: gable apex"), "cathedral.facade_finial": ("I", ""),
 "cathedral.rose": ("M", "front elevation: rose window centre & radius"), "cathedral.portal": ("M", "front elevation: portal opening & wimperg top"),
 "cathedral.arcade_open_h": ("I", "arcade height inside (not drawn)"), "cathedral.pier_w": ("I", ""), "cathedral.buttress": ("M", "plan/front elevation"),
 "cathedral.pinnacle_h": ("T", "front elevation, tuned by the loop"), "cathedral.flyer": ("M", "side elevations: flying-buttress springing heights"),
 "cathedral.tower_sw": ("M", "plan footprint; front elevation: tower top, spire tip 40.4 + cross 1.1 = 41.5 m height anchor"),
 "cathedral.tower_se": ("M", "plan footprint; front elevation: lower ruined SE tower with spirelet"), "cathedral.choir_y": ("M", "plan"),
 "cathedral.apse.cy": ("M", "DELIBERATE COMPROMISE (gap #6, locked): plan apse disc centre ~43.5 / tip 50.3, side elevations put the apse block ~3-4 m further south; 38.0 = 3 m south of the previous 41.0 (plan value pulled 2 m south for the plinth). West/east IoU +0.020 (0.721/0.728 -> 0.741/0.748), south/north/plan site/footprint unchanged; plan apse tip left ~3 m uncovered (footprint panel). See compare_log.md M5/M6"), "cathedral.apse.r": ("M", "plan: apse / ambulatory / buttress-pier radii"),
 "cathedral.apse.sides": ("I", "polygonal chevet, 12-gon (half used)"), "cathedral.apse.wall_top": ("T", "side elevations, tuned by the loop (lower bound keeps the ambulatory roof under the clerestory)"),
 "cathedral.apse": ("M", "side elevations"), "cathedral.roof_holes": ("M", "iso: nave roof partly exposed rafters on the east slope; hole pattern seeded"),
 "cathedral.gate": ("M", "plan/iso: iron fences & gates between the cathedral and the house rows"),
 "houses.storey_h": ("M", "front/side elevations: storey 31.7 / 30.0 / 35.0 px -> 3.2 m (the plan-scale cross-check)"),
 "houses.slab_t": ("I", ""), "houses.wall_t": ("I", ""), "houses.part_t": ("I", ""), "houses.row": ("M", "plan: two house rows on the long sides"),
 "houses.n_row": ("I", "superseded by houses.list (5 houses per row from the plan)"), "houses.floors_row": ("M", "elevations: 3 storeys"), "houses.roof_pitch_deg": ("M", "front elevation gable angle"),
 "houses.eave_var": ("M", "side elevations: eave steps between neighbours"), "houses.overhang": ("I", ""), "houses.corner": ("M", "plan/north elevation: corner houses behind the choir, 2 storeys"),
 "houses.door": ("I", "street doors (interiors not drawn)"), "houses.stair": ("I", "interior: dog-leg stair, 20 risers x 160 mm, tread 270 mm (laid out per plan of each house)"),
 "houses.partition": ("I", "interior: front room / back room partition + door"), "houses.chimney": ("M", "iso/elevations"), "houses.roof_hole": ("M", "iso: damaged roofs, seeded"),
 "houses.eave_extra": ("T", "loop parameter (row houses), all trials reverted"), "houses.cross_gable_frac": ("M", "iso: share of houses with a cross gable / dormer"),
 "walk": ("I", "walk-mode eye height and capsule radius"),
 "cathedral.nave_wall_top": ("M", "side/front elevations: clerestory windows ~18.6-22.8 m, nave eave ~24 m (gap #1 fix; locked)"),
 "cathedral.pinnacle_h": ("M", "iso/elevations: tall slender buttress pinnacles (gap #1 fix, was 3.94 tuned; locked)"),
 "cathedral.apse.wall_top": ("M", "continuous clerestory round the apse = nave eave (gap #1 fix; locked)"),
 "cathedral.clerestory_pinnacles": ("M", "side elevations/iso: pinnacle at every bay line + apse vertex, tops ~31 m (locked)"),
 "cathedral.facade_pinnacle_top": ("M", "front elevation: gable-flank pinnacles ~31-32 m (locked)"),
 "cathedral.pinnacle_spikes": ("I", "corner pinnaclets + crocket bands on every pinnacle (detail level)"),
 "cathedral.aisle_front_lancet": ("M", "front elevation: tall traceried lancets in the aisle fronts (locked)"),
 "cathedral.tower_sw": ("M", "plan footprint; front elevation: lower stage to 20.7, set-back belfry (2 tiers of paired lancets) to 31, corner pinnacles 33.2, slender spire to 40.4 + cross 1.1 = 41.5 m anchor (locked)"),
 "cathedral.tower_se": ("M", "plan footprint; front elevation: shorter belfry to 23.5 + octagonal spirelet 28.5 (locked)"),
 "compare_lock": ("I", "params the compare loop may not change (design intent / visual fidelity)"),
 # ---- gap #4 ruin / decay (whole section locked; S = seeded where the drawings give no information)
 "ruin.enabled": ("I", "switch: false rebuilds the intact model"), "ruin.seed": ("I", "seed of the ruin rng streams (separate from the older layouts)"),
 "ruin.moss_tops": ("M", "iso: green-grey growth on ledges, wall tops, treads -> up-facing stone/rubble faces use the *_moss texture"),
 "ruin.pinnacles": ("I", "S: share of snapped / chipped pinnacles (the drawings show them mostly whole; kept to ~1 in 4)"),
 "ruin.glass": ("M", "iso/elevations: most cathedral and many house windows read as dark empty openings; which ones = S"),
 "ruin.rose": ("I", "S: partial rose window (some glass wedges, spokes, inner-ring pieces lost) - rose drawn mostly intact"),
 "ruin.roof.nave_west_exposed": ("I", "S/plausible: a second, smaller collapse on the west slope over bay 5 (keeps the E/W silhouettes: the east slope is intact there)"),
 "ruin.roof.aisle_hole_frac": ("M", "iso: several holes in the aisle lean-to roofs"), "ruin.roof.ragged_cells": ("I", "ragged edge of collapsed areas (+-1 tile cell per row)"),
 "ruin.roof": ("I", "S: broken / missing rafters & purlins, slipped slates under the holes (iso shows bare rafters; the breakage pattern is seeded)"),
 "ruin.houses": ("M", "iso: big holes / sagging roofs on some houses; which houses + extents chosen to match, positions S"),
 "ruin.chimney_collapse_frac": ("I", "S: collapsed chimney stacks"), "ruin.brace_missing": ("I", "S: broken half-timber braces"),
 "ruin.balustrade": ("I", "S: crumbling balustrades / parapets (rail pieces fallen, balusters lost, post caps knocked off)"),
 "ruin.cornice_gap_p": ("I", "S: fallen eaves-cornice stones on the aisle walls"),
 "ruin.weather": ("M", "iso: dark soot / water streaks under sills and wall tops, grime near the ground, cracked plaster; decal sizes + densities I"),
 "ruin.rubble": ("I", "rubble heaps inside the nave/aisles and at wall bases + fallen rafters (not legible in the drawings); colliding, placed only where clear_spot() passes"),
 "ruin.debris": ("I", "counts of small decor debris pieces (non-colliding)"),
 "ruin.keepout_paths": ("I", "walk-test corridors that colliding rubble must keep clear of (in addition to every door/stair/space/link from spaces.json)"),
}
def src(path):
    best = ("I", ""); bl = -1
    for k, v in SRC.items():
        if (path == k or path.startswith(k + ".") or path.startswith(k + "_") or path.startswith(k)) and len(k) > bl: best, bl = v, len(k)
    return best
def get(p, path):
    for k in path.split("."): p = p[k]
    return p
rows = []
def walk(d, pre=""):
    for k, v in d.items():
        if k.startswith("_"): continue
        path = pre + k
        if path == "houses.list": rows.append(f"| `houses.list` | {len(v)} per-house entries | M | see houses_table.md (generated by src/house_table.py; locked) |"); continue
        if isinstance(v, dict): walk(v, path + ".")
        else:
            tag, note = src(path)
            try: v0 = get(P0, path)
            except Exception: v0 = v
            ch = "" if v0 == v else f" (was {v0})"
            rows.append(f"| `{path}` | {json.dumps(v)}{ch} | {tag} | {note} |")
walk(P)
L = ["# params.md - parameter table (generated by src/params_md.py from params.json)", "",
 "All geometry in `build.py` is generated from `params.json`. Units: metres. Axes: +X east, +Y north (towards the choir), +Z up;",
 "origin = centre of the plan panel's site bbox, z = 0 = ground line under the plinth.", "",
 "## Scale (the drawings carry no dimension lines)", "",
 "- **Plan**: isotropic 0.11 m/px about px (345, 480.5). Derived from the house storey height: 3.2 m storey (typical) <-> 31.7 px in the front",
 "  elevation, and the plan house depth (100 px = 11 m) matches the front-elevation house width read at the same storey scale.",
 "  Result: site 62.7 m x 102 m (plinth), cathedral 26 m wide x ~58 m long incl. chevet, spire 41.5 m.",
 "- **Elevations**: each panel is aligned with two anchors - horizontal = site extent from the plan (62.7 m for south/north, 102 m for west/east),",
 "  vertical = ground line (bottom of the silhouette) and the spire-cross tip = 41.5 m (top). These anchors are fixed in `ref_scale` and never",
 "  tuned, so the compare loop cannot move its own target.",
 "- Cross-check: with the two-anchor vertical scale (41.5 m over the panel height), the house storey reads 3.0 m (south, 31.7 px x 0.0945),",
 "  3.15 m (west, 30 px x 0.105) and 3.5 m (north, 35 px x 0.0995) - consistent with the 3.2 m storey within about +-9%.",
 "- Known inconsistency: the side elevations draw the cathedral ~25 m longer (relative to the site) than the plan does, and the front and",
 "  rear elevations disagree on the spire's lateral position. The plan is used as authority for horizontal layout; the elevations for heights.", "",
 "Source tags: **M** measured off a drawing panel, **I** inferred/assumed (not drawn, convention, or needed for the interiors/circulation),",
 "**T** tuned by `compare/compare_loop.py` (value before tuning in brackets; see compare_log.md).", "",
 "## Ruin (gap #4)", "",
 "`ruin` drives all decay procedurally (build.py + src/geom.py): snapped/chipped pinnacles, lost panes and tracery, partial rose, collapsed",
 "roof areas with broken rafters/purlins and slipped slates, sagging and collapsed house roofs, collapsed chimneys, broken braces,",
 "crumbling balustrades and cornices, rubble heaps + fallen rafters (colliding, only where `clear_spot()` keeps every door ray corridor,",
 "stair flight, space probe, outdoor link and walk corridor free), small debris + alpha decals (soot streaks, ground grime, cracks,",
 "fallen plaster with lath) as role `decor` = never collides (viewer + checker). Moss: up-facing stone/rubble faces get the `*_moss`",
 "textures. All ruin randomness uses its own seeded streams.", "",
 "Per-element streams (gap #6): every element (nave walls, ambulatory, each cathedral roof slope incl. its rafters / loose slates, towers,",
 "interior, gates, each house, each rubble group) starts at a named pin. `ruin_streams.json` stores the stream states recorded at those pins",
 "in the approved build (`DUMP_STREAMS=1 blender -b -P build.py` re-records them), so changing one element no longer re-rolls the others;",
 "pins missing from the file are seeded from the element name. The nave roof slopes use fixed 1.3 m tile columns from the facade end, so",
 "shortening the nave keeps the hole pattern of the remaining columns. Hole maps of the keyed slopes are logged in ruin_log.json.", "",
 "| parameter | value | src | note |", "|---|---|---|---|"] + rows
open(os.path.join(ROOT, "params.md"), "w").write("\n".join(L) + "\n"); print("params.md:", len(rows), "rows")
