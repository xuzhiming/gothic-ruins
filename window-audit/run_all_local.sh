#!/usr/bin/env bash
# One-command pipeline: params.json -> model -> compare -> circulation check -> GLB/web -> walk test -> beauty render.
#   ./run_all.sh                    full run (compare loop off: scores the current params only)
#   COMPARE_ROUNDS=4 ./run_all.sh   also run 4 automatic compare/adjust rounds first (appends to compare_log.md, updates params.json)
#   BEAUTY_SAMPLES=128 BEAUTY_RES=1600 FAST=1 (FAST=1 skips the beauty render)
set -euo pipefail
cd /workspace/gothic; R=$(pwd)
BL=${BLENDER:-/home/box/.local/bin/blender}
GT=${GLTF_TRANSFORM:-$( [ -x tools/gltf/node_modules/.bin/gltf-transform ] && echo tools/gltf/node_modules/.bin/gltf-transform || echo /workspace/tools/gltf/node_modules/.bin/gltf-transform)}   # project-local copy first (shared /workspace/tools may be reset by other jobs)
PORT=${PORT:-8766}
mkdir -p logs renders compare/out
step(){ echo; echo "=== [$(date +%H:%M:%S)] $*"; }

step "1/8 textures + reference silhouettes"
python3 src/make_textures.py > logs/textures.log
python3 compare/ref_extract.py > logs/ref_extract.log
python3 src/house_table.py > logs/house_table.log      # per-house table -> params.json houses.list + houses_table.md

step "2/8 compare loop (rounds=${COMPARE_ROUNDS:-0})"
ROUNDS=${COMPARE_ROUNDS:-0} COMPARE_LOG=$R/$( [ "${COMPARE_ROUNDS:-0}" -gt 0 ] && echo compare_log.md || echo logs/score_check.md ) \
  python3 compare/compare_loop.py | tee logs/compare_loop.log | tail -3
python3 src/params_md.py

step "3/8 build (Blender background, procedural)"
$BL -b -P build.py > logs/build.log 2>&1 || { tail -30 logs/build.log; exit 1; }
grep -E "BUILD OK|spaces" logs/build.log | tail -3

# Glass regression: actual saved Blend, through-hole rays and supported material API.
$BL -b -P check/test_aperture_geometry.py > logs/glass_geometry.log 2>&1
$BL -b building.blend -P check/test_glass_assets.py -- --report check/glass_report.json > logs/glass_assets.log 2>&1
python3 -c "import json; r=json.load(open('check/glass_report.json')); assert r['PASS'],r; print('glass apertures:',r['apertures'],'| unobstructed:',r['unobstructed_apertures'],'| retained occlusions:',r['retained_occlusions'])"
python3 check/test_m13_faces.py

step "4/8 orthographic renders + silhouette compare + side-by-side"
$BL -b building.blend -P src/render_sil.py -- renders 0.1 --shaded > logs/render_sil.log 2>&1
python3 compare/compare.py renders compare/out --sbs | tee logs/compare.log | tail -8
python3 compare/diag_side.py renders compare/diag current | tee logs/diag_side.log | grep IoU

step "5/8 circulation check (+ negative tests)"
$BL -b building.blend -P check/circulation_check.py > logs/check.log 2>&1 || true
python3 - <<'PY'
import json, sys
main, neg, neg2 = json.load(open("check/circulation_report.json"))
ok = main["PASS"] and neg["caught"] and neg2["caught"]
print("circulation:", "PASS" if main["PASS"] else "FAIL", f"| reachable {main['reachable']} | negative test (blocked door) caught: {neg['caught']} | negative test 2 (bad riser) caught: {neg2['caught']}")
sys.exit(0 if ok else 1)
PY

step "6/8 GLB -> gltf-transform (WebP textures, Meshopt geometry)"
$GT optimize building.glb web/building_opt.glb --compress meshopt --texture-compress webp \
    --simplify false --join-named false --flatten false --instance false > logs/gltf.log 2>&1 || { tail -20 logs/gltf.log; exit 1; }
python3 check/audit_glass_glb.py building.glb web/building_opt.glb > logs/glass_glb.json
cp spaces.json web/spaces.json
ls -l building.glb web/building_opt.glb | awk '{print $5, $9}'

step "7/8 NOT RUN: browser/WASD belongs to parent/cloud under explicit no-browser scope"
printf '%s\n' 'NOT RUN t22: local and production browser/WASD verification pending parent/cloud' > window-audit/browser_status.txt

if [ "${FAST:-0}" != "1" ]; then
  step "8/8 beauty render (Cycles, isometric reference angle)"
  $BL -b building.blend -P src/render_beauty.py -- renders/beauty_iso.png ${BEAUTY_SAMPLES:-96} ${BEAUTY_RES:-1600} --az 22 --el 50 --warm --fog $(python3 -c "import json;print(json.load(open('compare/mat/warm_light.json'))['fog'])") > logs/beauty.log 2>&1
  ls -l renders/beauty_iso.png | awk '{print $5, $9}'
fi
step "done - preview: http://localhost:$PORT/index.html"
