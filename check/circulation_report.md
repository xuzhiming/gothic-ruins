# Circulation check report

Model `building.blend`: 86 spaces, 71 doors/gates/openings, 25 stair flights, 6 outdoor links, 0 lifts (the medieval complex has none; lift edges are supported by the checker).

Method: BVH of all solid meshes (door leaves excluded - they open automatically), ray tests through every opening, a sideways ray beside every door that must hit wall (proves the opening pierces a real wall), per-step tread/riser/headroom rays on every flight, floor-continuity sampling on outdoor links, floor + headroom probe in every space, BFS from the entrance `approach`.

## as-built -> **PASS**

- openings ok: 71/71 (pierce their wall: 69/69)
- stair flights ok: 25/25
- outdoor links ok: 6/6
- spaces with floor + >= 2.1 m headroom: 86/86
- reachable from entrance: 86/86; unreachable: none

Example routes (BFS):

- **nave**: stairs_south_lower -> stairs_south_upper -> cathedral_steps -> portal
- **ambulatory**: stairs_south_lower -> stairs_south_upper -> cathedral_steps -> portal -> choir_ambulatory_W
- **tower_SW**: stairs_south_lower -> stairs_south_upper -> cathedral_steps -> portal -> nave_tower_SW
- **yard_E**: stairs_south_lower -> stairs_south_upper -> gate_yard_E
- **W3_F2_back**: stairs_south_lower -> stairs_south_upper -> open_plaza_street_W -> W3_door -> W3_stair_01 -> W3_stair_12 -> W3_F2_part
- **NE_F1_back**: stairs_south_lower -> stairs_south_upper -> open_plaza_street_E -> open_street_E_north_E -> NE_door -> NE_stair_01 -> NE_F1_part

| stair | from -> to | steps | riser range (measured) | min tread | min headroom | ok |
|---|---|---|---|---|---|---|
| stairs_south_lower | approach -> landing | 13 | [161.5, 161.5] mm | 375 mm | 30.0 m | yes |
| stairs_south_upper | landing -> plaza | 13 | [161.5, 161.5] mm | 338 mm | 30.0 m | yes |
| cathedral_steps | plaza -> parvis | 15 | [160.0, 160.0] mm | 300 mm | 30.0 m | yes |
| W0_stair_01 | W0_F0_front -> W0_F1_front | 20 | [160.0, 160.0] mm | 270 mm | 3.11 m | yes |
| W0_stair_12 | W0_F1_front -> W0_F2_front | 20 | [160.0, 160.0] mm | 270 mm | 5.93 m | yes |
| W1_stair_01 | W1_F0_front -> W1_F1_front | 20 | [160.0, 160.0] mm | 270 mm | 3.11 m | yes |
| W1_stair_12 | W1_F1_front -> W1_F2_front | 20 | [160.0, 160.0] mm | 270 mm | 3.69 m | yes |
| W2_stair_01 | W2_F0_front -> W2_F1_front | 20 | [160.0, 160.0] mm | 270 mm | 3.11 m | yes |
| W2_stair_12 | W2_F1_front -> W2_F2_front | 20 | [160.0, 160.0] mm | 270 mm | 6.99 m | yes |
| W3_stair_01 | W3_F0_front -> W3_F1_front | 20 | [160.0, 160.0] mm | 270 mm | 3.11 m | yes |
| W3_stair_12 | W3_F1_front -> W3_F2_front | 20 | [160.0, 160.0] mm | 270 mm | 6.07 m | yes |
| W4_stair_01 | W4_F0_front -> W4_F1_front | 20 | [160.0, 160.0] mm | 270 mm | 3.11 m | yes |
| W4_stair_12 | W4_F1_front -> W4_F2_front | 20 | [160.0, 160.0] mm | 270 mm | 4.12 m | yes |
| E0_stair_01 | E0_F0_front -> E0_F1_front | 20 | [160.0, 160.0] mm | 270 mm | 3.11 m | yes |
| E0_stair_12 | E0_F1_front -> E0_F2_front | 20 | [160.0, 160.0] mm | 270 mm | 5.53 m | yes |
| E1_stair_01 | E1_F0_front -> E1_F1_front | 20 | [160.0, 160.0] mm | 270 mm | 3.11 m | yes |
| E1_stair_12 | E1_F1_front -> E1_F2_front | 20 | [160.0, 160.0] mm | 270 mm | 5.19 m | yes |
| E2_stair_01 | E2_F0_front -> E2_F1_front | 20 | [160.0, 160.0] mm | 270 mm | 3.11 m | yes |
| E2_stair_12 | E2_F1_front -> E2_F2_front | 20 | [160.0, 160.0] mm | 270 mm | 5.14 m | yes |
| E3_stair_01 | E3_F0_front -> E3_F1_front | 20 | [160.0, 160.0] mm | 270 mm | 3.11 m | yes |
| E3_stair_12 | E3_F1_front -> E3_F2_front | 20 | [160.0, 160.0] mm | 270 mm | 5.04 m | yes |
| E4_stair_01 | E4_F0_front -> E4_F1_front | 20 | [160.0, 160.0] mm | 270 mm | 3.11 m | yes |
| E4_stair_12 | E4_F1_front -> E4_F2_front | 20 | [160.0, 160.0] mm | 270 mm | 3.62 m | yes |
| NW_stair_01 | NW_F0_front -> NW_F1_front | 20 | [160.0, 160.0] mm | 270 mm | 4.58 m | yes |
| NE_stair_01 | NE_F0_front -> NE_F1_front | 20 | [160.0, 160.0] mm | 270 mm | 7.61 m | yes |

