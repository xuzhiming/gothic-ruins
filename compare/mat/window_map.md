# M11 window map (gap #11 "十字形窗户" / cross windows)

Refs: `ref/front_south.png`, `ref/left_west.png`, `ref/isometric.png` only. Crops in `compare/mat/window_ref/`:
`fs_E4_windows.png` (front_south 585,250,710,400), `fs_E4_window_zoom.png` (610,265,690,330), `fs_W4_windows.png` (40,250,150,390),
`lw_row_windows.png` (left_west 190,290,330,370), `lw_row2_windows.png` (370,290,500,370), `lw_row_window_zoom.png` (195,295,255,340),
`iso_E_row.png` (iso 520,560,700,720), `iso_W_row.png` (255,150,420,330), `fs_cathedral_lancets.png` (300,180,450,360).

| item | reference observation | model (params.json houses.windows) |
|---|---|---|
| which buildings | every house window, all storeys, brick and half-timber houses alike, attic / dormer windows too; cathedral lancets are Gothic tracery (unchanged) | all house wall windows (`windows_row`, cross=True), dormer + attic + street-gable panes (`geom.cross_panel`); cathedral untouched |
| type | Kreuzstock: 1 vertical mullion + 1 horizontal transom -> 4 lights, upper lights shorter | mullion at centre, transom `transom_ratio` 0.40 of the light height below the head |
| proportions | upright, w:h ~ 0.75-0.8 (about 0.95 x 1.25 m); ground floor similar, some arched (round) heads | unchanged opening sizes (win_w x 1.25-1.35 m, round-head gf windows: transom at the spring, mullion into the arch) |
| frame | light grey-cream casing ~0.1 m round the opening, slightly proud; bars ~0.06-0.08 m | casing `frame_w` 0.10 m, proud `frame_proud` 0.03 m; sash `sash_w` 0.045 m; bars `mullion_w` 0.07 m, depth `frame_depth` 0.05 m |
| frame colour | pale weathered paint/stone, p85 of the window crop (180,165,155) | new material `wframe`: pale painted oak (178,172,161) with flaking paint to grey wood (118,110,98), grime |
| glass | dark, (50,52,50), slightly inset | pane inset `glass_inset` 0.10 m from the outer face (was the wall centre) |
| sill | light projecting sill under each window | sill `sill_h` 0.07, proud `sill_proud` 0.08, `sill_ext` 0.05 each side |
| half-timber storeys | windows sit between posts on the sill rail; light frame inside the post opening | flush mode: casing as a light lining in the reveal + sill board (posts / rail frame it, nothing clashes with the timber) |
| outer silhouette faces | — | rear faces + exposed end walls use flush mode too, so nothing projects beyond the outline (silhouette IoU unchanged) |
| shutters / lintels | none visible | none |
| ruin | some panes broken / dark, frames still there | lost panes per the unchanged ruin stream (same RR draws); a lost pane loses a bar only with p = 0.35 x `lost_bar_frac` 0.35 (frames mostly intact) |
