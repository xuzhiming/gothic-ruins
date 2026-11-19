#!/bin/bash
# quick beauty-light trial: beauty_try.sh TAG [extra render_beauty args]  (600 px, 24 spp, warm preset + overrides) -> dE table
cd "$(dirname "$0")/../.."; TAG=$1; shift; mkdir -p compare/mat/btry
FOG=$(python3 -c "import json;print(json.load(open('compare/mat/warm_light.json'))['fog'])")
/home/box/.local/bin/blender -b ${BLEND:-building.blend} -P src/render_beauty.py -- compare/mat/btry/$TAG.png 24 600 --az 22 --el 50 --warm --fog $FOG "$@" 2>&1 | grep -E "Error|BEAUTY OK" | head -3
python3 compare/mat/beauty_compare.py compare/mat/btry/$TAG.png compare/mat/after/matid.png try_$TAG | tail -13
