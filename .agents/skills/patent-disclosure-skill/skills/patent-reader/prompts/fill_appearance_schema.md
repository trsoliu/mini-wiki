# AppearanceSchema 填写（图 / 原文 → 外观事实）

只填 Schema，供笔记「外观要点」与 Canvas 外观卡。**不写** `figure_plan`，**不生成**线稿，**不跑** STEP / CAD / `image_gen`。

**合同**：`references/schemas/appearance.schema.yaml`

## 何时 Read

解读对象为**外观设计**专利（公开号 `CN…S`，或类型已判定为 design）。

## 落盘

工作目录 **`appearance_schema.json`**（入库脚本约定名）。

## 流程

1. 先判再收图（**勿默认六视**）  
   - 判 `product_form`：`solid` 立体产品 / `planar` 平面产品。  
   - 按设计要点列出 `claimed_faces`，正投影 = 要点落面；立体宜加立体图。**仅要点涉及六个面**才收齐六面正投影。平面产品一面或两面即可。  
   - 相同、对称或无要点的面写入 `omitted_views`。  
   - 材料来自已取证的专利视图 / 说明书图。  
2. **跨图联读**：多视视为同一产品；比例、开口、装饰位置须一致；矛盾写入 `uncertain`。  
3. 先填 AppearanceSchema，再写通俗笔记；禁止看图直接长文。  
4. **`Write`** 工作目录 `appearance_schema.json`  
   - 须写 `product_form`、`claimed_faces`、`omitted_views`（无省略则 `[]`）  
   - `views[].source_image` 可指向取证图路径  
   - 要点落面缺源图 → `uncertain`；故意不交的面只写 `omitted_views`，禁止写成「缺正式六视」  
   - `mode: reader`  
5. 区分「整体造型」与「装饰图案/色彩」；`uncertain` 单独列出。

## 最低输出

- `appearance_schema.json`：含 `overall_shape`、`product_form`、`claimed_faces`、`omitted_views`（可 `[]`）、`views`（或 `uncertain` 说明要点落面缺源图）、`ornament`/`color` 可空、`uncertain`
