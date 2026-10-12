# 解读侧 · 专利类型挂钩（Schema）

## 类型如何确定（优先自动）

**不必**强求用户口头说类型。有明确中国公开号时，取证后按下列顺序判定：

1. 用户显式声明（发明 / 实用新型 / 外观）  
2. **公开号文献种类码**（`CN…A/B`→发明，`CN…U/Y`→实用新型，`CN…S`→外观）  
3. 扉页/著录关键词（「实用新型」「外观设计」等）

推荐在取证后立刻跑：

```bash
python tools/patent_type.py --pub <公开号>
# 整仓：python skills/patent-reader/tools/patent_type.py --pub <公开号>
# 或：fetch_patent_pdf.py 成功时 stdout 已含 PATENT_TYPE: …
```

`fetch_patent_pdf.py` 写入的 `fetch_pdf_status.json` 含 `patent_type` / `patent_type_label_zh` / `patent_type_source`。

判定为实用新型或外观后，在 `patent_plain_reader.md` 主流程中：

| 类型 | Read | 合同 | Agent 落盘 | 入库写入 |
|------|------|------|------------|----------|
| 实用新型 | `prompts/fill_structure_schema.md` | `references/schemas/structure.schema.yaml` | `workdir/structure_schema.json` | 笔记「结构说明」节（无 Schema 脚注；连接表含件号+名称）+ Canvas 结构卡 |
| 外观设计 | `prompts/fill_appearance_schema.md` | `references/schemas/appearance.schema.yaml` | `workdir/appearance_schema.json` | 笔记「外观要点」节（无 Schema 脚注）+ Canvas 外观卡 |
| 发明 | 默认现有叙事；装置附图多时可**可选**写 StructureSchema | — | 可选 | 同上 |

**时机**：校对权要 / 写 `claim_deltas` 之后、撰写解读正文之前填 schema；入库时 `skills/patent-reader/tools/vault/write_patent_obsidian_note.py` 自动读取（或 `--structure-schema` / `--appearance-schema`）。

**figure_plan**：不写、不强制。工作目录若已有可忽略，**勿**按交底流程嵌图成文。

**不**调用交底包的 `disclosure_builder.md` / `image_gen.md` / 线稿 assist。

