# compare_log.md - automatic silhouette comparison loop

Scores: IoU of model vs reference silhouettes per orthographic view (reference panels aligned to metres, see params.md / compare/compare.py);
skyline (top-edge) error = mean |z_model - z_ref| per column. Plan view: IoU of the site outline + IoU of building footprints read off the plan.
Objective J = mean(4 elevation IoUs + footprint IoU) - 0.01 * mean skyline MAE. Zone errors are model minus reference (m).

## Round 0 (2026-11-19 13:06, baseline of current params.json)

| view | IoU | skyline MAE (m) | skyline RMSE (m) | max height model / ref (m) |
|---|---|---|---|---|
| south | 0.812 | 4.57 | 6.38 | 41.3 / 41.5 |
| north | 0.796 | 4.80 | 6.12 | 41.3 / 41.5 |
| west | 0.757 | 5.96 | 7.98 | 41.3 / 41.5 |
| east | 0.766 | 5.74 | 7.69 | 41.3 / 41.5 |
| top (plan) | site 0.942 / building footprint 0.853 | outline dist 1.19 | - | - |

J = 0.7442

Zone errors (largest first):

- north u[-31.0,-21.0] -> `houses.eave_extra` (mean): +6.54 m
- north u[21.0,31.0] -> `houses.eave_extra` (mean): +6.36 m
- west u[-40.0,-33.0] -> `cathedral.apse.wall_top` (mean): +6.14 m
- east u[33.0,40.0] -> `cathedral.apse.wall_top` (mean): +5.87 m
- south u[12.6,15.2] -> `cathedral.pinnacle_h` (max): +3.00 m
- south u[-15.2,-13.8] -> `cathedral.pinnacle_h` (max): +2.20 m
- north u[-3.5,3.5] -> `cathedral.nave_ridge` (mean): -2.03 m
- south u[-1.5,1.5] -> `cathedral.facade_apex` (max): +1.00 m

## Round 1

Start J = 0.7442. The three params whose zones differ most are tried one at a time (new = old - gain x mean zone error);
a trial is kept only if J improves, otherwise a 40% step is tried, otherwise the change is reverted, that param's gain is halved and it sits out the next round.

| param | mean zone error (m) | old | trial | J trial | result |
|---|---|---|---|---|---|
| `cathedral.apse.wall_top` | +6.00 | 22.5 | 21.1 | 0.7444 | **kept** |
| `houses.eave_extra` | +3.27 | 0.0 | -2.614 | 0.7304 | reverted |
| `houses.eave_extra` | +3.27 | 0.0 | -1.046 | 0.7395 | reverted |
| `cathedral.pinnacle_h` | +2.60 | 6.5 | 4.42 | 0.7452 | **kept** |

Scores after round 1 (best so far):

| view | IoU | skyline MAE (m) | skyline RMSE (m) | max height model / ref (m) |
|---|---|---|---|---|
| south | 0.813 | 4.56 | 6.38 | 41.3 / 41.5 |
| north | 0.797 | 4.77 | 6.08 | 41.3 / 41.5 |
| west | 0.758 | 5.94 | 7.93 | 41.3 / 41.5 |
| east | 0.768 | 5.72 | 7.64 | 41.3 / 41.5 |
| top (plan) | site 0.942 / building footprint 0.853 | outline dist 1.19 | - | - |

J = 0.7452 (round start 0.7442); kept: cathedral.apse.wall_top, cathedral.pinnacle_h

Zone errors after the round:

- north u[-31.0,-21.0] -> `houses.eave_extra` (mean): +6.54 m
- north u[21.0,31.0] -> `houses.eave_extra` (mean): +6.36 m
- west u[-40.0,-33.0] -> `cathedral.apse.wall_top` (mean): +6.14 m
- east u[33.0,40.0] -> `cathedral.apse.wall_top` (mean): +5.87 m
- north u[-3.5,3.5] -> `cathedral.nave_ridge` (mean): -2.03 m
- south u[-1.5,1.5] -> `cathedral.facade_apex` (max): +1.00 m
- south u[8.0,10.5] -> `cathedral.tower_se.spire_tip` (max): -1.00 m
- south u[12.6,15.2] -> `cathedral.pinnacle_h` (max): +1.00 m

## Round 2

Start J = 0.7452. The three params whose zones differ most are tried one at a time (new = old - gain x mean zone error);
a trial is kept only if J improves, otherwise a 40% step is tried, otherwise the change is reverted, that param's gain is halved and it sits out the next round.

| param | mean zone error (m) | old | trial | J trial | result |
|---|---|---|---|---|---|
| `cathedral.facade_apex` | +1.00 | 31.6 | 30.8 | 0.7440 | reverted |
| `cathedral.facade_apex` | +1.00 | 31.6 | 31.28 | 0.7448 | reverted |
| `cathedral.tower_se.spire_tip` | -0.90 | 26.5 | 27.22 | 0.7452 | reverted |
| `cathedral.tower_se.spire_tip` | -0.90 | 26.5 | 26.788 | 0.7452 | reverted |

Scores after round 2 (best so far):

