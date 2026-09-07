---
name: patent-application
description: "申请文件：把已有交底写成权利要求书、说明书、摘要与说明书附图。须指定交底目录；仅缺材料才终止。内容争议写入问题清单，不阻塞主文件。交付后对话末尾须给出清单路径并摘要条目。已有产出上改稿则另存新时间戳目录。须显式触发。"
user-invocable: false
---

# 申请文件

须用户点名（申请文件 / 申请底稿 / 申报材料 / 权利要求书 / `/申请底稿` / `/patent-apply`），并**指定交底材料目录**。  
缺交底书 / schema / 线稿则**终止**，引导先用交底技能补齐。内容歧义**不阻塞**：先出主文件，缺口写入 `问题清单.md`。交付后对话末尾须给出该文件路径并摘要条目（见 `issues.md`）。

主交付是**四件套**（Markdown + Word + 黑白图）。

1. **`Read`** `prompts/guardrails.md` → `intake.md`
2. 已有申请产出上改稿（未要求整案重写）：**`Read`** `iteration_context.md` → `iteration.md`（新时间戳目录、出 Word、问题清单），然后结束，不要再走第 3–5 步
3. 跑 `tools/material_gate.py --case-dir <交底目录>`；退出码 2 则停
4. 发明 / 实用新型：`claim_strategy.md` → `claims_builder.md` → `figures.md` → `specification_builder.md` → `numeral_register.md` → `consistency.md`
5. 外观：只走 `design_application.md`
6. 本包 `tools/emit_application_docx.py` 出 Word；**`Read`** `issues.md`，写 `问题清单.md`（不入正式文件），并在**同一条交付回复末尾**给出路径、摘要条目、请用户先看清单

整仓路径：`python skills/patent-application/tools/…`。  
产出：`outputs/patent-application/{案件标识}_{时间戳}/`。禁止跨包调用其他子技能 `tools/`。不做 TIFF，不做请求书 / 费减 / CPCNS。
