---
name: patent-exam-policy
description: "给交底用的政策简报：对照国知局近期口径，说明对交底写法/本稿的影响。技能进化仅为旁路，须另点名才改文件。"
user-invocable: false
---

# 政策简报（交底用）

须用户点名（政策简报 / 政策雷达 / 审查政策更新 / `/政策简报` / `/patent-brief` / `/patent-exam-policy`）。  
**默认只出简报，不改技能。** 「技能进化 / `/patent-evolve`」走同一套检索，但仍先出简报；只有用户再点名改技能时才 `Read` `apply_after_confirm.md`。

1. **`Read`** `prompts/guardrails.md` → `intake.md`
2. **`Read`** `prompts/research.md`（A/B 分层种子 + 实用新型/外观/实施细则 + 相对上次增量）
3. **`Read`** `prompts/emit_backlog.md` → `outputs/exam-policy/`（含施行日历）
4. **仅当**用户明确要求改交底技能 → **`Read`** `prompts/apply_after_confirm.md`

主题→文件：`references/topic_prompt_map.md`。信源种子：`references/sources.yaml`（A 可支撑交底口径；B 与地方预审不得单独改技能）。
