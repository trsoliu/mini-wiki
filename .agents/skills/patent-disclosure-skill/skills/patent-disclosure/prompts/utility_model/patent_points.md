# 实用新型 · 专利点挖掘（Step 3–4 特化）

**本文件仅用于专利类型 = 实用新型。** 发明请用 `../invention/patent_points_analyzer.md`；外观请用 `../design/patent_points.md`。

须先（或并行）完成 **`prompts/fill_structure_schema.md`**，产出案件目录 **`structure_schema.yaml`**（或 `.json`）及 **`figure_plan.yaml`**。挖点叙述须能回溯到 schema 的 `parts` / `relations` / `spatial`，并**主动联读** `figure_plan.relates_to`（勿只当入文清单）。

## Step 3：候选结构点

列出 **2–4 个**候选（结构向，勿默认「方法」）：

每个候选须说明：

| 项 | 要求 |
|----|------|
| 技术背景 | 现有安装/连接/布局方式及其痛点（拆装难、占孔、干涉、导热路径等） |
| 构造创新 | 对应哪些 **部件形状** / **连接关系** / **空间布局**（引用件号或 schema 字段） |
| 图证 | 支撑该候选的 `fig`（及 `relates_to` 链）；局部图优先作创新落点 |
| 与现有技术区别 | 可先据材料推断；查新后在第一章收紧 |
| 可实施性 | 普通技术人员能否按图制造/装配；`uncertain` 不得写成既定尺寸公差 |

若 `not_utility_model_signals` 非空（如纯算法、纯外观美感、方法步骤为主）：**反问**是否改发明或外观，勿硬写实用新型。

### 多图关系 → 挖点启发式（强制联读）

在已有 `figure_plan` 上，**按图际边联想**，勿把每张图当成孤立证据：

| `relates_to.relation` | 挖点用法 |
|----------------------|----------|
| `detail_of` | 局部相对总装多出的形状/咬合/缺口/筋位 → **优先候选**（常见真正可区分处） |
| `section_of` | 剖视暴露的通道、腔体、叠层、过盈面 → 布局/导热/走线类候选 |
| `exploded_of` | 爆炸图相对装配图多出的连接件、拆装顺序约束 → 连接类型/可拆装候选 |
| `alternate_view` / `same_state` | 另一视角才看清的相对位置 → 补全 `spatial`，避免漏布局点 |
| `sequence` | 步骤图差异 → 仅当体现**结构状态变化**（锁止/展开）才可作结构点；纯工艺步骤改发明分流 |

操作要点：

1. 对每条 `detail_of` / `section_of` / `exploded_of`：**对比**子图与父图的 `covers` 与可见 `relations`，写出「总装看不出、局部才暴露」的差异句。  
2. 同一连接若 `relations[].seen_in` 列出多图，跨图核对件号与 `type`/`where` 是否一致；矛盾进 `uncertain`，勿两边各写一套创新故事。  
3. 仅总装、无局部：仍可挖点，但须在候选中标明「缺局部图、细节置信度低」。  
4. **禁止**仅因某图 `score` 高就当创新点；高分图是入文优先，创新落点常在 `detail_of` 链上。

## Step 4：融合与选定

- 优先融合为**一套装置/结构**（同一装配关系上的多个形状特征），而非多篇方法专利。  
- 若多个候选分别落在同一 `relates_to` 链（如总装+卡扣局部）：**默认合成一篇**（总装定范围、局部定区分特征）。  
- 输出策略与发明相同：**默认一篇**最有价值的交底；用户要多篇时先列大纲再约定顺序。  
- 选定依据：构造可区分性、可实施、保护范围（装置书式）、查新后差异化、**图证链是否闭合**。

### 选定后须固化

1. 工作标题（「一种……装置/结构」）  
2. StructureSchema 定稿路径（workdir 或 knowledge）  
3. **`figure_plan.yaml`**（入文图按 score 排序；与 `parts`/`covers` 一致；支撑选定点的图际链 `relates_to` 已写；主题变了须重评）

下一步：**`Read`** 同目录 `disclosure_builder.md` + `template_reference.md`（Step 7）；查新走 `../prior_art_search.md` 且 **`--type utility_model`**。
