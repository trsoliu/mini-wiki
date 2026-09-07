# AppearanceSchema 填写（图 / 原文 → 外观事实）

**合同**：`references/schemas/appearance.schema.yaml`  
**附图选用**：`references/schemas/figure_plan.schema.yaml`（必做）

## 何时 Read

交底类型为**外观设计**。

## 落盘目录

默认 **`outputs/{案件标识}/`**。同目录写出：

| 文件 | 说明 |
|------|------|
| `appearance_schema.yaml`（或 `.json`） | AppearanceSchema 实例 |
| `figure_plan.yaml` | 入文视图选用、排序与**视图关联** |

`figure_plan.schema_ref` 填**本实例**（如 `appearance_schema.yaml`），勿填合同路径。

## 流程

1. 先判再收图（**勿默认六视**）  
   - 判 `product_form`：`solid` 立体产品 / `planar` 平面产品。  
   - 按设计要点列出 `claimed_faces`，正投影 = 要点落面；立体宜加立体图。**仅要点涉及六个面**才收齐六面正投影。平面产品一面或两面即可。  
   - 相同、对称或无要点的面写入 `omitted_views`（供简要说明），不为这些面凑图。  
   - 再收集已有正投影 / 立体图 / 效果图 / 专利视图。成文前即使有 STEP 也不投影。仅当用户已在**交底落盘后**确认开启（或成文前主动要求）：可用 `run_step_to_views.py` 自动投影作视图材料（外观仍以可见造型为准；场景图规则不变）。  
2. **跨图联读**：多视视为同一产品；比例、开口、装饰位置须一致；矛盾写入 `uncertain`  
3. 先填 AppearanceSchema，再写交底提纲  
4. **`Write`** `appearance_schema.yaml`（或 json）**与** `figure_plan.yaml`  
   - 须写 `product_form`、`claimed_faces`、`omitted_views`（无省略则 `[]`）  
   - `covers` 对齐 `views.name` 或设计要点短标签；`figure_plan` 正交条只覆盖 `claimed_faces`，勿为 `omitted_views` 分配入文 `fig`  
   - 多视之间可用 `relates_to`：`same_state` / `alternate_view`；局部造型用 `detail_of` 指向立体/主视  
   - `views[].source_image` 可选，指向材料路径  
   - 每张图写 `kind` + `relevance` + `quality` + `score`（见 `image_gen.md`）  
   - **入文须同时选**：合格/生成的 `lineart` **和** 干净实拍 `photo_clean`（md 与 Word 都嵌；交底对照用，不表示申请必须六视）。CAD 禁止入文；`photo_scene` 默认不入  
   - 要点落面缺源图 → `uncertain`；故意不交的面只写 `omitted_views`，禁止写成「缺正式六视」  
   - `theme_summary` = 当前产品外观主题；`patent_type: design`；`mode: disclosure`  
5. **外观线稿（必做）**：**`Read`** `prompts/image_gen.md`，再 **`Read`** `prompts/design_lineart_assist.md`。不问用户。先 `image_gen.py`：已有合格线稿则入文；否则图生图或文生图。实拍仍入文，只是不当线稿。CAD 投影不是线稿、不入文。仅 `PATENT_SKILL_SKIP_LINEART=1` 或用户明确不要线稿才跳过。  
6. 区分「整体造型」与「装饰图案/色彩」；`uncertain` 单独列出

## 多轮

换图、改产品侧重点或设计要点时：**无则新建、有则重评** `figure_plan.yaml`（含 `relates_to`），再改正文视图引用。

## 最低输出

- AppearanceSchema 实例：含 `overall_shape`、`product_form`、`claimed_faces`、`omitted_views`（可 `[]`）、`views`（或 `uncertain` 说明要点落面缺源图）、`ornament`/`color` 可空、`uncertain`  
- 同目录 **`figure_plan.yaml`**（正交入文条对齐 `claimed_faces`）
