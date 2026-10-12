# 公布公告著录检索

按发明人、申请人/单位、分类号、名称、摘要/简要说明、申请号/公开号检索中国专利公布公告。个人公开清单是其中一种用法。

用户给**一张图**或**一段权利要求**时，先 `Read` `prompts/derived_query.md`，把材料收成名称/摘要关键字后再检索。交底查新在交底包；本文件只跑公布站高级查询，并按下方翻页口径出报告。

## 必要输入

至少一项：发明人、申请人、分类号、名称、摘要/简要说明、申请号或公开号。缺省字段不填。多条件按公布站高级查询 AND。

单图 / 权要：读懂材料后至少填名称或摘要，并传 `--derived-from image|claims`。抽词口径见 `prompts/derived_query.md`。单图在 `--type` 为 `design` / `utility_model` / `invention` 之一后才提交（`--derived-from image` 且 `all` 会被脚本拒绝）。用户没说类型时看图推断并加 `--type-inferred`。权要按权利要求主题选类型，可用 `all`。

个人清单另需：

- 发明人/设计人姓名；
- 已知申请人或任职单位别名（可多个 `--applicant`）。缺少申请人时可先返回候选集，并标注同名归属尚未核实。

## 默认少翻页

阈值写在 `skills/patent-search/config.yaml`：

- `max_pages`：默认 **3** 页（含当前结果页）；
- `max_pages_hard`：探测不到「共 N 页」时，`--complete` 才用的回退硬上限（默认 20）；
- `page_size`：探测不到「每页 N 条」时的回退；条数只用页面采到的 `page_size_actual`；
- `page_delay_ms` / `http_error_retries`：降低公布站 HTTP 400。

对话中用户说「翻 5 页 / 多翻一点」→ `--max-pages 5`（普通检索仍受 hard 限制）。用户明确要求穷举清单时才加 `--complete`。第一页读到「共 N 页」则按总页数排程并翻「下页」；读不到再看还能不能点「下页」。普通多条件检索写「本次翻了 M 页」。

## 官方检索

```bash
python skills/patent-search/tools/cnipa_search.py \
  --inventor "姓名" \
  --applicant "申请主体一" \
  --applicant "申请主体二" \
  --type all
```

其他字段示例：`--title`、`--abstract`、`--class`、`--application-number`、`--publication-number`。

### 填表语法

跟公布站高级查询说明，按字段填。正例可直接仿；反例只标错形。

| 场景 | 正例 | 反例 |
|------|------|------|
| 名称 `#ti`、摘要 `#abs` | `计算机 and 应用`（`and` / `or` / `not` 前后空格） | `%计算机%` |
| 分类号 `#e51` | `B25J`、`B61G`、`09-03`（自左至右前缀） | `%B25J%` |
| 发明人 `#e72`、申请人 `#e71_73` | `朱云杰`；中间不确定 `朱?杰` | 个人清单写成「云杰」 |
| 申请号 `#an` | `2019211148833`（脚本去掉校验点） | `201921114883.3` 原样提交 |
| 公布公告号 `#pn` | `102853527A`、`10285`（脚本去掉 `CN` / `ZL`） | 把完整号截成更短、或 `%102853527%` |

摘要框是 `#abs`（`#ab` 与标签兜底）：发明/实用新型写摘要，外观写简要说明。首次特征用 `and`；0 条再减词或改 `or`。`?` / `%` 只用于发明人、申请人、申请号、公布号、分类号里记不清的那一位或那一段。

单图或权要示例：

```bash
python skills/patent-search/tools/cnipa_search.py \
  --title "杯盖" \
  --abstract "折叠 and 密封" \
  --class 09-03 \
  --type design \
  --derived-from image \
  --type-inferred \
  --derived-note "折叠杯盖"
```

脚本会：

1. 填高级查询页（发明人 `#e72`、名称 `#ti`、摘要 `#abs`、分类号 `#e51` 等）。申请号填表前去掉校验点（`201921114883.3` → `2019211148833`）；公布号去掉 `CN` / `ZL`。
2. 先解析**当前结果页**：采 `total_pages`（「共 N 页」）、`page_size_actual`（`#pageSize` /「每页 N 条」）和本页命中数；再点「下页」。回退 fetch 保留 `#searchAfter`。
3. 400 时退避重试，仍失败则 `complete=false` 停止。
4. `--complete` 的目标页数在采到总页数时等于总页数；探测不到才用 `max_pages_hard`。普通检索达到 `max_pages` 即停。
5. 若提供了发明人/申请人，按申请人过滤同名并合并同一申请的公布/授权记录。
6. 检索脚本把 payload 交给 `tools/emit_search_report.py` 落盘。默认 `outputs/patent-search/SEARCH-YYYYMMDD-HHMMSS.md`。改表头/字段/目录只改该文件。

## 完整性门禁

- 采到总页数且 `complete: true` 时，写「已翻完全部分页」。没采到总页数时，按还能不能点「下页」写「已翻到末页」。
- 采到总页数且未翻完：写「共 N 页，还剩 x 页未翻」；撞本次上限则写「共 N 页，本次上限 M」。
- 没采到总页数时，只说还能不能点「下页」。
- 退出码 `3` 或 `complete: false` 可以展示部分记录，并写明停止原因（`max_pages` / `max_pages_hard` / `http_400` / `stalled` 等）。
- 条数估计用 `(total_pages-1)*page_size_actual + 末页实条`；末页可能不足一页。
- WAF、验证码、DOM 改版记为检索失败，与零结果分开写。stderr `CNIPA_EPUB_ERROR` 带 `reason=`：`backend_timeout` / `backend_error` 写「公布站后端未返回」，建议缩窄条件后再查；`waf_rejected`、`submit_not_sent` 或「未出现高级查询页」写「公布站拦截或放行超时（脚本已换新会话重试一次）」，建议隔半小时再查。
- 公布公告只覆盖已公开/公告记录。

## 同名归属（个人清单用法）

- `verified_inventor_metadata` → “已由官方发明人著录核实”
- `inventor_query_and_applicant` → “发明人查询与申请人共同匹配”
- `inventor_query_only_unverified_namesake` → “仅姓名查询命中，同名归属待核实”

机读前缀：`EPUB_SEARCH_MD:` / `EPUB_SEARCH_JSON:`（stdout）、`EPUB_SEARCH_NOTE:` / `EPUB_SEARCH_INCOMPLETE:`（stderr）。面向用户给 Markdown 路径和中文摘要。

## 按特征精排（可选旁路）

用户点名或对照表派工时，`Read` `prompts/covers_rank.md`。用命中摘要对 Fk 打 `covers_feature`，经 `emit_covers_report.py` 另写 `SEARCH-*.covers.md` / `.covers.json`。列表仍是本次 `SEARCH-*.md`。
