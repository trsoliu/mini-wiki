# LaTeX 源码扫描（Step 2 子流程）

仅当 `project_scan.md` 门禁在扫描根内发现 **`.tex`** 后 **`Read` 本文**。无 `.tex` **不要**加载。不是独立步骤，不必编译，不问用户要源码。

## 目标

公式以 `.tex` 为准；产出短清单供后续 `formula_plan`。

读完主文件、公式词典，以及引用图中属本发明方法/模型/公式的部分。不读引用图外的 `.tex`、已归为综述/实验/附录的部分、同题 PDF 转出的 Markdown。清单落盘后，成文只认清单，不再载入 `.tex`。

分类依据路径、注释、`\section` / `\chapter` 的**含义**。下表为参考词表，非封闭枚举；未命中时整文件 `Read`。单文件文稿按 `\section` 分段归类。

## 禁止当正文

- 编译产物：`.aux`、`.log`、`.out`、`.toc`、`.lof`、`.lot`、`.bbl`、`.blg`、`.synctex.gz`、`.fdb_latexmk`、`.fls`
- `.bib` 默认不读
- 插图（`.pdf` 图、`.png`、`.eps`）不按本文读

## 流程

### 1. 发现引用图

1. 主文件：优先 `main.tex`；否则论文目录内**唯一**含 `\documentclass` / `\begin{document}` 的 `.tex`。不得把某一章当作全文。
2. **只 `Read` 主文件**，按 `\input` / `\include`（及 `subfiles`）出现顺序列出路径（相对主文件目录）。
3. 不得对 `Glob *.tex` 的每一个文件 `Read`（同树可能含旧稿、幻灯片、补充材料）。

### 2. 参考词表与分类

| 类别 | 处置 | 参考词表（文件名 / 节标题，中英均可） |
|------|------|--------------------------------------|
| 公式词典 | 必读 | `macros`、`def`、`cmd`、`symbol`、自写 `.sty`；主文件 preamble 或章节内的 `\newcommand` / `\def` |
| 本发明方法 | 整文件 `Read` | `method`、`model`、`approach`、`algorithm`；方法、模型、算法、方案、问题建模、系统设计 |
| 非方法章 | 默认不读 | `related`、`intro`、`experiment`、`ablation`、`appendix`、`proof`、`ack`、`supplement`；相关工作、研究现状、引言、绪论、实验、仿真、消融、附录、证明、致谢 |
| 未命中上列 | 整文件 `Read` | `chap3`、`body` 及未列入上列的标题 |

保留文件中的嵌套 `\input` / `\include` 须一并跟随。单次 `Read` 被工具截断时，用 offset 续读至文件结束，不得改为只抽取公式。

### 3. 工作集预算

编号展示公式列入清单至多约 20 条，优先本发明方法/模型中的式。其余写入 `formula_plan.omitted`。不得为求全而阅读附录证明。

### 4. 同题 PDF

存在完整 `.tex` 引用图时，公式以源码为准，`pdf_to_md` 文本层不得覆盖。不得将该 PDF 转出的 Markdown 作为公式来源再次阅读；缺图时再按页提取。

### 5. 落盘清单

写入 **`outputs/{案件标识}/tex_formula_inventory.md`**（案件目录尚未建立则先建；禁止写入用户扫描根 / `knowledge/`）。至少包含：

- 主文件路径、已读公式词典、跳过的章节
- 表：出处（`文件:行号` 或 `\label`）、LaTeX 原文、一句话说明在算什么（含式后条件）
- `source_kind: tex`（默认已核）

Step 7 撰写 `formula_plan` 时只 `Read` 本清单并勾选，不再将 `.tex` 载入成文上下文。清单缺失或用户新补 `.tex` 时，重新执行本文。

无 `.tex` 时不创建本文件。
