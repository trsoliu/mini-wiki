# 按特征精排（covers_feature）

仅当 **对照表派工** 或用户点名「按特征精排 / 能否填进某一特征格」时执行。普通著录检索**不要**读本文件，也不要生成 covers 旁路。

原 `SEARCH-*.md` / 命中 json **格式不动**。本步骤只另写 `SEARCH-*.covers.md` 与 `.covers.json`。

## 输入

- 刚完成的检索列表路径（`EPUB_SEARCH_MD:`）及命中（公开号、摘要、链接）。摘要尽量写入打分行的 `abstract` / `snippet`（没有独权全文时用摘要，不要编权要）。
- 特征清单：`claim_features.json` 或用户给出的 Fk 原文短语。

## 打分

对每条命中 × 每个空格/指定 Fk，判断「这段摘要能否填进该特征格」：

| 分 | `covers_feature` | 含义 |
|----|------------------|------|
| 5–4 | true | 摘要明确覆盖该限定 |
| 3 | true | 同手段、表述不同 |
| 1–2 | false | 仅关键词撞车 |
| 0 | false | 无关 |

禁止无摘要却标 true。术语可能同义时最高 3 分。

写入打分 JSON（示意）后调用脚本，`--beside` 指向本次列表 md：

```bash
python skills/patent-search/tools/emit_covers_report.py \
  --json outputs/patent-search/covers_payload.json \
  --beside outputs/patent-search/SEARCH-YYYYMMDD-HHMMSS.md
```

对话里同时给出列表 md 与 covers md 两条路径。covers 不是查新结论，不得写成 FTO / 无效意见。
