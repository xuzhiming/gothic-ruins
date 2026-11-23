# t22 local asset-only handoff — NOT a deployed website
Only merge the asset/source changes deliberately. Do not overwrite cloud T-3 web runtime with local web files. Production 8bca20e was not browser-verified here.

## Asset rebuild
Environment: Blender 5.3.0; Python numpy/Pillow/scipy; gltf-transform 4.5.1 (+ meshoptimizer), installed separately (tools/node_modules intentionally not bundled).
```
mkdir -p check tex
python3 src/make_textures.py
blender -b -P build.py
gltf-transform optimize building.glb web/building_opt.glb --compress meshopt --texture-compress webp --simplify false --join-named false --flatten false --instance false
blender -b -P check/test_aperture_geometry.py
blender -b building.blend -P check/test_glass_assets.py -- --report check/glass_report.json
python3 check/test_m13_faces.py
blender -b building.blend -P check/circulation_check.py
```
Grade JSON and especially compare/wall/wall_gain.json are exact required calibration dependencies; do not omit them. Generated tex are not included, but make_textures regenerates all of them without the private reference images.
Raw 37MB GLB/Blend/original references/crops/backups/temp images/credentials are NOT bundled. The optimized self-contained GLB is included.
Original run_all.sh additionally needs the local compare scripts and unpublished reference set; do not claim a full reference run from this intentionally reference-free handoff. Latest actual local stages1–6 and8 are evidenced; stage7/browser/WASD is NOT RUN. Prior old walk result is deliberately excluded.

## Full 365-slot (360 real +5 decorative) audit
Precomputed checkable per-window rays/materials/GLB data: window-audit/windows_all.json.gz; CSV and per-building/floor/orientation summary alongside it. Four solid spire ornaments are separate.
To rerun the inventory, create an isolated trace directory containing the exact build.py, params.json, ruin_streams.json, src/*.py, empty check/ and compare/wall/, and a tex symlink to generated tex. Run trace_all_windows.py there (NO_EXPORT); never overwrite the final scene for tracing. Then run offline decoder and actual saved-Blend audit:
```
# scripts are documented in their headers; the existing tools/gltf/node_modules location is expected by decoder
node check/decode_window_glb.cjs ROOT REPORTDIR/glb_decoded.json
blender -b ROOT/building.blend -P check/audit_all_windows.py -- INVENTORY_JSON REPORTDIR
python3 check/test_all_windows.py REPORTDIR/windows_full.json
```
Do not confuse transparent Glass with clear sightlines through original common walls/chimneys/rubble. Full details and decision exceptions: docs/window-audit-t22.md.
Web material matching MUST be exact material.name === 'Glass', never startsWith('Glass') (Glass_blind stays opaque). See docs/glass-web-contract.md. Keep glass collision; depthWrite=false/castShadow=false and production sorting/shadow/inside-outside views remain cloud verification items.
