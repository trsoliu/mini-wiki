# 审查答复 · 案例脱敏入库

前置：`guardrails.md`、`intake.md`；配置已确认。

## 输入（优先 PDF）

- **历史通知书 PDF**（必给路径；Agent 自动抽取，勿让用户粘贴）  
- 可选：**意见陈述/答复 PDF**（`--reply-pdf`）  
- 或已整理好的案例 Markdown（含 frontmatter，见 `oa_case.schema.yaml`）

模板：`skills/patent-oa/prompts/case_note_template.md`。

## 步骤

1. **抽取并起草**（推荐）：

```bash
pip install -r skills/patent-oa/tools/requirements-oa.txt   # 含 pymupdf
# 仅生成草稿（人审补 statutes / defect_types 后再入库）
python skills/patent-oa/tools/ingest_case.py --pdf path/to/notice.pdf \
  --reply-pdf path/to/reply.pdf \
  --case-id my-case-slug --title "脱敏标题" --draft-only
```

2. Agent `Read` 草稿 md + `.extracted.txt`，补全 frontmatter：`statutes`、`defect_types`、`patent_type`、`domain`、`strategy`、`outcome`、`related_cases`、`tags`；确认 `status: history`（待答复用 `pending`）。  
3. 人审：列出将脱敏项；用户确认「可入库」。  
4. 入库：

```bash
python skills/patent-oa/tools/ingest_case.py -i path/to/case.md --extra-name "客户名"
# 或确认草稿后：去掉 --draft-only，直接 --pdf …（会抽→写草稿→入库）
```

5. 向用户报告：`note_path`、`case_id`、chunk 数、sqlite 路径，以及 `_OA索引` / Canvas 已刷新。本轮是入库，**不要**再按 `soft_nudge.md` 提示「去入库」。  
6. **禁止**把未脱敏原文提交到 git。

单独抽文本：`python skills/patent-oa/tools/pdf_text.py -i notice.pdf`。  
仅刷新 Obs 结构：`python skills/patent-oa/tools/refresh_vault.py`。

## 落盘位置（方案 C）

| 有 Obsidian 库 | 无库 |
|----------------|------|
| `{vault}/oa/cases/history/{case_id}.md` | `{Documents}/…/oa/cases/history/` |
| `{vault}/oa/pending/` · `{vault}/oa/drafts/` · `{vault}/oa/playbooks/` | 同左相对结构 |
| `{vault}/oa/_OA索引.md` · `_OA看板.base` · `_OA关联.canvas` | 同左 |
| 向量：`{Documents}/…/oa/data/oa_vectors.sqlite` | 同左 |
