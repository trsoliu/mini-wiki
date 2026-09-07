---
name: patent-disclosure-skill
description: "中国专利技能：挖掘专利点与编写交底书（发明/实用/外观），把已有交底改写成申请文件四件套，按著录字段检索公布公告，通俗解读专利，对照审查口径出政策简报，辅助审查答复。| China patents skill: mine patent points and draft disclosures, rewrite an existing disclosure into Chinese application documents, search CNIPA bibliographic records, explain patents, brief examination-policy changes for disclosures, and assist office-action responses."
version: "4.2.0"
user-invocable: true
argument-hint: "[可选：项目路径 / 交底书 / 申请底稿 / 专利检索 / 专利号或 PDF / 政策简报 / 审查答复]"
allowed-tools: Read, Write, Edit, Grep, Glob, WebSearch, Bash
---

# 中国专利技能

按用户意图 **`Read`** 对应入口的 `SKILL.md`，再按该流程执行。

| 能力 | 做什么 | 何时进入 | 入口 |
|------|--------|----------|------|
| **交底** | 挖专利点 → 查新 → 成稿 → 迭代 | 专利挖掘、交底书、查新、实用新型、外观设计；`/patent-disclosure`、`/交底书` | `skills/patent-disclosure/SKILL.md` |
| **申请文件** | 已有交底 → 权要 / 说明书 / 摘要 / 附图 | **须显式**且**指定交底目录**：申请文件、申请底稿、申报材料、`/申请底稿`、`/patent-apply`。仅缺材料则终止；内容争议写入问题清单；交付末尾须摘要清单；改已有产出则另存 | `skills/patent-application/SKILL.md` |
| **检索** | 公布站高级查询（发明人/申请人/分类号/名称等） | 按著录字段查公布公告、个人公开清单；`/patent-search`。普通多条件**不要**默认翻完全部分页 | `skills/patent-search/SKILL.md` |
| **解读** | 公开号 / PDF / 全文 → 通俗笔记 + 图谱 | 读专利、公开号或 PDF 且目标为理解；`/patent-read`、`/读专利` | `skills/patent-reader/SKILL.md` |
| **审查答复** | 审查意见问答与草稿；库薄时引导入库/蒸馏 | **须显式**：审查意见、OA、案例入库、实务书、`/oa` | `skills/patent-oa/SKILL.md` |
| **政策简报** | 对照国知局口径，说明对交底写法/本稿的影响；改技能仅为旁路 | **须显式**：政策简报、政策雷达、`/政策简报`、`/patent-brief`、`/patent-exam-policy`。「技能进化 / `/patent-evolve`」同一入口，仍先出简报 | `skills/patent-exam-policy/SKILL.md` |

## 路由

- 填表、线稿、CAD、公式、Word 出图在交底包 `prompts/` 与 `tools/`；解读填表用解读包 `prompts/fill_*`；过 WAF 的 `browser.py`、Markdown 转 Word 的 `md_to_docx.py` **各包自带副本**。
- **禁止跨包调用**其他子技能的 `tools/`。需要同一能力就用本包副本。
- 专利号或 PDF 且意图为「读懂」→ **优先解读**，不跑交底 Step 1–8。
- **禁止**因写交底或读专利自动进入政策简报、审查答复或申请文件。申请文件必须用户点名并给出交底目录；缺 schema / 线稿 / 交底书则停，引导先补交底。内容争议不阻塞主文件。
- 交底 Step 5 查新只用交底包轻量检索（一词一页）；按发明人/申请人等做著录检索时只用检索包，两者不要混用。

## 目录

```
SKILL.md                         # 本文件：子技能路由入口
skills/patent-disclosure/        # 交底（含填表/线稿/CAD/公式/docx）
skills/patent-application/       # 申请文件四件套（须显式；须指定交底目录）
skills/patent-search/            # 著录检索
skills/patent-reader/            # 解读
skills/patent-oa/                # 审查答复
skills/patent-exam-policy/        # 政策简报（技能进化为旁路）
```

## 环境与约定

- **默认语言**：面向用户的检索清单、交底书、申请文件、解读和审查答复用简体中文；脚本机读前缀与 JSON 字段名保持稳定。
- **脚本判读（尤其 Windows）**：stderr 有字 **不等于** 失败。以 **退出码 0** 和机读前缀为准：`EPUB_HITS_JSON:` / `EPUB_SEARCH_MD:` / `EPUB_SEARCH_JSON:` / `EPUB_CLASS_HINT:`、`PROBE:` / `BROWSER:`、`MERMAID:` / `DOCX:`、`APPLICATION_GATE:` / `APPLICATION_CLAIMS:` / `APPLICATION_NUMERALS:`。PowerShell 可能把 stderr 标成 `NativeCommandError`；**禁止**因此重跑安装或把查新降级 WebSearch。
- **专利类型**：未显式指定时交底**默认发明**。
- **脚本路径**：相对本技能仓库根（本文件所在目录）。整仓：`python skills/patent-disclosure/tools/…`。当前工作区不是本仓库时，把技能安装目录接到命令前面。单独拷走某一子包时，该包内用 `python tools/…`。不要写厂商环境变量。
- **用户产出**：写在当前工作区 `outputs/`（解读 `outputs/patent_reader/`，检索 `outputs/patent-search/`，政策 `outputs/exam-policy/`，审查答复 `outputs/oa/`，申请文件 `outputs/patent-application/`），不要写到技能安装目录或 `tmp/`。调用脚本时 cwd 用工作区根；`-o` / `-w` 用上述相对路径。

## 执行前核对

```
□ 已 Read 对应 skills/*/SKILL.md，未把本文件当交底/申请底稿/检索/解读正文
□ 交底查新未调用 patent-search
□ 著录检索未用交底一词一页结果冒充清单
□ 政策简报 / 审查答复 / 申请文件仅在显式触发时进入
□ 申请文件已指定交底目录；门禁未过未开写
□ 未跨包调用其他子技能的 tools/
□ 未把政策简报当成改技能；无点名未改交底包以外的目录
```
