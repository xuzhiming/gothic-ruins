# Transparent glass: local validation report

## Status and scope
Implemented approved Scheme A in /workspace/gothic only. Full M13 snapshot: /workspace/gothic-M13-before-glass-20261123-0134. No edits to web/main.js or web/index.html; no access to /workspace/gothic-repo; no commit, push or deployment. No furniture, lamps or room-layout changes.

## Material / web handoff
Exact transparent material name: `Glass`. `alphaMode=BLEND`, opacity .24, metallic 0, roughness .09, IOR 1.5 (glTF default, omitted), transmission 0, doubleSided=true. Pale grey-green `glass_clear.png` with subtle dirt. Original Glass geometry / UVs unchanged, including original slab thickness; "thin" means the alpha approximation, not newly modeled physically refracting panes. It is not a transmission/refraction simulation.

Exact opaque material name: `Glass_blind`; retains original dark glass image and original shader appearance, for blind lancets / tympanum only. These walls remain solid. `Glass_glass` retains extras role=glass and is still colliding. See docs/glass-web-contract.md for runtime suggestions.

## Openings and visibility
38 real openings: 1 rose, 18 attic/cross-gable, 19 dormers. Dormer solid boxes replaced by shells, locally clipping the underlying roof inside the dormer footprint to connect to the existing attic. All 38 structural-wall apertures have clear sampled wall rays. 37 have unobstructed sight samples; E4 rear dormer House_E4_dormer_29 is blocked by its original overlapping chimney (fingerprint unchanged), not by an uncut wall. Keep that limitation explicit: no chimney relocation was authorized. Original structural timber cross-beams can cross some window center rays; quadrant rays are logged, not hidden.

Evidence: check/window_apertures.json, check/glass_report.json (centers/normals/probe hits and deep attic rays), glass-evidence/glass_collision_rays.json (37 intact rectangular panes hit by glass-only collision rays), glass-evidence/protected_identity.json. All original pane and blind geometry/UVs, WinFrame and tracery match M13 exactly. All 40 original textures, E4 main-storey M13 geometry/materials/UVs, parameters including 15 mm lime layer, spaces and ruin layout remain unchanged.

## Tests
- TDD: M13 asset test fails for opaque shader and blocked rose/attic; new tests subsequently pass. Geometry unit suite 3/3 including the roof UV-loop regression. M13 selectors 3/3.
- Full serial ./run_all.sh: logs/run_all_glass.log ends GLASS_FULL_EXIT=0. Both blocked-door and bad-riser negatives caught; 86 spaces reachable.
- WASD: PASS, 87 waypoints, 1227 samples, 286.7 m, no penetrations/stuck/page errors; 4 doors minimum openness 1.0. This is load/collision regression, NOT browser glass visual acceptance (test mode does not render).
- Raw and optimized GLB self-describing alpha materials audited by check/audit_glass_glb.py; logs/glass_glb.json and glass-evidence/glb_final.json.

## Metric changes (not concealed)
IoU M13 -> glass: south .8078 -> .8076; north .8119 -> .8116; west .7404 unchanged; east .7477 unchanged; top .9420 unchanged. Building footprint .8514 -> .8521. Outline distance 1.186 m unchanged. Skyline MAE 4.580 / 4.215 / 6.316 / 6.168 m unchanged; entire skyline sample arrays identical. At compare.py alpha threshold >40, south/north/foot lose 40/48/270 mask pixels, west/east/top unchanged. Openings change internal silhouette pixels; no claim of zero mask changes is made.

## Outputs
- building.blend (final saved asset)
- building.glb: 37,780,052 bytes (local raw asset, not for Pages)
- web/building_opt.glb: 4,917,564 bytes; 168,099 triangles (M13:161,143; +6,956 from aperture/reveal/shell triangulation and roof clipping). SHA256 b5d06c807228c60a0a748ade3861ea2fc6b07730ac4a771292023565bb936f42.

## Real Cycles comparisons
All are original 720x540, 24-sample Cycles renders from the frozen before/after .blend files, same cameras and warm world/sun, no image manipulation or added interior lights. All before/after images were opened with Read and inspected. Directory glass-evidence/: before_/after_ pairs for main_out, main_out_down, main_in, attic_out, attic_in, dormer_out, dormer_in, rose_out, rose_in, church_side_out, rear_blocked_out (22 images). Main-storey exterior view correctly sees the original nearby partition/floor rather than an invented furnished room; inward-to-outward panes show the courtyard sharply. rear_blocked_out truthfully shows the retained chimney. Full pipeline refreshed renders/beauty_iso.png only; docs/renders HD gallery not regenerated.

## Remaining / no end-to-end claim
Web runtime still needs Glass-only transparent/depthWrite/shadow/ordering integration by T-3. GLB loader supplies BLEND/opacity automatically, but current main.js still casts opaque glass shadows and does not disable glass depth writing. Transparent intersecting panes/Decal ordering, real browser interior/exterior near/far visuals and shadow acceptance remain pending. No deploy/publish was attempted.