| view | IoU | skyline MAE (m) | skyline RMSE (m) | max height model / ref (m) |
|---|---|---|---|---|
| south | 0.813 | 4.56 | 6.38 | 41.3 / 41.5 |
| north | 0.797 | 4.77 | 6.08 | 41.3 / 41.5 |
| west | 0.758 | 5.94 | 7.93 | 41.3 / 41.5 |
| east | 0.768 | 5.72 | 7.64 | 41.3 / 41.5 |
| top (plan) | site 0.942 / building footprint 0.853 | outline dist 1.19 | - | - |

J = 0.7452 (round start 0.7452); kept: none

Zone errors after the round:

- north u[-31.0,-21.0] -> `houses.eave_extra` (mean): +6.54 m
- north u[21.0,31.0] -> `houses.eave_extra` (mean): +6.36 m
- west u[-40.0,-33.0] -> `cathedral.apse.wall_top` (mean): +6.14 m
- east u[33.0,40.0] -> `cathedral.apse.wall_top` (mean): +5.87 m
- north u[-3.5,3.5] -> `cathedral.nave_ridge` (mean): -2.03 m
- south u[-1.5,1.5] -> `cathedral.facade_apex` (max): +1.00 m
- south u[8.0,10.5] -> `cathedral.tower_se.spire_tip` (max): -1.00 m
- south u[12.6,15.2] -> `cathedral.pinnacle_h` (max): +1.00 m

## Round 3

Start J = 0.7452. The three params whose zones differ most are tried one at a time (new = old - gain x mean zone error);
a trial is kept only if J improves, otherwise a 40% step is tried, otherwise the change is reverted, that param's gain is halved and it sits out the next round.

| param | mean zone error (m) | old | trial | J trial | result |
|---|---|---|---|---|---|
| `houses.eave_extra` | +3.27 | 0.0 | -1.307 | 0.7392 | reverted |
| `houses.eave_extra` | +3.27 | 0.0 | -0.523 | 0.7432 | reverted |
| `cathedral.nave_ridge` | -0.84 | 29.5 | 30.172 | 0.7437 | reverted |
| `cathedral.nave_ridge` | -0.84 | 29.5 | 29.769 | 0.7447 | reverted |
| `cathedral.pinnacle_h` | +0.60 | 4.42 | 3.94 | 0.7454 | **kept** |

Scores after round 3 (best so far):

| view | IoU | skyline MAE (m) | skyline RMSE (m) | max height model / ref (m) |
|---|---|---|---|---|
| south | 0.813 | 4.55 | 6.38 | 41.3 / 41.5 |
| north | 0.797 | 4.76 | 6.06 | 41.3 / 41.5 |
| west | 0.758 | 5.93 | 7.92 | 41.3 / 41.5 |
| east | 0.768 | 5.72 | 7.64 | 41.3 / 41.5 |
| top (plan) | site 0.942 / building footprint 0.853 | outline dist 1.19 | - | - |

J = 0.7454 (round start 0.7452); kept: cathedral.pinnacle_h

Zone errors after the round:

- north u[-31.0,-21.0] -> `houses.eave_extra` (mean): +6.54 m
- north u[21.0,31.0] -> `houses.eave_extra` (mean): +6.36 m
- west u[-40.0,-33.0] -> `cathedral.apse.wall_top` (mean): +6.14 m
- east u[33.0,40.0] -> `cathedral.apse.wall_top` (mean): +5.87 m
- north u[-3.5,3.5] -> `cathedral.nave_ridge` (mean): -2.03 m
- south u[-1.5,1.5] -> `cathedral.facade_apex` (max): +1.00 m
- south u[8.0,10.5] -> `cathedral.tower_se.spire_tip` (max): -1.00 m
- north u[-10.5,-8.0] -> `cathedral.tower_se.spire_tip` (max): -0.80 m

## Round 4

Start J = 0.7454. The three params whose zones differ most are tried one at a time (new = old - gain x mean zone error);
a trial is kept only if J improves, otherwise a 40% step is tried, otherwise the change is reverted, that param's gain is halved and it sits out the next round.

| param | mean zone error (m) | old | trial | J trial | result |
|---|---|---|---|---|---|
| `cathedral.facade_apex` | +1.00 | 31.6 | 31.2 | 0.7448 | reverted |
| `cathedral.facade_apex` | +1.00 | 31.6 | 31.44 | 0.7451 | reverted |
| `cathedral.tower_se.spire_tip` | -0.90 | 26.5 | 26.86 | 0.7454 | reverted |
| `cathedral.tower_se.spire_tip` | -0.90 | 26.5 | 26.644 | 0.7454 | reverted |

Scores after round 4 (best so far):

| view | IoU | skyline MAE (m) | skyline RMSE (m) | max height model / ref (m) |
|---|---|---|---|---|
| south | 0.813 | 4.55 | 6.38 | 41.3 / 41.5 |
| north | 0.797 | 4.76 | 6.06 | 41.3 / 41.5 |
| west | 0.758 | 5.93 | 7.92 | 41.3 / 41.5 |
| east | 0.768 | 5.72 | 7.64 | 41.3 / 41.5 |
| top (plan) | site 0.942 / building footprint 0.853 | outline dist 1.19 | - | - |

J = 0.7454 (round start 0.7454); kept: none

Zone errors after the round:

- north u[-31.0,-21.0] -> `houses.eave_extra` (mean): +6.54 m
- north u[21.0,31.0] -> `houses.eave_extra` (mean): +6.36 m
- west u[-40.0,-33.0] -> `cathedral.apse.wall_top` (mean): +6.14 m
- east u[33.0,40.0] -> `cathedral.apse.wall_top` (mean): +5.87 m
- north u[-3.5,3.5] -> `cathedral.nave_ridge` (mean): -2.03 m
- south u[-1.5,1.5] -> `cathedral.facade_apex` (max): +1.00 m
- south u[8.0,10.5] -> `cathedral.tower_se.spire_tip` (max): -1.00 m
- north u[-10.5,-8.0] -> `cathedral.tower_se.spire_tip` (max): -0.80 m

## Round 5

Start J = 0.7454. The three params whose zones differ most are tried one at a time (new = old - gain x mean zone error);
a trial is kept only if J improves, otherwise a 40% step is tried, otherwise the change is reverted, that param's gain is halved and it sits out the next round.

| param | mean zone error (m) | old | trial | J trial | result |
|---|---|---|---|---|---|
| `houses.eave_extra` | +3.27 | 0.0 | -0.654 | 0.7423 | reverted |
| `houses.eave_extra` | +3.27 | 0.0 | -0.261 | 0.7440 | reverted |
| `cathedral.nave_ridge` | -0.84 | 29.5 | 29.836 | 0.7449 | reverted |
| `cathedral.nave_ridge` | -0.84 | 29.5 | 29.634 | 0.7452 | reverted |

Scores after round 5 (best so far):

| view | IoU | skyline MAE (m) | skyline RMSE (m) | max height model / ref (m) |
|---|---|---|---|---|
| south | 0.813 | 4.55 | 6.38 | 41.3 / 41.5 |
| north | 0.797 | 4.76 | 6.06 | 41.3 / 41.5 |
| west | 0.758 | 5.93 | 7.92 | 41.3 / 41.5 |
| east | 0.768 | 5.72 | 7.64 | 41.3 / 41.5 |
| top (plan) | site 0.942 / building footprint 0.853 | outline dist 1.19 | - | - |

J = 0.7454 (round start 0.7454); kept: none

Zone errors after the round:

- north u[-31.0,-21.0] -> `houses.eave_extra` (mean): +6.54 m
- north u[21.0,31.0] -> `houses.eave_extra` (mean): +6.36 m
- west u[-40.0,-33.0] -> `cathedral.apse.wall_top` (mean): +6.14 m
- east u[33.0,40.0] -> `cathedral.apse.wall_top` (mean): +5.87 m
- north u[-3.5,3.5] -> `cathedral.nave_ridge` (mean): -2.03 m
- south u[-1.5,1.5] -> `cathedral.facade_apex` (max): +1.00 m
- south u[8.0,10.5] -> `cathedral.tower_se.spire_tip` (max): -1.00 m
- north u[-10.5,-8.0] -> `cathedral.tower_se.spire_tip` (max): -0.80 m

## Result of this loop

params.json updated with the best accepted round.

| view | IoU | skyline MAE (m) | skyline RMSE (m) | max height model / ref (m) |
|---|---|---|---|---|
| south | 0.813 | 4.55 | 6.38 | 41.3 / 41.5 |
| north | 0.797 | 4.76 | 6.06 | 41.3 / 41.5 |
| west | 0.758 | 5.93 | 7.92 | 41.3 / 41.5 |
| east | 0.768 | 5.72 | 7.64 | 41.3 / 41.5 |
| top (plan) | site 0.942 / building footprint 0.853 | outline dist 1.19 | - | - |

J = 0.7454


## Manual round M1 (2026-11-19 13:28, gap #1: verticality + pinnacles, visual fidelity over silhouette score)

Read off ref front_south / back_north / left_west / right_east / isometric: nave eave ~24-25 m (clerestory windows ~18.6-22.8 m), ridge ~30 m;
SW tower = lower stage to ~20.7 m, set-back belfry with two tiers of tall paired lancets to ~31 m, 4 corner pinnacles to ~33 m, slender
octagonal spire (base dia ~2-3 m) to 41.5 m incl. cross; SE tower = shorter belfry + spirelet ~28.5 m; pinnacle at every bay line on the
clerestory (rising above the eave, ~31 m) and on every apse vertex; tall slender pinnacles (~6.5 m) on every aisle / chevet buttress;
facade flank pinnacles to ~31.8 m; tall traceried lancets in the aisle fronts.

Changes (params.json + build.py; all now in `compare_lock` so the loop cannot undo them):

- `cathedral.nave_wall_top` 22.5 -> 24.0; `apse.wall_top` 21.1 -> 24.0 (continuous clerestory); `flyer_z_in` 19.0 -> 20.5, `flyer_z_out` 14.5 -> 15.2
- `buttress_top` 16.5 -> 17.5, `pinnacle_h` 3.94 -> 6.5 (aisle + chevet buttress pinnacles, top 24.0 m)
- new `clerestory_pinnacles` {top 31.0, shaft 2.4, w 0.8}: buttress strips + pinnacles at 5 bay lines x 2 sides + 7 apse vertices
- new `facade_pinnacle_top` 31.8 (was implicit 30.6); new `pinnacle_spikes`: 4 corner pinnaclets + crocket bands on every pinnacle
- `tower_sw`: top 30.0 -> 31.0, `spire_r` 1.9 -> 1.45, new belfry_z0 20.7 / belfry_w 3.9 / 2 lancet tiers / corner pinnacles to 33.2 / stage pinnacles to 24.9
- `tower_se`: top 21.5 -> 23.5, pyramid -> octagonal spirelet r 1.2 to 28.5, belfry_z0 18.2 / belfry_w 3.6 / corner pinnacles to 26.0
- new `aisle_front_lancet` {w 2.2, sill 3.0, apex 8.6} (was 1.4 x 4.0-9.0)