| opening | type | a -> b | clear | pierces wall | ok |
|---|---|---|---|---|---|
| portal | ext_door | parvis -> nave | True | True | yes |
| nave_tower_SW | door | nave -> tower_SW | True | True | yes |
| arcade_aisle_W_1 | opening | nave -> aisle_W | True | True | yes |
| arcade_aisle_W_2 | opening | nave -> aisle_W | True | True | yes |
| arcade_aisle_W_3 | opening | nave -> aisle_W | True | True | yes |
| arcade_aisle_W_4 | opening | nave -> aisle_W | True | True | yes |
| choir_ambulatory_W | opening | nave -> ambulatory | True | True | yes |
| aisle_W_ambulatory | opening | aisle_W -> ambulatory | True | None | yes |
| tower_SW_aisle_W | door | tower_SW -> aisle_W | True | True | yes |
| nave_tower_SE | door | nave -> tower_SE | True | True | yes |
| arcade_aisle_E_1 | opening | nave -> aisle_E | True | True | yes |
| arcade_aisle_E_2 | opening | nave -> aisle_E | True | True | yes |
| arcade_aisle_E_3 | opening | nave -> aisle_E | True | True | yes |
| arcade_aisle_E_4 | opening | nave -> aisle_E | True | True | yes |
| choir_ambulatory_E | opening | nave -> ambulatory | True | True | yes |
| aisle_E_ambulatory | opening | aisle_E -> ambulatory | True | None | yes |
| tower_SE_aisle_E | door | tower_SE -> aisle_E | True | True | yes |
| apse_arcade_0 | opening | nave -> ambulatory | True | True | yes |
| apse_arcade_1 | opening | nave -> ambulatory | True | True | yes |
| apse_arcade_2 | opening | nave -> ambulatory | True | True | yes |
| apse_arcade_3 | opening | nave -> ambulatory | True | True | yes |
| apse_arcade_4 | opening | nave -> ambulatory | True | True | yes |
| apse_arcade_5 | opening | nave -> ambulatory | True | True | yes |
| gate_yard_W | gate | plaza -> yard_W | True | True | yes |
| gate_yard_E | gate | plaza -> yard_E | True | True | yes |
| W0_F0_part | door | W0_F0_front -> W0_F0_back | True | True | yes |
| W0_F1_part | door | W0_F1_front -> W0_F1_back | True | True | yes |
| W0_F2_part | door | W0_F2_front -> W0_F2_back | True | True | yes |
| W0_door | ext_door | street_W -> W0_F0_front | True | True | yes |
| W1_F0_part | door | W1_F0_front -> W1_F0_back | True | True | yes |
| W1_F1_part | door | W1_F1_front -> W1_F1_back | True | True | yes |
| W1_F2_part | door | W1_F2_front -> W1_F2_back | True | True | yes |
| W1_door | ext_door | street_W -> W1_F0_front | True | True | yes |
| W2_F0_part | door | W2_F0_front -> W2_F0_back | True | True | yes |
| W2_F1_part | door | W2_F1_front -> W2_F1_back | True | True | yes |
| W2_F2_part | door | W2_F2_front -> W2_F2_back | True | True | yes |
| W2_door | ext_door | street_W -> W2_F0_front | True | True | yes |
| W3_F0_part | door | W3_F0_front -> W3_F0_back | True | True | yes |
| W3_F1_part | door | W3_F1_front -> W3_F1_back | True | True | yes |
| W3_F2_part | door | W3_F2_front -> W3_F2_back | True | True | yes |
| W3_door | ext_door | street_W -> W3_F0_front | True | True | yes |
| W4_F0_part | door | W4_F0_front -> W4_F0_back | True | True | yes |
| W4_F1_part | door | W4_F1_front -> W4_F1_back | True | True | yes |
| W4_F2_part | door | W4_F2_front -> W4_F2_back | True | True | yes |
| W4_door | ext_door | street_W -> W4_F0_front | True | True | yes |
| E0_F0_part | door | E0_F0_front -> E0_F0_back | True | True | yes |
| E0_F1_part | door | E0_F1_front -> E0_F1_back | True | True | yes |
| E0_F2_part | door | E0_F2_front -> E0_F2_back | True | True | yes |
| E0_door | ext_door | street_E -> E0_F0_front | True | True | yes |
| E1_F0_part | door | E1_F0_front -> E1_F0_back | True | True | yes |
| E1_F1_part | door | E1_F1_front -> E1_F1_back | True | True | yes |
| E1_F2_part | door | E1_F2_front -> E1_F2_back | True | True | yes |
| E1_door | ext_door | street_E -> E1_F0_front | True | True | yes |
| E2_F0_part | door | E2_F0_front -> E2_F0_back | True | True | yes |
| E2_F1_part | door | E2_F1_front -> E2_F1_back | True | True | yes |
| E2_F2_part | door | E2_F2_front -> E2_F2_back | True | True | yes |
| E2_door | ext_door | street_E -> E2_F0_front | True | True | yes |
| E3_F0_part | door | E3_F0_front -> E3_F0_back | True | True | yes |
| E3_F1_part | door | E3_F1_front -> E3_F1_back | True | True | yes |
| E3_F2_part | door | E3_F2_front -> E3_F2_back | True | True | yes |
| E3_door | ext_door | street_E -> E3_F0_front | True | True | yes |
| E4_F0_part | door | E4_F0_front -> E4_F0_back | True | True | yes |
| E4_F1_part | door | E4_F1_front -> E4_F1_back | True | True | yes |
| E4_F2_part | door | E4_F2_front -> E4_F2_back | True | True | yes |
| E4_door | ext_door | street_E -> E4_F0_front | True | True | yes |
| NW_F0_part | door | NW_F0_front -> NW_F0_back | True | True | yes |
| NW_F1_part | door | NW_F1_front -> NW_F1_back | True | True | yes |
| NW_door | ext_door | north_W -> NW_F0_front | True | True | yes |
| NE_F0_part | door | NE_F0_front -> NE_F0_back | True | True | yes |
| NE_F1_part | door | NE_F1_front -> NE_F1_back | True | True | yes |
| NE_door | ext_door | north_E -> NE_F0_front | True | True | yes |

