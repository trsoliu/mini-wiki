---
name: patent-reader
description: "中国专利通俗解读：公开号/PDF 成通俗笔记、图谱与 Obsidian 入库。"
user-invocable: false
---

# 专利通俗解读

1. **`Read`** `prompts/patent_plain_reader.md`
2. 实用新型或外观：**`Read`** `prompts/type_hooks.md` + `prompts/fill_*`
3. 笔记 / 自检：`obsidian_ofm_companion.md`、`patent_reader_self_check.md`

工具在 **`tools/`**（本包 `extract/` · `analyze/` · `vault/`）。  
中间产物：用户工作区 **`outputs/patent_reader/`**。PDF：`tools/extract/fetch_patent_pdf.py`；入库：`tools/vault/write_patent_obsidian_note.py`。

与交底互斥：解读不跑交底 Step 1–8。
