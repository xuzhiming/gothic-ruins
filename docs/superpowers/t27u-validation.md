# t27u 门口挡路木构 — 根因、修复与验收

日期：2026-11-23（America/New_York）
任务：用户报告「尾部两侧各有一间房子的门口有木头挡住了」（owner id pt27u）
范围：仅 `/workspace/gothic` 本地完整资产。未 clone，未改 `/workspace/gothic-repo`，未改网页 JS/HTML，未跑本机 headless 网页，未重渲 8 张高清图库，未经授权不推送/合并/部署。

## 1. 根因（先两端普查，不是猜测）

对 T24 已发布基线 `web/building_opt.glb`（4,885,908 字节，sha256 `25cae1f4b468c6999f29b5397609092d0d867cb07222b81bcadc8e9162d77319`）的当前 `building.blend` 做了全部 12 扇房屋外门的双向胶囊（R=0.30 m）与几何普查。

| 门 ID | 位置 | 结论 |
|---|---|---|
| NW_door | 北端转角，朝北路/广场，center `[-22.6, 37.075, 4.2]` | **挡住** |
| NE_door | 北端转角对称，center `[21.4, 37.075, 4.2]` | **挡住** |
| W0_door | 西排北端第一栋临街，center `[-20.525, 26.24, 4.2]` | **同样生成器缺陷，一并挡住** |
| W4_door / E4_door | 南端（尾部的另一种理解） | **本来就是通的** |
| W1–W3, E0–E3 | 其余排屋 | 通 |

用户说的「尾部两侧各有一间」对应 **北端对称的 NW 与 NE**，不是南端 W4/E4。W0 是普查出来的同一缺陷，不是猜测的「那两栋」，修复时一并处理。

挡住的对象是固定立面半木构水平梁，不是可开木门扇、不是门楣/楼板、不是废墟倒木：

- 对象：`House_NW_timber`、`House_NE_timber`、`House_W0_timber`，role=`solid`，材质 timber。
- 来源：`build.py` `timber_face()` 在 `z0+0.08`（踢脚梁）和 `z0+0.85`（腰梁）通长 `beam(..., 0.05, W-0.05)`，**没有在 `ops` 里的门洞处断开**。`z1-0.14` 的层间压梁在门洞上方，本来就不挡路。
- 只有地面层为 plaster 且 `timber` 非空的房子会在底层跑 `timber_face`：W0（grid+pentice）、NW（braced）、NE（grid）。其余排屋底层是 brick/stone 或 `timber=None`。
- 木梁凸出门外约 0.17–0.24 m，在 z≈4.36 与 5.0（脚踝/腰部）横贯整个 1.2 m 门宽。胶囊 96 次命中/门；门扇、楼板、门框、门楣被正确排除。
- 旧 `circulation_check` 只在墙平面打射线，会穿过凸出门外的梁，所以 T24 动线检查没抓到。
- 斜撑本来就会跳过有洞的开间；竖向门框柱也在。梁不是楼板承重构件（楼板另做），因此做最小断开，而不是改布局或关碰撞。

## 2. 修复（最小，保留废墟立面）

修改前备份：`/workspace/gothic-t27u-baseline/`（含 T24 blend/glb/opt glb/spaces/build.py/params，opt GLB 哈希已核对）。

代码：新增 `src/timber_rails.py` `timber_rail_segments()`，`timber_face` 水平梁按开口竖向范围断开，端点停在已有门框柱（`s ± w/2 ± 0.09`）。层间压梁若在洞口之上保持通长。不删除整片木材，不改 collision role，不改门扇、楼梯、护栏、窄巷。`params.json` 与 `src/geom.py` 哈希未变。

## 3. TDD

- `check/test_timber_rail_segments.py`：旧代码缺模块，RED；实现后 6/6 GREEN。
- `check/test_door_clearance.py`：在 **未改的 T24 blend** 上 RED，且只失败 W0/NW/NE（各 96 次 timber 胶囊命中 + 开口中部木梁射线），W4/E4 及其余 9 扇为 clear，门楣存在，86° 门扇开合不打到木材，楼梯记录在。修复重建后 12/12 clear，lintel ok，swing ok。
- 已挂入 `run_all.sh`（`SKIP_WEB_TEST=1` 资产流水线）。

## 4. 验收（资产流水线，无本机网页）

- 8 条窄巷导出净宽（含饰面）：raw min 1.406288 m，opt min **1.403997 m**（与 T24 相同）；后巷护栏 6 个 role=solid 包围盒未变。
- 动线：circulation PASS，98 空间可达；堵门与坏踏步负测都抓住。
- 全窗：365 槽，360 真窗 + 5 盲窗，235 透明，125 缺玻璃；映射 0 缺失/未知/漏窗；GLB Glass 5516 + Glass_blind 440；`test_all_windows.py` 8/8（断言未放宽）。
- M13：south 55、street 426，无误差；M10/M11/M12b 15mm 相关 houses 配置与 T24 备份一致。
- 材质配方：相对 T24 隔离集 0 变化。29 个隔离网格中仅 **House_NW_timber、House_NE_timber** 因本次门洞断梁而变（W0 timber 不在该隔离集）。
- 剪影相对私有参考，与 T24 巷后分数 **逐项相同**（不是声称相对巷前参考不变）：south IoU 0.8002，north 0.7967，west 0.7356，east 0.7434，top IoU 0.9136，footprint 0.824，outline 1.723 m。
- 玻璃 alpha BLEND、双面、alpha 0.24 在 raw/opt GLB 均保留。
- `web/main.js`、`web/index.html` 时间戳仍为 2026-11-19，未改。`/workspace/gothic-repo` 未动。
- 真 Cycles 站立视点前后对比（同一相机，24spp 640）：`t27u-evidence/renders/before_*`、`after_*`、`before_after_contact.png`。目视：NW/NE/W0 腰梁与踢脚梁已在门框柱处断开，门扇完整可见；周边斜撑、立柱、破损粉刷保留；W4/E4 南端对照仍是空拱门、无新增木构。

## 5. 产出哈希

| 文件 | 字节 | sha256 |
|---|---:|---|
| T24 `web/building_opt.glb`（修复前） | 4,885,908 | `25cae1f4b468c6999f29b5397609092d0d867cb07222b81bcadc8e9162d77319` |
| 新 `web/building_opt.glb` | 4,915,244 | `cf44409ef728e583f11cfbb2d8b57c8181bb93487b905eebfe28cbf4d1f482d9` |
| 新 `building.glb`（raw，不进交接包） | 37,722,384 | `282cf358cd72b82d9ef4ca0dd41a448ca843cfc9e64bfc92777c4324f6ec971a` |
| `spaces.json`（未变） | — | `78984baf9b80b1c19f532a60f658018892e70c067946710f33f280bf6470f78d` |

网页 WASD/玻璃/控制请原 cloud 做真实浏览器回归。本次不推送、不合并、不部署。