| view | IoU before -> after | skyline MAE (m) before -> after |
|---|---|---|
| south | 0.809 -> 0.825 | 4.57 -> 4.15 |
| north | 0.796 -> 0.804 | 4.78 -> 4.59 |
| west | 0.761 -> 0.755 | 5.89 -> 6.11 |
| east | 0.769 -> 0.762 | 5.74 -> 5.97 |
| plan footprint | 0.862 -> 0.862 | - |

(0.1 m/px renders.) Front/back improve; the side views lose ~0.007 IoU because the taller clerestory/pinnacles are drawn shorter in the
side references over the house rows (the known side-view/plan length inconsistency). Kept deliberately.
## Round 0 (2026-11-19 13:29, baseline of current params.json)

| view | IoU | skyline MAE (m) | skyline RMSE (m) | max height model / ref (m) |
|---|---|---|---|---|
| south | 0.827 | 4.17 | 5.96 | 41.3 / 41.5 |
| north | 0.804 | 4.59 | 5.90 | 41.3 / 41.5 |
| west | 0.751 | 6.17 | 8.51 | 41.3 / 41.5 |
| east | 0.760 | 5.96 | 8.23 | 41.3 / 41.5 |
| top (plan) | site 0.942 / building footprint 0.853 | outline dist 1.19 | - | - |

J = 0.7470

Zone errors (largest first):

- north u[-31.0,-21.0] -> `houses.eave_extra` (mean): +6.54 m
- north u[21.0,31.0] -> `houses.eave_extra` (mean): +6.36 m
- west u[-40.0,-33.0] -> `cathedral.apse.wall_top` (mean): +6.19 m
- east u[33.0,40.0] -> `cathedral.apse.wall_top` (mean): +5.93 m
- south u[12.6,15.2] -> `cathedral.pinnacle_h` (max): +4.00 m
- south u[-15.2,-13.8] -> `cathedral.pinnacle_h` (max): +3.20 m
- north u[-10.5,-8.0] -> `cathedral.tower_se.spire_tip` (max): +1.20 m
- north u[-3.5,3.5] -> `cathedral.nave_ridge` (mean): -1.11 m

## Round 1

Start J = 0.7470. The three params whose zones differ most are tried one at a time (new = old - gain x mean zone error);
a trial is kept only if J improves, otherwise a 40% step is tried, otherwise the change is reverted, that param's gain is halved and it sits out the next round.

| param | mean zone error (m) | old | trial | J trial | result |
|---|---|---|---|---|---|
| `houses.eave_extra` | +3.27 | 0.0 | -2.614 | 0.7331 | reverted |
| `houses.eave_extra` | +3.27 | 0.0 | -1.046 | 0.7422 | reverted |
| `cathedral.facade_apex` | +1.00 | 31.6 | 30.8 | 0.7462 | reverted |
| `cathedral.facade_apex` | +1.00 | 31.6 | 31.28 | 0.7467 | reverted |
| `cathedral.nave_ridge` | -0.47 | 29.5 | 29.873 | 0.7465 | reverted |
| `cathedral.nave_ridge` | -0.47 | 29.5 | 29.649 | 0.7467 | reverted |

Scores after round 1 (best so far):

| view | IoU | skyline MAE (m) | skyline RMSE (m) | max height model / ref (m) |
|---|---|---|---|---|
| south | 0.827 | 4.17 | 5.96 | 41.3 / 41.5 |
| north | 0.804 | 4.59 | 5.90 | 41.3 / 41.5 |
| west | 0.751 | 6.17 | 8.51 | 41.3 / 41.5 |
| east | 0.760 | 5.96 | 8.23 | 41.3 / 41.5 |
| top (plan) | site 0.942 / building footprint 0.853 | outline dist 1.19 | - | - |

J = 0.7470 (round start 0.7470); kept: none

Zone errors after the round:

- north u[-31.0,-21.0] -> `houses.eave_extra` (mean): +6.54 m
- north u[21.0,31.0] -> `houses.eave_extra` (mean): +6.36 m
- west u[-40.0,-33.0] -> `cathedral.apse.wall_top` (mean): +6.19 m
- east u[33.0,40.0] -> `cathedral.apse.wall_top` (mean): +5.93 m
- south u[12.6,15.2] -> `cathedral.pinnacle_h` (max): +4.00 m
- south u[-15.2,-13.8] -> `cathedral.pinnacle_h` (max): +3.20 m
- north u[-10.5,-8.0] -> `cathedral.tower_se.spire_tip` (max): +1.20 m
- north u[-3.5,3.5] -> `cathedral.nave_ridge` (mean): -1.11 m

## Round 2

