# StructureSchema 填写（图 / 原文 → 结构事实）

**合同**：`references/schemas/structure.schema.yaml`  
**附图选用**：`references/schemas/figure_plan.schema.yaml`（必做）

## 何时 Read

交底类型为**实用新型**，或发明案中需写清装置结构。

## 落盘目录

默认 **`outputs/{案件标识}/`**（与交底定稿同级）。同目录写出：

| 文件 | 说明 |
|------|------|
| `structure_schema.yaml`（或 `.json`） | StructureSchema 实例 |
| `figure_plan.yaml` | 入文附图选用、排序与**图际关联** |

`figure_plan.schema_ref` 填**本实例**相对路径（如 `structure_schema.yaml`），勿填合同文件 `references/schemas/structure.schema.yaml`。

## 流程

1. 收集结构图（照片、CAD 截图、爆炸图、专利附图）  
   - 成文前即使有 **`.step`/`.stp`** 也不投影、不装依赖；用已有图片/文档填表。仅当用户已在**交底落盘后**确认开启（或成文前主动要求）：按 `project_scan.md`「CAD / STEP」运行 **`run_step_to_views.py --enable-step-parse`**，以产出的 `views/*` + `*.seed.yaml` 为材料起点。  
   - 仅有原生 CAD、无 STEP：勿假装已解析；交付回复末尾提示导出 STEP（见 `cad_scan.py`）。  
2. **跨图联读**：总装 / 爆炸 / 局部须对照同一套件号；先建立「图角色」再填 parts（禁止每张图各起一套命名）  
   - **件号粒度**：`parts` 只列为交底第三章要指认的部件。可分离总成（端盖、定子、转子、轴）可以分开写。**不要**为了画图把加强筋、单颗螺栓、齿形、倒角、剖面符号、剖切指示拆成独立 `parts.id`；这些写进该件的 `shape` 即可。剖视关系写进 `figure_plan.relates_to`，不要把剖切线/箭头当成零件去画。  
3. 先填 StructureSchema，再写交底；禁止看图直接长文  
4. **`Write`** `structure_schema.yaml`（或 json）**与** `figure_plan.yaml`  
   - 若有 `figure_plan.seed.yaml` / `structure_schema.seed.yaml`：可复制审改为定稿；**CAD 种子条保持 `kind: cad`、不入文**，须识图重评 `relevance` / `quality`。  
   - 对每张候选图判定 `role` / `kind` / `covers`（对齐 `parts.id`）/ `relevance` / `quality` / `score`  
   - **图际关联**：局部/剖视/爆炸图填写 `relates_to`（如 `detail_of` → 总装 `fig`）；有 assembly+detail 入文对时**不得**漏写  
   - 可选：关键 `relations[].seen_in` 列出能看见该连接的 `fig` 号  
   - **入文只选合格 `lineart`**；`cad` / 实拍只打分，禁止当线稿入文  
   - 仅 `use_in_disclosure: true` 分配连续 `fig`（1…N）  
   - `theme_summary` 写当前结构主题；`patent_type: utility_model`；`mode: disclosure`  
5. **结构线稿（必做）**：**`Read`** `prompts/image_gen.md`，再 **`Read`** `prompts/structure_lineart_assist.md`（轮廓后必 **`Read`** `structure_lineart_compose.md`）。不问用户。先 `image_gen.py` 看 `mode`：已有合格线稿则入文、不再生成整张；否则图生图（CAD/实拍可作参考）或文生图。按 `parts` 写出子 SVG 再拼总图，再 overlay 件号；叠标后须读图按名称核对引出线（改锚点 YAML 重叠标，最多 2 轮）。禁止自创件号。勿与外观 `design_lineart_*` 混用。仅 `PATENT_SKILL_SKIP_LINEART=1` 或用户明确不要线稿才跳过。  
6. `uncertain` 不得写成确定保护点；跨图对不上的写入 `uncertain`

## 多轮

原材料增删换、主题/候选点变更、新增局部图时：**无清单则新建、有则重评** `figure_plan.yaml`（含 `relates_to`），再改交底附图与「如图 N」。细则见 figure_plan 合同「多轮同步」。

## 最低输出

- StructureSchema 实例：合法 JSON/YAML，含必填 `parts`、`relations`（或显式 `[]` + 说明）、`spatial`、`uncertain`  
- 同目录 **`figure_plan.yaml`**（可无入文图，但须条目说明原因；有总装+局部则须 `relates_to`）
