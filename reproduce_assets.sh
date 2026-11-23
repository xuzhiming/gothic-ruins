#!/usr/bin/env bash
# No browser, network service, push, deployment or private references.
set -euo pipefail
cd "$(dirname "$0")"
BL=${BLENDER:-blender}
GT=${GLTF_TRANSFORM:-tools/gltf/node_modules/.bin/gltf-transform}
mkdir -p logs compare/wall check web evidence/windows
python3 -m unittest check/test_alley_layout.py check/test_asset_pipeline.py -v > logs/unit.log 2>&1
python3 src/house_table.py
python3 src/params_md.py
"$BL" -b -t 4 --python-exit-code 1 -P build.py > logs/build.log 2>&1
"$BL" -b -t 4 --python-exit-code 1 building.blend -P check/test_aperture_geometry.py > logs/apertures.log 2>&1
"$BL" -b -t 4 --python-exit-code 1 building.blend -P check/test_glass_assets.py -- --report check/glass_report.json > logs/glass.log 2>&1
python3 check/test_m13_faces.py
"$BL" -b -t 4 --python-exit-code 1 building.blend -P check/test_alley_assets.py > logs/alleys.log 2>&1
"$BL" -b -t 4 --python-exit-code 1 building.blend -P check/circulation_check.py > logs/circulation.log 2>&1
python3 - <<'VALIDATE'
import json
r=json.load(open('check/circulation_report.json'));assert r[0]['PASS'] and r[1]['caught'] and r[2]['caught'],r
VALIDATE
"$GT" optimize building.glb web/building_opt.glb --compress meshopt --texture-compress webp --simplify false --join-named false --flatten false --instance false > logs/optimize.log 2>&1
cp spaces.json web/spaces.json
python3 check/audit_glass_glb.py building.glb web/building_opt.glb > evidence/glass_glb.json
node check/audit_alley_glb.cjs "$PWD" evidence/guard_contract.json evidence/alley_glb_report.json evidence/alley_contract.json
"$BL" -b -t 4 --python-exit-code 1 -P check/trace_all_windows.py -- "$PWD" "$PWD/evidence/inventory.json" > logs/trace.log 2>&1
node check/decode_window_glb.cjs "$PWD" "$PWD/evidence/windows/glb_decoded.json"
"$BL" -b -t 4 --python-exit-code 1 building.blend -P check/audit_all_windows.py -- evidence/inventory.json evidence/windows > logs/windows.log 2>&1
python3 check/test_all_windows.py evidence/windows/windows_full.json
sha256sum building.glb web/building_opt.glb spaces.json
printf 'REPRODUCED ASSET CHECKS PASS; browser/controls/glass appearance NOT TESTED.\n'
