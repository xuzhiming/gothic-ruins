# t22 全建筑窗口审计与最小修复

范围：仅本机资产。未操作发布副本、Git、浏览器、线上站点或网页 JS/HTML。生产据报为 8bca20e，不以本地旧 web 推断生产。

## 逐一覆盖

- 13个建筑ID；360个真窗槽位（242主层、80尖拱、18阁楼/山墙、19老虎窗、1玫瑰窗）。另列5个装饰盲窗/门楣和4个实心尖顶 lucarne 装饰。
- 235个槽位有现存透明玻璃，125个整窗玻璃因原废墟规则缺失；玫瑰窗另有24片侧/扇区中的14片现存、10片缺失。不补造玻璃。
- 所有4214个生成玻璃/盲窗面实例均匹配保存的Blend，0个遗漏面、0个未映射玻璃面。4204个唯一面哈希与10个原玫瑰窗相邻扇区共享侧面重复相符。
- 每窗8×8候选孔内采样，共22682个有效采样点；近墙内外双向不透明结构/自身玻璃射线、额外4m深处内外结构、透明贴花层都有逐窗记录。原始GLB与实际Meshopt优化GLB均离线解码后对每个点双向验玻璃，命中存在性差异0。没有仅凭Glass材质名称判断通视。

|建筑|真窗|有透明玻璃|整窗缺玻璃|不透明真玻璃|部分/全部结构遮挡*|其中全挡|
|---|---:|---:|---:|---:|---:|---:|
|Cathedral|81|33|48|0|12|2|
|E0|25|20|5|0|1|0|
|E1|18|16|2|0|0|0|
|E2|14|10|4|0|3|0|
|E3|17|11|6|0|0|0|
|E4|31|20|11|0|1|1|
|NE|25|20|5|0|3|2|
|NW|25|21|4|0|2|1|
|W0|31|23|8|0|1|0|
|W1|19|13|6|0|6|0|
|W2|20|17|3|0|2|0|
|W3|23|13|10|0|0|0|
|W4|31|18|13|0|0|0|

*遮挡是重叠标记，含原缺玻璃槽位，不可与235/125相加。方位/楼层（含零窗方位）/组件和精确法向及方位角逐项见清单。

## 根因与精确改动

原先所有235处现存真窗的材质已经透明，本轮没有制造材质改动。找出并只修复两处遗漏：
1. NW朝南主面老虎窗 `NW/dormer/dormer/attic/S/1`：之前屋顶开口从玻璃后方开始；挑檐/出挑使主屋面唇边侵入玻璃下缘。在原窗宽1m、原窗玻璃上下缘之间，局部清掉原主屋顶喉口；不移动窗框、外形或屋顶布局。近孔结构通视采样从54/64提高至64/64。
2. 玫瑰窗：墙洞已开，但旧墙裂纹透明贴片仍跨洞，3个孔内采样命中。仅沿同一96边形窗洞裁切刚生成的立面墙贴片，孔内旧墙贴片命中3→0；墙外贴片UV及原色保留。

最小修改文件：build.py、src/window_apertures.py；check/test_aperture_geometry.py增加保域回归；新增全量追踪/射线/GLB解码/汇总/范围测试。docs/glass-web-contract.md明确旧本地viewer不能代表生产。params、ruin_streams、geom、make_textures、face_materials均不改。
实际181个网格中179个含顶点/面/UV/材质槽完全相同；只变 House_NW_slate（439→444面）及 Decal_decal_crack（116→131面）。全部玻璃、窗框/花饰、M13墙体与1.5cm薄抹灰、烟囱、木构、家具、盲窗、室内布局和碰撞玻璃保持。所有纹理逐文件哈希不变；spaces.json、params.json逐字节不变。

## 保留的遮挡与真正的决策项

31个真窗槽位在近结构带有部分/全部实体遮挡，全部明确归因，而不是不透明玻璃：原塔楼/中殿共墙、飞扶壁、木构/塔楼楼板、W1原下垂屋檐、原烟囱和角屋原废墟端墙。不能为了“透视”删除这些结构。
其中6个槽位近带全挡：
- `Cathedral/lancet/tower_SE_stage/tier_1/W/1`；现存透明玻璃；Cathedral_stone
- `Cathedral/lancet/tower_SE_stage/tier_1/W/2`；原缺玻璃；Cathedral_stone
- `E4/dormer/dormer/attic/E/1`；现存透明玻璃；Chimneys_brick_red
- `NW/main/end/F0/W/1`；现存透明玻璃；House_NW_rubble
- `NE/main/end/F0/E/1`；现存透明玻璃；House_NE_rubble
- `NE/main/end/F0/E/2`；原缺玻璃；House_NE_rubble