All remaining zone errors <= 0.3 m (or their params exhausted) - converged, no change.

## Result of this loop

params.json updated with the best accepted round.

| view | IoU | skyline MAE (m) | skyline RMSE (m) | max height model / ref (m) |
|---|---|---|---|---|
| south | 0.827 | 4.17 | 5.96 | 41.3 / 41.5 |
| north | 0.804 | 4.59 | 5.90 | 41.3 / 41.5 |
| west | 0.751 | 6.17 | 8.51 | 41.3 / 41.5 |
| east | 0.760 | 5.96 | 8.23 | 41.3 / 41.5 |
| top (plan) | site 0.942 / building footprint 0.853 | outline dist 1.19 | - | - |

J = 0.7470

## Manual round M2 (2026-11-19 14:10, gap #2: house variety; per-house table, visual fidelity over silhouette score)

Per-house table read off top_plan / left_west / right_east / front_south / back_north / isometric (src/house_table.py ->
params.json houses.list + houses_table.md; `houses.list` added to `compare_lock`). Main changes: 6 -> 5 houses per row (plan party walls),
widths 10.2-18.3 m, eave offsets -0.8..+0.3 m, pitch from the measured ridge rise (29-42 deg instead of 50 everywhere), per-house
ground-floor / upper materials, half-timber patterns (grid / braced / X), jetties 0.3-0.45 m, setbacks 0-0.35 m, street cross gables,
street + rear dormers, chimneys at the plan positions, roof-hole fractions, brick patches on plaster, pentice roofs, rubble end walls.

| view | IoU before -> after | skyline MAE (m) before -> after |
|---|---|---|
| south | 0.825 -> 0.811 | 4.15 -> 4.48 |
| north | 0.804 -> 0.812 | 4.59 -> 4.40 |
| west | 0.755 -> 0.721 | 6.11 -> 6.98 |
| east | 0.762 -> 0.728 | 5.97 -> 6.82 |
| plan footprint | 0.862 -> 0.848 | - |

Intermediate test with the same table but the old steep pitches (40-50 deg): south 0.821, north 0.789, west 0.747, east 0.754.
So ~0.026 of the side-view loss comes from the lower (measured) roofs: in left_west/right_east the space above the house roofs is
filled by the cathedral (drawn ~25 m longer there than in the plan), so lower roofs uncover reference pixels. North improves
because the rear elevations' house heights now match. The loop's global `houses.eave_extra` trials (-1.8 / -0.7 m) were reverted.

## Round 0 (2026-11-19 14:12, baseline of current params.json)

| view | IoU | skyline MAE (m) | skyline RMSE (m) | max height model / ref (m) |
|---|---|---|---|---|
| south | 0.814 | 4.46 | 6.21 | 41.3 / 41.5 |
| north | 0.811 | 4.40 | 6.04 | 41.3 / 41.5 |
| west | 0.718 | 7.02 | 9.38 | 41.3 / 41.5 |
| east | 0.727 | 6.81 | 9.11 | 41.3 / 41.5 |
| top (plan) | site 0.942 / building footprint 0.838 | outline dist 1.19 | - | - |

J = 0.7248

Zone errors (largest first):

- west u[-40.0,-33.0] -> `cathedral.apse.wall_top` (mean): +6.19 m
- east u[33.0,40.0] -> `cathedral.apse.wall_top` (mean): +5.93 m
- north u[21.0,31.0] -> `houses.eave_extra` (mean): +5.69 m
- north u[-31.0,-21.0] -> `houses.eave_extra` (mean): +5.16 m
- south u[12.6,15.2] -> `cathedral.pinnacle_h` (max): +4.00 m
- south u[-15.2,-13.8] -> `cathedral.pinnacle_h` (max): +3.20 m
- south u[21.0,31.0] -> `houses.eave_extra` (mean): -1.58 m
- north u[-10.5,-8.0] -> `cathedral.tower_se.spire_tip` (max): +1.20 m

## Round 1

Start J = 0.7248. The three params whose zones differ most are tried one at a time (new = old - gain x mean zone error);
a trial is kept only if J improves, otherwise a 40% step is tried, otherwise the change is reverted, that param's gain is halved and it sits out the next round.

| param | mean zone error (m) | old | trial | J trial | result |
|---|---|---|---|---|---|
| `houses.eave_extra` | +2.30 | 0.0 | -1.842 | 0.7134 | reverted |
| `houses.eave_extra` | +2.30 | 0.0 | -0.737 | 0.7205 | reverted |
| `cathedral.facade_apex` | +1.00 | 31.6 | 30.8 | 0.7239 | reverted |
| `cathedral.facade_apex` | +1.00 | 31.6 | 31.28 | 0.7245 | reverted |
| `cathedral.nave_ridge` | -0.47 | 29.5 | 29.873 | 0.7243 | reverted |
| `cathedral.nave_ridge` | -0.47 | 29.5 | 29.649 | 0.7245 | reverted |

Scores after round 1 (best so far):

