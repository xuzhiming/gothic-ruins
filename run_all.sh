#!/usr/bin/env bash
# One-command pipeline: params.json -> model -> compare -> circulation check -> GLB/web -> walk test -> beauty render.
#   ./run_all.sh                    full run (compare loop off: scores the current params only)
#   COMPARE_ROUNDS=4 ./run_all.sh   also run 4 automatic compare/adjust rounds first (appends to compare_log.md, updates params.json)
#   BEAUTY_SAMPLES=128 BEAUTY_RES=1600 FAST=1 (FAST=1 skips the beauty render)
set -euo pipefail
cd "$(dirname "$0")"; R=$(pwd)
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
cp spaces.json web/spaces.json
ls -l building.glb web/building_opt.glb | awk '{print $5, $9}'

step "7/8 preview server + headless-Chrome walk test"
if ! curl -sf -o /dev/null "http://localhost:$PORT/index.html"; then
  nohup python3 -m http.server "$PORT" --directory "$R/web" > logs/http.log 2>&1 &
  sleep 1
fi
python3 walk/walk_test.py --url "http://localhost:$PORT/index.html" | tee logs/walk.log | tail -4
python3 -c "import json,sys; r=json.load(open('walk/walk_result.json')); print('walk:', 'PASS' if r['PASS'] else 'FAIL'); sys.exit(0 if r['PASS'] else 1)"

if [ "${FAST:-0}" != "1" ]; then
  step "8/8 beauty render (Cycles, isometric reference angle)"
  $BL -b building.blend -P src/render_beauty.py -- renders/beauty_iso.png ${BEAUTY_SAMPLES:-96} ${BEAUTY_RES:-1600} --az 22 --el 50 --warm --fog $(python3 -c "import json;print(json.load(open('compare/mat/warm_light.json'))['fog'])") > logs/beauty.log 2>&1
  ls -l renders/beauty_iso.png | awk '{print $5, $9}'
fi
step "done - preview: http://localhost:$PORT/index.html"
