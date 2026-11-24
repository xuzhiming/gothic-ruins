# t27u 门口挡路木构 — 范围收窄后的修复与验收

日期：2026-11-23（America/New_York）
任务：用户报告「尾部两侧各有一间房子的门口有木头挡住了」（pt27u），后续按 PR4 review 把修复严格限制在 3 扇门。
范围：仅 `/workspace/gothic` 本地完整场景重建。未 clone，未改 `/workspace/gothic-repo`，未改网页 JS/HTML，未跑本机浏览器，未重渲 8 张高清图库，未经授权不推送/合并/部署。

PR4 head `44b8675202be06c85a142de1a0e517a1b5e6a017` 上的 opt GLB `cf44409ef728e583f11cfbb2d8b57c8181bb93487b905eebfe28cbf4d1f482d9` **不能作为最终资产**：那一版对全部 `ops` 切水平梁，窗洞也被断开。云端源码和 GLB 未再改。本机已按正确门语义重建，本报告与新包用于更新同一 PR4。

## 1. 根因（两端普查，不是猜测）

对照 T24 已发布基线 `web/building_opt.glb`（4,885,908 字节，sha256 `25cae1f4b468c6999f29b5397609092d0d867cb07222b81bcadc8e9162d77319`）普查全部 12 扇外门。

- 用户说的「尾部两侧各有一间」是北端对称的 **NW_door**、**NE_door**。
- 南端 W4/E4 本来就通。
- 同一生成器缺陷还挡住西排北端 **W0_door**，一并修。

挡住的是 `timber_face()` 通长踢脚梁（`z0+0.08`）和腰梁（`z0+0.85`），对象 `House_NW_timber` / `House_NE_timber` / `House_W0_timber`，role=solid。层间压梁在洞口上方，本来不挡路。只有底层 plaster 且 timber 非空的房子会在地面层画这些梁。旧 circulation 只在墙平面打射线，会漏掉凸出门外的梁。不是可开木门扇、门楣、楼板或废墟倒木，也不是承重构件。

## 2. 第一次修复过宽（PR4 review，于此纠正）

第一版 `timber_rail_segments` 对**全部**与梁竖向重叠的 `ops` 切梁。不能用 `kind`（flat/round 门窗都有）区分。上层窗默认 `sill=0.9`，与腰梁（中心 `z0+0.85`、半高 0.08，占 0.77–0.93）重叠，于是窗边也被切断。

对 T24 基线做**全场** timber 网格审计（64 个 timber 网格，不是 29 个隔离集）：实际被改了 **9** 个 `House_*_timber`：NW/NE/W0（该改）以及 **W1/W2/W3/E0/E1/E2**（窗边误伤）。E3/E4/W4 及主教堂/门扇/废墟木构未变。先前报告写「29 隔离网格只变 NW/NE」是不完整的：W0 不在该隔离集，另外 6 栋的上层木梁也变了。

T24 基线三角数已先在 `gothic-t27u-baseline/building.blend` 上核实，与给定表一致：W1 2647、W2 2522、W3 2514、E0 2906、E1 3184、E2 2159。

## 3. 正确修复（只修 3 门，窗梁恢复原状）

- 地面层临街门 ops 增加 `opening: "door"`；`windows_row` 的窗不标。
- `timber_rail_segments` **只**在 `opening == "door"` 处断开，端点仍停在已有门框柱（`s ± w/2 ± 0.09`）。低窗（甚至 `sill=0` 盖住腰梁）也不切。
- 门上压梁保持整段。
- 立柱 / 斜撑 / 门框柱循环未改。窗上穿梁是既有立面风格，本次不改。
- `wall` / `_skin` / `wall_decals` / `skin_holes` 只用 `s,w,h,sill,kind,k` 等已知键，额外 `opening` 字段被忽略，兼容。
- `params.json` 与 `src/geom.py` 哈希未变。

修改前备份仍在 `/workspace/gothic-t27u-baseline/`。

## 4. TDD

