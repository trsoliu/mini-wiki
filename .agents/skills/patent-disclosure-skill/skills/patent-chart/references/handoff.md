# 交接（路径不是摘要）

跨解读 / 检索包时，对话与 payload 只传：

- `scene`
- 左列：已公开只要公开号；未公开只要 `left.paths`（`left.source=local`）
- 右列：公开号列表、产品名、`right[].url`（产品页）、产品/标准文件路径、covers 旁路路径
- 允许补 D 与否；用户明说「帮我补搜 / 对比文件未定」时写 `search_fill: true`（可专利性/无效允许右列暂空）
- 派工解读：`Read` `skills/patent-reader/SKILL.md` 后按其流程执行。对照表只要 `claim_features.json`（含从权）和 `description_paragraphs.json`。不写通俗笔记、不入库、不裁附图。全文用解读包 `fetch_patent_pdf.py`。失败则请用户给 PDF。
- 派工检索：`Read` `skills/patent-search/SKILL.md` 后按其流程执行
- 禁止未读对方 SKILL 就直接调其 `tools/`；禁止调交底 `cnipa_epub_search.py`
- 对话收齐后：`outputs/patent-chart/{案件}/{会话}/intake.json`（以该会话磁盘为准）
- 用户给出的文件路径记在 `left.paths` / `right[].paths`（`path` 为第一项）
- 导出对照表用 `--into {INTAKE_DIR}`，和 intake 放在同一会话目录

禁止把权要「概括成要点」代替 `text` 原文路径；禁止诱导编造未给出的产品结构。
