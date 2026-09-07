---
name: patent-search
description: "中国专利公布公告著录检索：发明人、申请人、分类号、名称等高级查询字段。"
user-invocable: false
---

# 著录检索

通用公布站高级查询，不是「个人清单技能」。个人公开清单只是一种用法。

**先 `Read` `prompts/patent_search.md`。**

## 默认少翻页

- 阈值在 **`config.yaml`**：`max_pages`（默认 3）；`max_pages_hard`（默认 20）仅在探测不到「共 N 页」时启用。
- `page_size` 只是探测不到「每页 N 条」时的回退，不要用它估总条数。
- 对话里用户说「多翻几页 / 翻 5 页」→ 传 `--max-pages N`（普通检索仍受 hard 限制）；或改 `config.yaml`。
- **不要**一上来爬完全部分页。只有用户明确要求穷举清单时才加 `--complete`。
- `--complete` 第一页若读到「共 N 页」，按总页数翻完（硬上限随总页数）；读不到才用 `max_pages_hard`。
- 采到总页数才能说「已翻完全部分页」或「还剩 x 页」；没采到只谈还能不能点「下页」。
- `complete: false` 时禁止称为「全部」。退出码 `3` 表示分页不完整。

## 命令

```bash
python skills/patent-search/tools/cnipa_search.py --inventor "姓名" --applicant "单位"
python skills/patent-search/tools/cnipa_search.py --title "数据处理" --class B01J20 --max-pages 2
python skills/patent-search/tools/cnipa_search.py --inventor "姓名" --complete
```

单独拷走本包时：`python tools/cnipa_search.py …`。

结果默认落到 **`outputs/patent-search/SEARCH-YYYYMMDD-HHMMSS.md`**（gitignore）。改版式只动 `tools/emit_search_report.py`。

机读前缀：`EPUB_SEARCH_MD:` / `EPUB_SEARCH_JSON:` / `EPUB_SEARCH_NOTE:` / `EPUB_SEARCH_INCOMPLETE:`。对话里告诉用户 Markdown 路径，不要只倒 JSON。

必须走高级查询字段（`#e72` 发明人、`#ti` 名称、`#e51` 分类号等），禁止把发明人姓名填进首页综合框代替。申请号填表前去掉校验点。

**不做**：Google Patents / 学术检索与跨库去重、PSS 登录站、权利要求全文/同族深挖。  
**禁止**被交底 Step 5 当查新引擎调用。
