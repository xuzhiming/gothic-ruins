# 步行跳跃、自由飞行与玻璃运行时

状态：用户已批准，按本说明实现。不改模型、贴图或 GLB。不在本分支合并或部署。

基准：`main` `418206e`。工作分支：`cursor/walk-jump-fly-fd67`。

## 范围

- 改 `web/main.js`、`web/surface.js`、`web/index.html`、`README.md` 的操作说明，以及部署拷贝清单里的 `web/surface.js`。
- 新增浏览器测试 `walk/preview_controls_test.py`。原 `walk/walk_test.py` 必须保持通过。
- 不改 `web/building_opt.glb`、`src/`、`build.py`、贴图。玻璃资产由另一条流水线导出；本分支只做网页运行时。

## 现有事实

- 模式只有 `orbit` 与 `walk`。WASD 水平移动 4 m/s，仅 `ShiftLeft` 为 1.8 倍。指针锁定后鼠标转向。`Tab` 在两种模式间切换。
- 胶囊半径 0.3 m、总高 1.6 m，眼高 1.6 m。重力 -20。着地时竖直速度被清零并向下贴地。子步不超过 10 ms。脚低于约 -30 m 回到入口。
- 助踏只在着地移动时抬升 3–35 cm。碰撞体含全部实体三角，排除门扇和 `role === "decor"`。`role === "glass"` 在碰撞体内。
- 自动门只在 `mode === "walk"`、水平距离 < 3.2 m、脚与门高差 < 2 m 时打开。
- `Space`、`F`、`C`、方向键未绑定。OrbitControls 未调用 `listenToKeyEvents`。`Ctrl` 仍被环绕控件监听，且 `Ctrl+W` 会关标签页，所以下降不用 Ctrl。
- 失焦不会清键。右上角按钮获得焦点时，浏览器会用 `Space` 点击该按钮。
- 手机只有环绕的一指旋转和双指缩放平移，步行没有摇杆。
- 当前遍历把每个网格 `castShadow` / `receiveShadow` 设为开（测试模式除外）。只有材质名匹配 `/^Decal/i` 的对象被设成透明、`depthWrite = false`、`renderOrder = 2`。
- three.js GLTFLoader 对 `alphaMode: BLEND` 会设置 `transparent = true` 且 `depthWrite = false`，但不会把 `alphaMode` 留在 `userData`。对象 extras 会进 `mesh.userData`，因此 `role` 可读。
- 现有 GLB 的玻璃仍是不透明材质。在最终 GLB 到达之前，不能宣称玻璃透视已端到端验证。

## 步行与跳跃

- 未起跳时，水平速度、贴地、助踏、胶囊推出和坠落重置与现在一致。
- `Space` 只在步行、着地、非连发时起跳。初速 4.1 m/s，顶点约 0.42 m。按住不连跳，空中再按无效。
- 起跳后约 0.12 s 内不再贴地，避免同一子步被判定重新着地。
- 向上位移先从头顶向上射线。撞到则停在命中点下方 2 cm，并清掉向上速度。随后仍用胶囊推出，避免低顶穿入楼板。

## 飞行

- `F` 或「Fly 飞行」切换。飞行是步行子状态：仍用指针锁定、头灯和准星。环绕逻辑不改。
- WASD 只做水平平移，不跟俯仰爬升。`Space` 上升，`C` 下降。`ShiftLeft` 或 `ShiftRight` 加速。基础 8 m/s，加速 20 m/s，竖直同速。
- 飞行不做胶囊碰撞、不施加重力、不助踏、不触发自动门，可以穿墙观察。
- 软边界：水平距原点 150 m，脚高度 -15 m 到 160 m。
- 进入飞行前保留最近一次着地且已推出的安全姿态。从未行走时用入口。
- 退出飞行时从当前位置向下找落点：胶囊能放下、头顶 1.65 m 无遮挡、脚不低于 -5 m，就把脚贴到该表面并清速度，不模拟下坠。不合格则恢复安全姿态。`Walk`、`Tab`、`Orbit` 都会先做这次退出。`Start` 直接回入口并关掉飞行。`__walk.teleport` 只关飞行，不改调用方指定的落点。

## 输入与界面

- HUD 写明环绕、漫游或飞行，以及对应按键。右上角 Orbit / Walk / Fly 互斥高亮。
- `Space` 始终 `preventDefault`，避免焦点在按钮上时误触发。
- `blur` 和页面隐藏时清空按键与起跳锁。
- 窄屏或粗指针时，步行显示「跳跃」，飞行显示「上升」「下降」。不新增摇杆。环绕触控手势不变。

## 玻璃

真正玻璃必须同时满足：

- 网格或材质的 `userData.role === "glass"`
- 以及导出的混合信号：`userData.alphaMode === "BLEND"`，或 `opacity < 0.999`，或（`transparent === true` 且 `depthWrite === false`）

`alphaMode` 为 `OPAQUE` 或 `MASK` 时不当作透视玻璃。只看名字里的 Glass / blind 不得打开透明。

对真正玻璃：保留导出的透明度与颜色，强制 `depthWrite = false`、`castShadow = false`、`renderOrder = 1`（不透明墙为 0，贴花为 2）。不把它从 BVH 移除。盲窗和不透明玻璃保持导出状态，包括阴影。

贴花路径保持原样。

## 验收

见 `docs/superpowers/plans/2026-11-23-walk-jump-fly.md`。最终 GLB 未入库时，玻璃项只验证策略函数和当前场景没有被名字误透明；透视外观列为待资产集成。
