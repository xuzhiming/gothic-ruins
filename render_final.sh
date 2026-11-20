#!/bin/bash
# Final deliverables: HD beauty stills (Cycles CPU + OpenImageDenoise, warm preset) + contact sheet -> final/stills/.
# One Blender process per still (memory). Env: SPP=64 ISO_RES=3000 RES=2560 ONLY="01_hero_iso 05_nave_interior" (subset) OUT=final/stills (output dir)
# Video steps (src/film_path.py + walk/film_capture.py, three.js capture) are DISABLED (user: no videos); VIDEO=1 would re-enable.
set -e; cd "$(dirname "$0")"; BL=${BLENDER:-/home/box/.local/bin/blender}; O=${OUT:-final/stills}; mkdir -p $O logs
SHOTS=${ONLY:-"01_hero_iso 02_aerial_south 03_plaza_facade 04_portal 05_nave_interior 06_street_west 07_apse_NE 08_hero_iso_dusk"}
for s in $SHOTS; do
  case $s in 01_hero_iso|08_hero_iso_dusk) R=${ISO_RES:-3000}; N=${SPP:-64};; 05_nave_interior) R=${RES:-2560}; N=$(( ${SPP:-64}*3/2 ));; *) R=${RES:-2560}; N=${SPP:-64};; esac
  echo "[$(date +%T)] $s ${R}px ${N} spp"
  $BL -b building.blend -P src/render_still.py -- $s $O/$s.png $N $R > logs/still_$s.log 2>&1 || { echo "FAILED $s (see logs/still_$s.log)"; continue; }
  grep "STILL OK" logs/still_$s.log
done
python3 src/contact_sheet.py $O $O/contact_sheet.jpg
if [ "${VIDEO:-0}" = 1 ]; then echo "video steps disabled by request (see src/film_path.py, walk/film_capture.py)"; fi
