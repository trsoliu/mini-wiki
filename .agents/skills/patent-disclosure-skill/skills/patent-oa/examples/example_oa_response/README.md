# 审查答复演练材料

虚构、已脱敏的极简样例，用于冒烟测试：入库、标签检索、可选向量检索、答复草稿。  
目录对齐方案 C（history / pending / drafts）。

| 路径 | 用途 |
|------|------|
| `cases/history/hist-inventiveness-clamp.md` | 历史案：创造性 + 修改后授权 |
| `cases/history/hist-clarity-connector.md` | 历史案：清楚性 + 仅意见陈述 |
| `pending/oa_notice_pending.md` | 待答复通知书 |
| `drafts/` | 入库前人审草稿（可空） |

## 建议冒烟

```bash
# 可选：跳过向量，只测标签
python skills/patent-oa/tools/config.py skip-vector

# 入库两篇历史案（需已确认配置；可 --dry-run）
python skills/patent-oa/tools/ingest_case.py -i skills/patent-oa/examples/example_oa_response/cases/history/hist-inventiveness-clamp.md --skip-redact
python skills/patent-oa/tools/ingest_case.py -i skills/patent-oa/examples/example_oa_response/cases/history/hist-clarity-connector.md --skip-redact

# 刷新 Obsidian 索引 / Canvas / Bases
python skills/patent-oa/tools/refresh_vault.py

# 用待答复通知书检索（md/txt 亦可）
python skills/patent-oa/tools/search_cases.py \
  --query-file skills/patent-oa/examples/example_oa_response/pending/oa_notice_pending.md \
  --defect inventiveness \
  --statute "专利法第22条第3款" \
  --top-k 3
```

对话触发示例：

```text
审查答复：历史案在 skills/patent-oa/examples/example_oa_response/cases/history/，
待答复通知书 skills/patent-oa/examples/example_oa_response/pending/oa_notice_pending.md
```

细则见 [SKILL.md](../../SKILL.md)、`skills/patent-oa/prompts/`。