这些若也要“无障碍向外看”，需要用户决定是否改变共墙/烟囱/废墟等结构；本轮保持。5个装饰盲龛/门楣仍不透明实墙，不擅自打通；4个尖顶lucarne是实心石/瓦装饰，从未建模玻璃或窗洞，也单列待决定。室内只保留原有楼板/隔墙/楼梯与教堂原布置，不新增家具、房间或灯光。远处实体或背光会使透明窗看暗，不把它误报材质不透明。

## 材质与网页交接

`Glass`（严格全名匹配，绝非 startsWith("Glass")）：Blender5.3 BLENDED，alpha .24、metallic0、roughness .09、IOR1.5、transmission0，浅灰绿色原透明贴图；GLB alphaMode BLEND、doubleSided true、alpha .24。薄片alpha近似，不是物理折射；原厚度与双层玫瑰窗几何不变。`Glass_blind`继续OPAQUE。
网页建议保留导入颜色/透明度、普通depthTest，Glass独有depthWrite=false/castShadow=false，评估receiveShadow=false；保持玻璃碰撞；不要全局强设renderOrder或隐藏背墙。透明网格与贴花排序/投影须由父任务/云端针对真实生产核验。

## 测试与指标

- 先观察冻结原资产两项回归FAIL，再修复；最终全窗口8项PASS，裁孔单元4项PASS，范围1项PASS，M13选择器3项PASS。
- run_all.sh的资产阶段1–6及8串行重跑，最新 logs/run_all_t22_local.log exit0；第7阶段浏览器/WASD遵从禁止浏览器明确NOT RUN。不是完整端到端PASS，不复用旧WASD结果。
- 动线检查PASS，reachable=86；堵门负测caught=True；错误踏步负测caught=True。
- IoU S .8076、N .8116、W .7404、E .7477、top .9420，均与本轮前完全一致；footprint .8521、outline1.186m不变。
- 四向skyline完整数组完全一致；MAE 4.580/4.215/6.316/6.168m。
- 原始/优化GLB窗玻璃5516三角、盲窗440三角均保留，逐窗原始/优化GLB双向射线与Blend匹配。

## 产物与真实图像

- 优化GLB：web/building_opt.glb，4917968字节，SHA256 `abb11f6ac7d264f973390fcab03f9ae5b7ab67a9f5ef4d6f298385b008ba2eaa`。
- 原始GLB：building.glb，37782588字节，仅本机，不进入交接包。完整场景：building.blend。
- 全量机器证据：window-audit/windows_all.json.gz、windows_all.csv、summary.json、decorative_ornaments.json。
- 比对、保护范围、材质和测试证据：window-audit/validation_summary.json、identity.json、regression_{red_final,green}.log、scope_{red,green}.log，logs/run_all_t22_local.log。
- 真Cycles 640×480/16samples同机位before_/after_：nw_dormer_out、nw_dormer_in、rose_out、rose_in，共8张，window-audit/*.png。均由Blender直接渲染，Read目视；无P图。额外before_e2_chimney_out、before_ne_rubble_out、before_w1_sagged_eave_out、before_tower_shared_wall_out用于保留遮挡说明。
- E1/W3中间试裁被范围回归发现不必要，最终恢复原网格字节级身份；其临时试验图只在window-audit/iterations/，不得作为最终图。
- 最新资产前备份：/workspace/gothic-before-full-window-audit-20261123-0628；更早M13备份：/workspace/gothic-M13-before-glass-20261123-0134。
- 原高清网页图库未重渲，web中仅building_opt.glb内容改变。

## 未完成

无推送/部署，也未访问发布副本。浏览器、生产three.js透明排序/阴影、内外近远视角及最新模型的WASD/飞行碰撞须父任务/云端协调验证。结构遮挡和盲窗/尖顶装饰是否改变，须用户另行确认。

## 独立交接包复现
仅复制交接包到 window-repro-t22，不带原Blend、私有参考或既有tex；从make_textures起完整重建并优化。重建GLB与最终优化GLB的4917968字节逐字节cmp一致，SHA256相同；见window-audit/reproducibility.json。