| view | IoU | skyline MAE (m) | skyline RMSE (m) | max height model / ref (m) |
|---|---|---|---|---|
| south | 0.814 | 4.46 | 6.21 | 41.3 / 41.5 |
| north | 0.811 | 4.40 | 6.04 | 41.3 / 41.5 |
| west | 0.718 | 7.02 | 9.38 | 41.3 / 41.5 |
| east | 0.727 | 6.81 | 9.11 | 41.3 / 41.5 |
| top (plan) | site 0.942 / building footprint 0.838 | outline dist 1.19 | - | - |

J = 0.7248 (round start 0.7248); kept: none

Zone errors after the round:

- west u[-40.0,-33.0] -> `cathedral.apse.wall_top` (mean): +6.19 m
- east u[33.0,40.0] -> `cathedral.apse.wall_top` (mean): +5.93 m
- north u[21.0,31.0] -> `houses.eave_extra` (mean): +5.69 m
- north u[-31.0,-21.0] -> `houses.eave_extra` (mean): +5.16 m
- south u[12.6,15.2] -> `cathedral.pinnacle_h` (max): +4.00 m
- south u[-15.2,-13.8] -> `cathedral.pinnacle_h` (max): +3.20 m
- south u[21.0,31.0] -> `houses.eave_extra` (mean): -1.58 m
- north u[-10.5,-8.0] -> `cathedral.tower_se.spire_tip` (max): +1.20 m

## Round 2

All remaining zone errors <= 0.3 m (or their params exhausted) - converged, no change.

## Result of this loop

params.json updated with the best accepted round.

| view | IoU | skyline MAE (m) | skyline RMSE (m) | max height model / ref (m) |
|---|---|---|---|---|
| south | 0.814 | 4.46 | 6.21 | 41.3 / 41.5 |
| north | 0.811 | 4.40 | 6.04 | 41.3 / 41.5 |
| west | 0.718 | 7.02 | 9.38 | 41.3 / 41.5 |
| east | 0.727 | 6.81 | 9.11 | 41.3 / 41.5 |
| top (plan) | site 0.942 / building footprint 0.838 | outline dist 1.19 | - | - |

J = 0.7248


## Manual round M3 (2026-11-19 14:30, gap #3: plaster texture - materials/UVs only, no geometry change)

New seamless lime-plaster textures (periodic FFT noise, 1024 px over 4 m, tones A/B/C per house), red blotches removed,
plaster UV tile 3.0 -> 4.0 m (no longer phase-locked to the 3.2 m storey) + per-house UV offset. Silhouette scores unchanged:
south 0.811, north 0.812, west 0.721, east 0.728, plan footprint 0.848.

## Manual round M4 (2026-11-19 15:05, gap #4: ruined / decayed Gothic look - params.json `ruin`, locked)

Geometry damage (snapped/chipped pinnacles, lost panes + tracery, partial rose, west-slope collapse over bay 5, broken rafters/purlins,
house roof collapses W1/E3/NE + sags, collapsed chimneys, crumbling balustrades/cornice, rubble heaps, fallen rafters, debris) and
weathering (seamless moss/soot textures, alpha decals). Silhouette scores (before -> after):
south 0.811 -> 0.808, north 0.812 -> 0.812, west 0.721 -> 0.721, east 0.728 -> 0.728, plan site 0.941 -> 0.942, footprint 0.848 -> 0.851.

## Manual round M5 (2026-11-19, gap #5: west/east elevation IoU - diagnosis first; result: documented compromise, no geometry change)

Tools: `compare/diag_side.py` (per-column FP/FN overlay + skylines + zone breakdown, now also run by run_all.sh step 4 -> compare/diag/diag_*_current.png),
`compare/mask_check.py` (mask threshold/morphology sensitivity), `compare/align_scan.py` (anchor scale/shift scan, diagnostic only),
`compare/ref_check_sheet.py` (mask outline + anchors on the ref panels), `compare/experiment.py` (score a variant on all views without touching params.json).

Diagnosis (west / east, IoU 0.721 / 0.728):
- Extraction is not the problem: mask follows the drawn outline (compare/diag/ref_check_sides.png); looser / stricter thresholds and no-closing change IoU by <= 0.0014
  (west 0.7222 / 0.7207 / 0.7208, east 0.7292 / 0.7270 / 0.7278). Closing is what keeps the spire cross (top anchor) - without it the bbox top drops 19 px.
  No title bar; ground line = plinth base; top = cross tip.
- Projection: orthographic (verticals vertical, no receding side walls; cathedral ridge reads 29-31 m in all four elevations, i.e. no depth scaling).
- Content: ref silhouette = rear of the house row UNION the cathedral behind it (same as the model render). Houses band (4.4-17.5 m) matches exactly (0 FP / 0 FN)
  because the cathedral fills everything behind it -> house roof heights have no W/E effect.
- Loss by zone (west, IoU-loss points): over the plaza (ref draws nave+tower+spire where the plan has the open plaza) 0.148, apse/chevet z>17.5 0.048,
  north end low 0.033, south-end terrace 0.014, nave 0.013, plinth 0.012, towers 0.011, houses 0.000. East the same (0.147 / 0.047 / 0.031 ...).
  IoU without the plaza conflict zone: 0.840 / 0.849. The side refs draw the cathedral ~79 m long (spire over plaza y~-28.6) and compress the north
  end ~3-4 m (corner house y 26-37 vs plan 36.9-47.9; tall apse block ends y~43 vs plan apse disc tip 50.3).
