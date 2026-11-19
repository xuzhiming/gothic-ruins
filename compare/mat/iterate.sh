#!/bin/bash
# one material round: textures -> build (no export) -> neutral + matid renders -> per-material dE vs reference
set -e; cd "$(dirname "$0")/../.."; TAG=${1:-iter}; BL=${BLENDER:-/home/box/.local/bin/blender}
python3 src/make_textures.py > /dev/null
PARAMS=params.json OUTDIR=compare/work/mat_$TAG NO_EXPORT=1 $BL -b -P build.py 2>&1 | grep -E "BUILD OK|Error" 
$BL -b compare/work/mat_$TAG/building.blend -P compare/mat/render_mat.py -- compare/mat/$TAG 1000 48 2>&1 | grep -E "OK|Error"
python3 compare/mat/mat_compare.py compare/mat/$TAG $TAG
