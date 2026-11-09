# 海外检索（Google Patents）

用户点名海外 / 指定局时才用：「海外检索」「查美国专利」「包含欧洲 / 日本 / 韩国」「PCT 检索」「查 XX 公司在美国的专利」等。没提国家的「查查有没有类似专利」仍走公布站 `patent_search.md`。交底查新不走本文件。

数据源是 Google Patents（无需登录和 key）。阈值未公开，脚本请求容易被判为自动流量，所以每次运行只发一个请求，不重试。

## 检索词

| 场景 | 正例 | 反例 |
|------|------|------|
| 中文技术词 | 译成英文并补同义词：`(battery OR cell) (thermal runaway)` | 直接填中文查美日韩 |
| 日韩文献 | 仍用英文（Google 已把非英文专利机译成英文并建索引） | 另造日文、韩文检索词 |
| 中国文献 | 不走本文件，用公布站 | `--country CN` 代替公布站 |

用户的中文原意写进 `--note`，报告里保留。

## 字段

| 用户说法 | 参数 |
|----------|------|
| 关键词（空格即 AND；`OR`；`-词` 排除；引号整词） | `-q` |
| 名称 / 摘要 / 权利要求里出现 | `--title` / `--abstract` / `--claims` |
| CPC（含下位加 `/low`） | `--cpc H01M10/48/low`，可重复 |
| 申请人 / 发明人 | `--assignee` / `--inventor`，可重复 |
| 局别 | `--country US,EP,WO,JP,KR`（「包含海外」未点国家时用这五个） |
| 外观 / 授权 / 申请公开 | `--type design`、`--status grant`、`--status application` |
| 日期 | `--after` / `--before`（YYYY、YYYY-MM、YYYY-MM-DD），`--date-field priority\|filing\|publication`，默认优先权日 |
| 最新 / 最早优先 | `--sort new` / `--sort old`（缺省按相关度） |
| 每页条数、翻页 | `--num`（默认 10，见 `config.yaml`）、`--page 2` |

美国、欧洲没有实用新型一档；用户要查实用新型也按普通专利查，不加 `--type`。

## 命令

```bash
python skills/patent-search/tools/gp_search.py \
  -q "(battery OR cell) (thermal runaway)" \
  --country US,EP,JP --after 2020 \
  --note "电池热失控预警"
```

## 交付清单

- stdout `GP_SEARCH_MD:` → 对话给出这个 Markdown 路径和中文摘要（共几条、本页几条、前几条公开号与申请人）。
- stdout `GP_SEARCH_JSON:` → 命中机读对象；`hits[].snippet` 是命中片段。
- 报告写入 `outputs/patent-search/SEARCH-*.md`，与公布站报告同目录。

## 一行门禁

- 用户点名海外或指定局之后，才跑 `gp_search.py`。
- 用户说「下一页」「再多看一些」之后，才加 `--page` 再跑一次；不自行循环翻页。
- 退出码 4（stderr `GP_SEARCH_ERROR: reason=blocked`）之后，本轮海外检索结束：告诉用户「Google Patents 暂时限流，稍后再试」，不重试、不换参数再发、不改用 WebSearch 凑结果。
- 退出码 1 时按 `reason` 如实说明（`unavailable` 连不上、`bad_response` 接口可能改版），不写成 0 条。

## 完整性

报告「完整性」一行已按总数写明是否末页；一页结果不得说成完整清单。命中片段不是摘要：要判断技术方案或填对照表，把公开号交解读包 `fetch_gp_fulltext.py` 取全文。

## 半句边界

不编造公开号、链接或总数；结果不冒充交底查新、FTO 或无效结论。
