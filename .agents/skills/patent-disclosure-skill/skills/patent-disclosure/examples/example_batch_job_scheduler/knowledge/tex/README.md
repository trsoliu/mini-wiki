# tex / 虚构论文源码链（不必编译）

演练 Step 2 的 **`prompts/tex_scan.md`**（由 `project_scan.md` 门禁按需加载）。与 `docs/architecture.md`、`pkg/scheduler` 口径一致，均为虚构。引用图：

1. `main.tex`（主文件，含 `\documentclass`）
2. `macros.tex`（`\MatchScore` 等公式词典；不可跳过）
3. `sections/method.tex`（式 (1) 匹配分、式 (2) 限频条件）

仍须写入案件目录 **`tex_formula_inventory.md`**，后续 `formula_plan` 只认清单。跳过若出现的 `.aux` / `.log`。同题若再扫 PDF，**公式以本链为准**，`source_kind: tex`。
