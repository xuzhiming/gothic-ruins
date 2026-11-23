# 跳跃、飞行与玻璃运行时 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在现有轨道/步行预览上加入落地单跳和无碰撞飞行，并让网页按导出的透明度处理真正的玻璃，同时不改 GLB。

**Architecture:** 运动仍在 `web/main.js` 的胶囊步进里。飞行是 `walk` 的子状态，退出时做落点检测或回到 `lastSafe`。玻璃判断放在无 Three 依赖的 `web/surface.js`，加载网格时调用。测试用无头 Chrome 驱动真实页面和 `window.__walk`。

**Tech Stack:** three.js、three-mesh-bvh、静态 `web/`、Playwright、Python 3。

## Global Constraints

- 不修改 `web/building_opt.glb`、Blender 脚本或贴图。
- 下降键是 `C`。不用 `Ctrl`。
- 步行未起跳时保留 WASD、`ShiftLeft` 1.8 倍、助踏、自动门、`Tab`、Orbit、Start。
- 保留既有 `__walk` 方法：`ready`、`setMode`、`render`、`teleport`、`setYaw`、`setPitch`、`state`、`doorsNear`、`doorCount`、`raySegment`、`floorAt`。`state()` 可追加字段。
- `teleport` 必须关掉飞行且把脚放到给定坐标。
- 玻璃只认 `role === "glass"` 加上混合信号，不认名称。
- 真正玻璃留在 BVH。
- 没有最终透明 GLB 时不得宣称透视端到端通过。
- 部署清单必须带上 `web/surface.js`，否则 Pages 会在 import 处失败。

---

### Task 1: 浏览器测试先红

**Files:**
- Create: `walk/preview_controls_test.py`
- Test: `python3 walk/preview_controls_test.py --url http://localhost:8766/index.html`

- [x] **Step 1: 写测试**

测试在 `?test=1` 页面上覆盖：单跳且按住不连跳；头顶 0.22 m 封板挡住后脚的升高小于 0.30 m；飞行 WASD 与 Shift 加速、Space 升、C 降、水平 150 m 与脚高 -15..160 边界；墙内 `placeFly` 后退出，结果点 `blocked` 为假且离开墙点；`blur` 后松开前不再移动；焦点在 `#bOrbit` 时 `Space` 仍保持 walk 并起跳；F / Fly / Tab / Walk / Start 的 HUD 与按钮高亮；飞行靠近 portal 时门保持关闭，步行靠近才打开；`classifySurface` / `applyPolicy` 对盲窗、仅名称含 Glass、`alphaMode BLEND`、低 opacity 的断言；当前场景里非混合材质不被改成透明，`role === glass` 的网格不被排除出碰撞体，贴花仍是透明且 `renderOrder === 2`。若场景中 `realGlass` 数量为 0，结果写 `e2e_glass: pending_final_glb`，测试仍可因策略用例通过。截一张飞行 HUD 到 `walk/cp_fly_mode.png`。

- [x] **Step 2: 先跑，确认失败**

```bash
cd /workspace/web && python3 -m http.server 8766
python3 /workspace/walk/preview_controls_test.py --url http://localhost:8766/index.html
```

Expected: FAIL，因为 `__walk.classifySurface`、`setFly`、`sealOverhead` 尚不存在。

### Task 2: 玻璃策略

**Files:**
- Create: `web/surface.js`
- Modify: `web/main.js` 加载循环、`.github/workflows/deploy.yml`

- [x] **Step 3: 实现 `web/surface.js`**

导出 `isBlendedMaterial`、`hasGlassRole`、`isRealGlass`、`applySurfacePolicy`。

`isBlendedMaterial`：`alphaMode` 为 `OPAQUE` 或 `MASK` 则否；`BLEND` 则是；`opacity < 0.999` 则是；`transparent && depthWrite === false` 则是；其余否。

`hasGlassRole`：网格或材质 `userData.role === "glass"`。

`applySurfacePolicy`：跳过材质名 `/^Decal/i`。真正玻璃设 `transparent = true`、`depthWrite = false`，不改 `opacity`。网格 `castShadow = false`，`renderOrder` 至少为 1。返回是否处理了真正玻璃。

- [x] **Step 4: 接到加载循环**

在贴花分支之后对其他网格调用 `applySurfacePolicy`。不要把 `role === "glass"` 加入 `isDecor` / `isLeaf`。`deploy.yml` 增加 `cp web/surface.js dist/surface.js`。

### Task 3: 跳跃、飞行、落点、界面

**Files:**
- Modify: `web/main.js`、`web/index.html`、`README.md`

- [x] **Step 5: 运动**

常量：`JUMP = 4.1`，`FLY_SPEED = 8`，`FLY_BOOST = 2.5`，水平半径 150，脚高 -15 到 160。

`step` 在 `jumpQueued && onGround && jumpLock <= 0` 时把 `vel.y` 设为 `JUMP`、`onGround = false`、`jumpLock = 0.12`，并清掉队列。空中的队列直接丢掉。否则保持原来的贴地 / 重力公式。向上的 `dy` 用头顶射线夹紧，皮肤 0.02 m。`jumpLock` 期间强制 `onGround = false`。着地时记录 `lastSafe`。

`stepFly` 只做水平 WASD、Space 升、C 降、Shift 加速，然后夹紧边界。不调用 shapecast。

`sealOverhead(gap)` 在胶囊顶上方放一块水平盖板 BVH，`castFirst` 和推出都查询它。仅测试钩子使用，默认 `lid === null`。

`tryLanding`：胶囊无重叠且脚下 0.4 m 内有地面，或向下 120 m 射线命中且脚 ≥ -5、头顶 1.65 m 空、胶囊不重叠。失败用 `lastSafe`，再没有就 `toStart`。

门的 `near` 增加 `&& !fly`。

- [x] **Step 6: 输入与 HUD**

`F` 切换飞行。`Space` preventDefault；仅步行且非飞行、非 repeat 时排队起跳。飞行时 `Space` 只上升。`blur` / `visibilitychange` 清空 `keys` 和 `jumpQueued`。

按钮 `#bFly`。触控区 `#touch` 在 `(pointer: coarse)` 或 `max-width: 800px` 且处于步行时显示。`#tJump` 仅步行，`#tUp` / `#tDown` 仅飞行。

HUD 三套中文提示，含坐标。

`__walk` 追加 `setFly`、`placeFly`、`blocked`、`sealOverhead`、`classifySurface`、`applyPolicy`、`surfaces`、`glassSample`、`clearInput`。`state` 追加 `mode` 和 `fly`。`teleport` 先 `fly = false`。

- [x] **Step 7: 跑新测试直到通过，再跑步行回归**

```bash
python3 /workspace/walk/preview_controls_test.py --url http://localhost:8766/index.html?test=1
python3 /workspace/walk/walk_test.py --url http://localhost:8766/index.html
```

`preview_controls_test.py` 自己会加 `test=1`。Expected: 两者 PASS。飞行 HUD 截图存在。`e2e_glass` 在当前 GLB 上为 `pending_final_glb`。

- [x] **Step 8: 提交并开 PR，不合并、不部署**
