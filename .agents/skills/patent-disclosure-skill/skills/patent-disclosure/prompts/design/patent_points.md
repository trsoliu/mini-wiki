# 外观设计 · 专利点挖掘（Step 3–4 特化）

**本文件仅用于专利类型 = 外观设计。** 发明 / 实用新型分见对应目录。

须先完成 **`prompts/fill_appearance_schema.md`**，产出案件目录 **`appearance_schema.yaml`**（或 `.json`）及 **`figure_plan.yaml`**。挖点须联读 **`figure_plan.relates_to`**（多视一致、局部造型落点），勿只列单张「好看」图。

## Step 3：候选外观点

列出 **1–3 个**候选（造型 / 图案 / 色彩或其结合）：

| 项 | 要求 |
|----|------|
| 产品名称与用途 | 与 schema `product_name` 一致 |
| 设计要点 | 对齐 `design_points`（看得见的形状、线条、比例、图案、配色） |
| 视图与图证 | 支撑要点的 `fig` 及 `relates_to`（立体↔正交↔局部） |
| 与在先外观差异 | 可先据材料推断；查新后在「与在先差异」节收紧 |

若 `not_design_signals` 非空（内部构造、电路、受力分析、工艺步骤等）：**反问**是否改实用新型/发明，**禁止**把功能构造写成外观要点。

### 多视关系 → 挖点启发式（强制联读）

| `relates_to.relation` | 挖点用法 |
|----------------------|----------|
| `alternate_view` / `same_state` | 多视交叉核对轮廓、开口、装饰位置；**仅在多视稳定出现**的特征才升为设计要点 |
| `detail_of` | 局部相对整体多出的可见造型（倒角、筋线、纹理、接口造型）→ 可作**设计要点候选**；须仍属外观、非内部构造 |
| `sequence` | 使用状态变化若带来**可见形态**差异，可单列「变化状态」要点；勿写成操作方法 |

操作要点：

1. 立体图给出整体印象；正交/`alternate_view` 用于确认比例与对称；`detail_of` 用于收紧「究竟新在哪一处可见细节」。  
2. 某特征只在一张图出现、其它关联视图对不上 → 写入 `uncertain` 或降权，勿当确定要点。  
3. 场景/`reference` 图不参与挖点主证据（除非清单明确入文且能裁出产品外形）。

## Step 4：选定

- 外观通常 **一篇产品一件申请** 口径；多造型需用户确认是否分案。  
- 选定依据：视觉可区分性、视图充分、与查新差异、不越界写结构功能、**多视图证一致**。

### 选定后须固化

1. 产品名称（交底文头）  
2. AppearanceSchema 定稿路径  
3. **`figure_plan.yaml`**（入文视图清单；先 `product_form` 再按 `claimed_faces` 定正投影，立体宜加立体图，**非默认六视**；`covers` / 图题用官方全称；支撑要点的多视 `relates_to` 已写；场景图默认不入文除非明确启用）

成文前必做：`references/design_view_cnipa.md` + `prompts/image_gen.md` + `prompts/design_lineart_assist.md`（不问用户；已有线稿须过 4.2 才入文，否则重画）。干净实拍与线稿都写入 md 与 Word；CAD/实拍不得标成线稿；透视棚拍不得当合格正投影。

下一步：**`Read`** 同目录 `disclosure_builder.md` + `template_reference.md`；查新 **`--type design`**。
