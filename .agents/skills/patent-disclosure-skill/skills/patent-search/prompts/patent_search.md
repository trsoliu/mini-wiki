# 公布公告著录检索

用于按发明人、申请人/单位、分类号、名称、申请号/公开号等字段检索中国专利公布公告。个人公开清单只是其中一种用法，不是本包的全部定义。

与交底 Step 5 技术主题查新不同：本流程走高级查询多条件，并按配置翻页；**不要**用交底轻量一词一页的结果代替本包。

## 必要输入

至少一项：发明人、申请人、分类号、名称、申请号或公开号。缺省字段不填。多条件按公布站高级查询 AND。

个人清单场景另需：

- 发明人/设计人姓名；
- 已知申请人或任职单位别名（可多个 `--applicant`）。缺少申请人时可先返回候选集，但须标注同名归属尚未核实。

## 默认少翻页

阈值写在 `skills/patent-search/config.yaml`：

- `max_pages`：默认 **3** 页（含当前结果页）；
- `max_pages_hard`：探测不到「共 N 页」时，`--complete` 才用的回退硬上限（默认 20）；
- `page_size`：探测不到「每页 N 条」时的回退，禁止用配置值估总条数；
- `page_delay_ms` / `http_error_retries`：降低公布站 HTTP 400。

对话中用户说「翻 5 页 / 多翻一点」→ `--max-pages 5`（普通检索仍受 hard 限制）。只有明确要求穷举清单时才加 `--complete`。第一页读到「共 N 页」则按总页数排程并翻「下页」；读不到再退回能否点「下页」。普通多条件检索**禁止**声称「全部」。

## 官方检索

```bash
python skills/patent-search/tools/cnipa_search.py \
  --inventor "姓名" \
  --applicant "申请主体一" \
  --applicant "申请主体二" \
  --type all
```

其他字段示例：`--title`、`--class`、`--application-number`、`--publication-number`。

脚本会：

1. 使用高级查询页字段（发明人 `#e72`、名称 `#ti`、分类号 `#e51` 等），禁止用首页综合关键词框模拟发明人检索；申请号在填表前去掉校验点（`201921114883.3` → `2019211148833`）；
2. 先解析**当前结果页**：采 `total_pages`（「共 N 页」）、`page_size_actual`（`#pageSize` /「每页 N 条」）和本页命中数；再点「下页」。不要跳「到第 N 页」，不要对第 1 页再 POST 一遍，也不要清空 `#searchAfter`（会 HTTP 400）；
3. 400 时退避重试，仍失败则 `complete=false` 停止，禁止死循环；
4. `--complete` 的目标页数在采到总页数时等于总页数；探测不到才用 `max_pages_hard`。普通检索达到 `max_pages` 即停；
5. 若提供了发明人/申请人，按申请人过滤同名并合并同一申请的公布/授权记录；
6. 检索脚本把 payload 交给 `tools/emit_search_report.py` 落盘，不在爬虫里拼 Markdown。默认 `outputs/patent-search/SEARCH-YYYYMMDD-HHMMSS.md`。改表头/字段/目录只改该文件。

## 完整性门禁

- 采到总页数且 `complete: true` 时，才可说「已翻完全部分页」。没采到总页数时，只根据还能不能点「下页」说「已翻到末页」。
- 采到总页数且未翻完：写明「共 N 页，还剩 x 页未翻」；若撞本次上限则写「共 N 页，本次上限 M」。
- 没采到总页数时，退回「还能不能点下页」，禁止用总页数说话。
- 退出码 `3` 或 `complete: false` 可以展示部分记录，必须写明停止原因（`max_pages` / `max_pages_hard` / `http_400` / `stalled` 等）。
- 不要用配置 `page_size` 估条数。预期约 `(total_pages-1)*page_size_actual + 末页实条`；末页可能不足一页。
- WAF、验证码、DOM 改版属于检索失败，不等于零结果。
- 公布公告只覆盖已公开/公告记录，公开记录数不得写成实际提交总数。

## 同名归属（个人清单用法）

- `verified_inventor_metadata` → “已由官方发明人著录核实”
- `inventor_query_and_applicant` → “发明人查询与申请人共同匹配”
- `inventor_query_only_unverified_namesake` → “仅姓名查询命中，同名归属待核实”

机读前缀：`EPUB_SEARCH_MD:` / `EPUB_SEARCH_JSON:`（stdout）、`EPUB_SEARCH_NOTE:` / `EPUB_SEARCH_INCOMPLETE:`（stderr）。面向用户给 Markdown 路径和中文摘要，不要只倒 JSON 键。