## NEGATIVE TEST: door W3_door blocked by a solid box -> **FAIL**

Expected: FAIL. The check **caught it**. Newly unreachable spaces: ['W3_F0_back', 'W3_F0_front', 'W3_F1_back', 'W3_F1_front', 'W3_F2_back', 'W3_F2_front']

- openings ok: 70/71 (pierce their wall: 69/69)
- stair flights ok: 25/25
- outdoor links ok: 6/6
- spaces with floor + >= 2.1 m headroom: 86/86
- reachable from entrance: 80/86; unreachable: ['W3_F0_front', 'W3_F0_back', 'W3_F1_front', 'W3_F1_back', 'W3_F2_front', 'W3_F2_back']

Failures:

- door W3_door (street_W->W3_F0_front): clear=False pierces_wall=True blocked_at(h,lat,dist)=[2.25, 0.0, -0.25]
- unreachable from 'approach': ['W3_F0_front', 'W3_F0_back', 'W3_F1_front', 'W3_F1_back', 'W3_F2_front', 'W3_F2_back']

## NEGATIVE TEST 2: one tread of W3_stair_01 raised 60 mm -> **FAIL**

Expected: FAIL. The check **caught it**.

- openings ok: 71/71 (pierce their wall: 69/69)
- stair flights ok: 24/25
- outdoor links ok: 6/6
- spaces with floor + >= 2.1 m headroom: 86/86
- reachable from entrance: 82/86; unreachable: ['W3_F1_front', 'W3_F1_back', 'W3_F2_front', 'W3_F2_back']

Failures:

- stair W3_stair_01: ['tread missing/misplaced at [-25.325, -7.728, 5.16] (found 5.219999883174896)', 'riser range 100-220 mm outside 150-180', 'headroom 0.06 m < 2.1 m at step 5']
- unreachable from 'approach': ['W3_F1_front', 'W3_F1_back', 'W3_F2_front', 'W3_F2_back']