- Alignment scan: best 0.781 at x-scale 1.06 + shift 4 m (south), but that slides the ref plinth ends past the site edge and only overlays the
  drawn-too-long cathedral; anchors are feature-consistent (stairs/terrace end, plinth ends) -> not changed (would move the target).

Options quantified (S / N / W / E / top site / footprint; base 0.808 / 0.812 / 0.721 / 0.728 / 0.942 / 0.851):
| option | S | N | W | E | footprint | verdict |
|---|---|---|---|---|---|---|
| E1 lengthen cathedral to facade y -28 (10 bays, towers/steps/gate moved) | 0.807 | 0.814 | 0.843 | 0.849 | 0.649 | rejected: builds over the plan's plaza, bollard ring, steps |
| E2 facade to y 0 (-3.9 m) | 0.808 | 0.815 | 0.727 | 0.733 | 0.820 | rejected: -0.031 footprint for +0.006 |
| E3 apse wall_top 21.1 / roof 27.1 (gap #1 lock) | 0.807 | 0.814 | 0.724 | 0.731 | 0.851 | rejected: +0.003, undoes gap #1 apse height |
| E4 chevet pier pinnacles 2.5 m | 0.808 | 0.812 | 0.722 | 0.729 | 0.851 | rejected: +0.001, iso shows full pinnacles |
| E5 apse centre 41 -> 40 / 39 / 38 / 37 | .808/.809/.808/.806 | .812/.814/.812/.811 | .717/.732/.741/.735 | .724/.739/.748/.742 | .854/.854/.851/.849 | rejected: plan apse disc tip at y 50.3 would be left 2-4 m uncovered (footprint flat only because the model chevet is wider than the traced disc); non-monotonic W/E (40, 37) = ruin rng shifts in the nave roof |
| E6 all houses eave -1.5 m | 0.791 | 0.829 | 0.700 | 0.707 | 0.851 | rejected: houses band empties, south worse |
| E7 narrower chevet (r_amb 7.5, r_pier 8.3, cy 41.6) | 0.808 | 0.812 | 0.718 | 0.725 | 0.855 | rejected: W/E worse |
| E8 corner houses lower / flatter (a/b/c) | .804/.802/.799 | .815/.816/.816 | .720/.721/.720 | .727/.728/.727 | 0.851 | rejected: north +0.004, south -0.004..-0.009, W/E 0 |

Decision: keep the plan-consistent geometry. The W/E ceiling without contradicting the plan is ~0.72-0.73 (plan-consistent part 0.84 / 0.85);
the remaining loss is a drawing inconsistency between the side elevations and the plan/front/iso, not an extraction, alignment or modelling error.

## Manual round M6 (2026-11-19 16:03, gap #6: apse compromise - user-approved option E5)

`cathedral.apse.cy` 41.0 -> 38.0 (locked in compare_lock; params.md marks it as a deliberate compromise between the side elevations,
which put the apse block 3-4 m further south, and the plan, whose apse disc tip at y 50.3 is now left ~3 m uncovered).
Everything keyed to the apse follows cy: chevet, ambulatory walls/roofs, piers, flyers, pinnacles, apse roof + finials, podium half-disc,
ambulatory space probe, altar, apse rubble piles, ruin keep-out ring (now re-centred on cy in build.py) and the walk-test apse waypoints.
Short straight choir bay (2.7 m): choir->ambulatory openings use thinner jambs (w = Lch - 0.8 when Lch < 4 m), choir clerestory lancet
and ambulatory side lancets narrowed to fit the bay (no overlap with the pier strips).
Ruin streams: per-element pins (ruin_streams.json recorded from the approved build; reproduces it to 4 um) + fixed 1.3 m tile columns
on the nave slopes. Nave roof hole map unchanged except one hole in a column that no longer exists (west slope 41 -> 40 cells,
east 102 -> 102, aisles identical); rafters identical; rubble piles identical except the 3 apse-base piles, moved 3.0 m south with the apse.

| view | IoU before -> after | skyline MAE (m) before -> after |
|---|---|---|
| south | 0.808 -> 0.808 | 4.58 -> 4.58 |
| north | 0.812 -> 0.812 | 4.22 -> 4.22 |
| west | 0.721 -> 0.741 | 6.99 -> 6.32 |
| east | 0.728 -> 0.748 | 6.84 -> 6.17 |
| top (plan) | site 0.942 -> 0.942, footprint 0.851 -> 0.851 | outline 1.19 -> 1.19 |

Circulation PASS (86 reachable, both negative tests caught), walk test PASS (0 penetrations, 0 stuck).

## M7 — exterior materials matched to reference renders (gap #7, 2026-11-19)
Method: ref colour stats from hand-placed rects (compare/mat/ref_samples.json, locations in compare/mat/ref_sample_locations_*.png);
ours = Cycles neutral-light iso (white sky 0.85/0.9, white sun 3.2, AgX, az22 el50 ortho118) + Workbench material-ID mask, median of
eroded pure mask, one frozen global gain 1.231; ΔE = CIEDE2000. Grade = per-texture linear gains (compare/mat/grade.json, 7 rounds).
| material | ΔE before | ΔE after |
|---|---|---|
| stone_cathedral | 3.7 | 1.1 |
| slate | 12.5 | 0.7 |
| plaster | 2.5 | 0.9 |
| brick | 7.3 | 0.6 |
| timber | 9.9 | 0.8 |
| stone_plinth | 3.1 | 0.2 |
| plinth_rock | 8.4 | 0.3 |
| cobble | 8.5 | 0.8 |
| stair | 8.4 | 0.6 |
| chimney | 1.8 | 0.5 |
| iron | 7.7 | 0.4 |
| (house_walls union) | 3.4 | 1.6 |
| mean (11) | 6.71 | 0.62 |
Pattern: slate 8 courses/2 m (0.25 m) slope-aligned UVs; setts ~0.5 m (ref ~0.8 m, kept smaller for street-level read);
house brick 6.25 cm courses; ashlar 0.375 m courses; stair flagstones; soil earth/rock lenses; tangent normal maps (glTF normalTexture).
Buttresses: ref only ~1 L* darker than walls, so no extra darkening. Contrast (IQR L*) still lower than ref on brick/stair, higher on cobble.
Scores unchanged (S .808 N .812 W .741 E .748 top .942 fp .851). GLB 22.65 MB raw / 3.72 MB optimized (was 19.24 / 3.45).

## M8 — warm beauty light + material contrast (gap #8, 2026-11-19)
Beauty light: new `--warm` preset in src/render_beauty.py, parameters in compare/mat/warm_light.json (shared reference for the
three.js preview): sky (0.598,0.598,0.585)x1.1, sun 3.6 (1,0.965,0.915) angle 18 deg (soft shadows), AgX Base Contrast, exposure +0.25,
light warm fog 0.0004 (was cool 0.0015), camera-only warm paper backdrop (≈ ref paper 234,228,224). Tuned with compare/mat/beauty_try.sh
(600 px / 24 spp trials) + compare/mat/beauty_compare.py (no gain: whole-building mean Lab + per-material medians vs ref/isometric.png).
Whole building mean Lab ref (44.9, 0.8, 4.1): before (35.1, 0.5, -1.2) dE00 9.95 -> after (44.2, 1.0, 3.9) dE00 0.76; L* IQR 18.3 / 14.0 -> 18.8.
Per-material dE00 under beauty light (1600 px, matid 1600): mean 10.42 -> 1.87 (plaster -6 L* darker than ref, iron/timber +3 L* lighter).
Contrast: make_textures.contrast() two-band log-luminance contrast (low band = blur at 0.12 m, the iso pixel size) per texture
(grade.json "_contrast"), fitted with compare/mat/fit_contrast.py, mean colours refit with fit_grade.py; stronger brick mottling/lime.
Neutral L* IQR ref / M7 / M8: brick 20.8/9.3/14.0, stair 22.5/6.9/13.4, cobble 8.0/13.1/8.8, stone 19.9/28.8/28.6.
Full numeric match was reached (brick 20.8, stair 22.3; grade_m8_full.json, tmp/tex_m8_full) but looked like camouflage brick and
checkerboard stairs at street level; the ref crops show their spread comes from geometry (tread/riser shading, window frames, pipes,
plaster patches), so the shipped state is a compromise (brick [3.0,1.3], stair [2.2,1.3]). Stone spread is shadow/interior dominated
(dark tail L*<25 in the hard-sun neutral render; texture IQR only ~4), texture contrast reduced to [0.7,0.85] with no measurable effect.
Neutral dE00 mean 0.57 (M7 0.62). Preview: AgX tone mapping, warm sky/fog 0xd6cfc4 140-560 m, hemi 0xf4ece0/0x5a5044 1.3, sun 0xfff1df 2.3.
Iron gate b* in preview plaza -1.5 -> +2.8 (no longer blue). Scores unchanged. GLB 22.58 MB / 3.71 MB.

## M9 — stairs: no more bright checkerboard slabs (gap #9, 2026-11-19)
geom.stair(sides=..., top=...): treads "stair", risers "stair_riser", stringer sides "stair_side" (all group Stairs; geometry unchanged,
so riser/tread checks are untouched — no geometric bevel, the nosing roll-off is in the normal map). Per-step UV frames: one 0.4 m
texture row per tread (row bottom = nosing) and one row per riser (row top = under-nosing lip, bottom = grime corner), lateral
offset per step -> the slab pattern follows each step instead of world-tiling across steps. New textures: subtle per-slab tone
(+-4 %, was 0.72..1.17 + contrast x3.9), fine 2 px joints, worn/chipped nosings, darker grime at the back of each tread, darker risers
(lip shadow + foot grime + moss), plain coursed stringers; "_contrast" for stair removed; colours refit (fit_grade, 3 textures).
Applied to the south monumental stairs (both flights) and the cathedral steps. Preview gets it through the GLB (same materials).
Stair dE00: neutral 0.8 -> 0.5, beauty light 1.06 -> 1.14. L* IQR / p10-90 vs ref 22.5 / 40.6: neutral 13.4/26.2 -> 8.9/14.1,
beauty 12.0/24.3 -> 9.5/14.8 (the old spread was the patchy slabs; the remaining gap is tread/riser geometry shading, which in the
0.12 m/px iso is only 1-3 px per step). Scores unchanged; circulation, negatives, walk PASS. GLB 23.40 MB / 3.72 MB.