- `check/test_timber_rail_segments.py`（9 项）：低窗 sill=0 覆盖腰梁高度仍不切；只有窗、无门时两水平梁整段；无 `opening` 的 flat/round 开口不切；显式门在门框柱停；门上压梁整段。过宽实现上前 3 项 RED，收窄后 9/9 GREEN。
- `check/test_door_clearance.py`：旧 T24 blend 上只红 W0/NW/NE；重建后 12/12 clear，门楣在，86° 开合不打到木材。
- `check/test_timber_scope.py`：先核对基线 6 栋三角数，再对全部 timber 网格做哈希对比（不以计数代替几何）。过宽资产 RED（6 栋 restore_bad）。收窄重建后 GREEN：只变 W0/NW/NE，6 栋哈希与三角数回到基线。

已挂入 `run_all.sh`（基线 blend 存在时跑 scope）。

## 5. 验收（`SKIP_WEB_TEST=1 FAST=1`，无本机网页）

- 全场 timber：64 对 64。仅 `House_W0_timber`（2818→2842）、`House_NW_timber`（2818→2842）、`House_NE_timber`（3015→3039）改变；W1 2647、W2 2522、W3 2514、E0 2906、E1 3184、E2 2159 与基线网格哈希一致。
- 门：12/12 双向胶囊净空，lintel ok，86° 开合不打木材；楼梯记录在。circulation PASS，98 空间可达；堵门与坏踏步负测抓住。
- 8 巷 opt 导出净宽（含饰面）**1.403997 m**（与 T24 相同）；raw min 1.406288 m；后巷 6 道 role=solid 护栏包围盒未变。
- 全窗：365=360 真窗+5 盲窗，235 透明，125 缺玻璃；映射 0 缺失/未知/漏窗；GLB Glass 5516 + Glass_blind 440；`test_all_windows.py` 8/8（断言未放宽）。
- M13 south 55 / street 426，无误差；M10/11/M12b 15mm 配置与备份一致。29 隔离网格中仅故意改了 NW/NE timber（W0 不在该集）；材质配方 0 变化。以全场 timber 审计为准。
- 剪影与 T24 巷后分数逐项相同：south 0.8002，north 0.7967，west 0.7356，east 0.7434，top IoU 0.9136，footprint 0.824，outline 1.723 m。
- `spaces.json` 未变。`web/main.js` / `index.html` 时间戳仍为 2026-11-19。`/workspace/gothic-repo` 未动。
- 真 Cycles 站立视点沿用原相机（T24 基线 before + 本版 after）：`t27u-evidence/renders/before_*`、`after_*`、`before_after_contact.png`。已 Read 确认：NW/NE/W0 腰梁与踢脚梁在门框柱处断开，门扇完整可见，两侧立面梁保留；W4/E4 仍是空拱门。6 栋窗梁恢复由全场网格哈希证明（那些是上层腰梁，不在这组地面门特写里）。

## 6. 新 GLB（取代 cf44409…）

| 文件 | 字节 | sha256 |
|---|---:|---|
| T24 `web/building_opt.glb`（修复前） | 4,885,908 | `25cae1f4b468c6999f29b5397609092d0d867cb07222b81bcadc8e9162d77319` |
| 过宽版（作废，PR4 旧 head） | 4,915,244 | `cf44409ef728e583f11cfbb2d8b57c8181bb93487b905eebfe28cbf4d1f482d9` |
| **新** `web/building_opt.glb` | **4,887,336** | `242aaf2a7e5e1d1b4400b0b5f19219a3253ab67d02b70c7b7718f323c08d6c9b` |
| **新** `building.glb`（raw，不进交接包） | **37,625,784** | `6ececb4649ec1eca5d0c62423e7fed55418021bf3082a17f4d3c8d9761e553d5` |
| `spaces.json`（未变） | — | `78984baf9b80b1c19f532a60f658018892e70c067946710f33f280bf6470f78d` |

独立复现（本机完整 Blender 资产，勿 clone）：在 `/workspace/gothic` 对已备份的 T24 基线应用上述源码（`build.py` 门 ops 标 `opening:"door"`，`src/timber_rails.py` 只在该标记处断梁），`SKIP_WEB_TEST=1 FAST=1 ./run_all.sh`。对照基线 blend：`/workspace/gothic-t27u-baseline/building.blend`。

网页 WASD/玻璃/控制请原 cloud 用本包更新同一 PR4 后做真实浏览器回归。本次不推送、不合并、不部署。
