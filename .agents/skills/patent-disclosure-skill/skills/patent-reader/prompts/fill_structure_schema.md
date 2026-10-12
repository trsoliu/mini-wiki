# StructureSchema 填写（图 / 原文 → 结构事实）

只填 Schema，供笔记「结构说明」与 Canvas 结构卡。**不写** `figure_plan`，**不生成**线稿，**不跑** STEP / CAD / `image_gen`。

**合同**：`references/schemas/structure.schema.yaml`

## 何时 Read

解读对象为**实用新型**，或附图以装配/结构为主的装置向专利。

## 落盘

工作目录 **`structure_schema.json`**（入库脚本约定名）。

## 流程

1. 收集已取证的结构图（专利附图、爆炸图、剖视）。用图与说明书填表，**不要**投影 STEP、不要装 CAD 依赖。  
2. **跨图联读**：总装 / 爆炸 / 局部须对照同一套件号；先建立「图角色」再填 parts（禁止每张图各起一套命名）。  
   - **件号粒度**：`parts` 只列为说明书要指认的部件。可分离总成（端盖、定子、转子、轴）可以分开写。**不要**把加强筋、单颗螺栓、齿形、倒角、剖面符号拆成独立 `parts.id`；这些写进该件的 `shape` 即可。  
3. 先填 StructureSchema，再写通俗笔记；禁止看图直接长文。  
4. **`Write`** 工作目录 `structure_schema.json`  
   - `theme_summary` 写当前结构主题；`patent_type: utility_model`（若为发明案的装置附图可仍写发明类型，但结构字段照填）  
   - `mode: reader`  
5. `uncertain` 不得写成确定保护点；跨图对不上的写入 `uncertain`。

## 最低输出

- `structure_schema.json`：合法 JSON，含必填 `parts`、`relations`（或显式 `[]` + 说明）、`spatial`、`uncertain`
