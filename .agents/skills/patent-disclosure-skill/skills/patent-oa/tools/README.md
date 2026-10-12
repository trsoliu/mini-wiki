# 审查答复工具

案例笔记（Obsidian）+ 可选向量检索。**向量不是必须的**。

## 对话配置（推荐）

Agent 按 `skills/patent-oa/prompts/configure_embedding.md` 问答；写文件命令示例：

```bash
python skills/patent-oa/tools/config.py recommend
python skills/patent-oa/tools/config.py skip-vector
# 或：预设 + Key（Key → 文档目录 embedding.secrets.yaml）
python skills/patent-oa/tools/config.py set --preset zhipu --api-key "sk-..."
# 或：自定义
python skills/patent-oa/tools/config.py set --provider openai_compatible \
  --model embedding-3 --dimensions 1024 \
  --base-url https://open.bigmodel.cn/api/paas/v4 \
  --api-key "sk-..."
# set 默认自检；也可单独：
python skills/patent-oa/tools/config.py selftest
python skills/patent-oa/tools/config.py status
python skills/patent-oa/tools/rebuild_vectors.py --confirm
```

- 配置：`{Documents}/patent-disclosure-skill/oa/embedding.config.yaml`  
- 密钥：同目录 `embedding.secrets.yaml`（勿提交）  
- 自检失败仍可用标签检索。

## Provider

| provider | 典型 preset |
|----------|-------------|
| `openai_compatible` | `zhipu` / `dashscope` / `openai` |
| `minimax` | `minimax` |
| `local` | `local` |

## 入库 / 检索（优先 PDF）

```bash
python skills/patent-oa/tools/search_cases.py --pdf notice.pdf --defect inventiveness --top-k 5
python skills/patent-oa/tools/ingest_case.py -i path/to/case.md
python skills/patent-oa/tools/refresh_vault.py   # 索引 + Bases + 关联 Canvas
python skills/patent-oa/tools/refresh_vault.py --inventory  # 只读：历史案数量（答复末尾引导用）
python skills/patent-oa/tools/emit_opinion_docx.py -i outputs/oa/案/会话/意见陈述_时间戳.md
python skills/patent-oa/tools/emit_chart.py --json outputs/oa/案/会话/_payload.json --into outputs/oa/案/会话
```

意见陈述 Word：**仅用户确认采纳某份草稿后**，按 `assets/opinion_statement.md` 写递交 md，再跑本包 `emit_opinion_docx.py`（`md_to_docx.py` 是本包副本）。不做官方电子表单、不排版权要替换页。普通括号包 LaTeX 时 stderr 打印 `LATEX_DELIM:`，**不阻断**出 Word（陈述书可能引用权要原文括号）。

对照表 xlsx：`emit_chart.py` / `highlights.py` / `xlsx_minimal.py` / `write_intake.py` 是 `skills/patent-chart/tools/` 的副本。改对照包时覆盖本包同名文件。测试 `tests/test_chart_tools_sync.py` 会比对。

Obsidian 结构：`oa/cases/history/` · `oa/pending/` · `oa/drafts/` + `_OA索引` / `_OA看板.base` / `_OA关联.canvas`。

见 `skills/patent-oa/prompts/`、[docs/vault.md](../docs/vault.md) 与 [SKILL.md](../SKILL.md)。
