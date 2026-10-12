# Schema 合同说明

| 文件 | 用途 | 交底怎么用 |
|------|------|------------|
| `structure.schema.yaml` | 形状/构造 | `prompts/utility_model/`；填表见 `fill_structure_schema.md` |
| `appearance.schema.yaml` | 外观造型 | `prompts/design/`；填表见 `fill_appearance_schema.md` |
| `figure_plan.schema.yaml` | 附图选用、排序与图际关联（`relates_to`） | 实用/外观成文只嵌 `use_in_disclosure: true` |
| `formula_plan.schema.yaml` | 发明公式提纲（`origin` + `source_kind` / `verified` + 可选起草） | 含公式时先写 `formula_plan.yaml`；材料式保真，无原文才用 `references/formulas/` |
| `design_lineart_brief.schema.yaml` | 外观线稿描述（成文前必做） | 不问用户；已有合格线稿或大模型生成；CAD 不得当线稿 |
| `structure_lineart_brief.schema.yaml` | 实用结构线稿描述（成文前必做） | 不问用户；轮廓与序号分层；禁止自创件号；CAD 不入文 |
| `structure_lineart_compose.schema.yaml` | 实用结构线稿按件拼装 | 每件一个子 SVG，总图相对引用；粒度止于件号；crop / 单件图 / 占位框 |
| `scorecard.schema.yaml` | 1+N 立项后弱校验评分表 | 默认表 `references/scorecards/gbt42748_fence.yaml`，可整表替换 |
| `decompose.schema.yaml` | 技术分解 | `outputs/{案}/fence/decompose.yaml` |
| `design_around.schema.yaml` | 突围路径（全面覆盖/等同列表） | `outputs/{案}/fence/design_around.yaml` |
| `matrix.schema.yaml` | 技术功效矩阵 | `outputs/{案}/fence/matrix.yaml` |
| `family_plan.schema.yaml` | 保护型 1+N 族树 | `outputs/{案}/fence/family.yaml`；说明稿 `专利布局.md` 由模型按 `prompts/fence/plan.md` 直写，「立项校验」章按 `prompts/fence/score.md` 回写 |

填写指令：`prompts/fill_structure_schema.md`、`fill_appearance_schema.md`（填表末步写出 **`figure_plan.yaml`**，含跨图核对与 `relates_to`）；线稿合同 **`prompts/image_gen.md`**；外观视图口径 **`references/design_view_cnipa.md`**（审查指南 4.2；交底打分与申请核查同一清单）；外观检查 **`tools/check_design_views.py`**；外观见 **`prompts/design_lineart_assist.md`**；实用新型见 **`prompts/structure_lineart_assist.md`** + **`structure_lineart_compose.md`**。  
多轮改材料或主题时须同步重评 `figure_plan`（含 `relates_to`；见该合同「多轮同步」）。StructureSchema 可选 `relations[].seen_in` 标注连接可见于哪些 `fig`。
