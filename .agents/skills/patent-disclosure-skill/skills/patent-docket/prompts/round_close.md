# 轮次收口

`phase: round_close` 或已进入 `terminal_*`。

## 对照清单

`Read` 本轮 `paths.issues_md` 与上一轮申请目录中的 `问题清单.md`（若有）。对 `issues[]`：

- 已落地 → `done`
- 故意不做 → `deferred`
- 仍在 → 保持 `open`

写 `ROUND-{n}.md`（可选，短）：本轮 phase 路径、关闭的 id、仍 open 的 id。

## 下一状态

1. 无 `open` → `terminal_complete`
2. `len(rounds) >= max_rounds` 或 `round >= max_rounds` 且本轮申请已核过 → 仍有 `open` 则 `terminal_max_rounds`，否则 `terminal_complete`
3. 未满 3 轮且仍有 `open`：
   - 有阻塞 `ask_human` → `ask_human`
   - 剩余 `open` 仅为非阻塞 `ask_human`（著录项目、可选补材、未点名的范围策略），且本轮已有申请交付、无 `disclosure_fix` / `application_fix` → 将这些条改为 `defer`，再按第 1 条走 `terminal_complete`。**禁止**为空转加轮次
   - 否则 `round` 加 1，转 `triage`（让分诊再决定派工）或直接 `dispatch_*`（若分诊已在本轮做过且处置未变）

第 3 轮停后：面向用户列出残留条目和路径，请人接手；**禁止**再派工。

## 终态陈述（强制）

同一条回复先写清路径（案卷目录、`docket.yaml`、当前 round、终态 phase、交底路径、申请路径），**最后**用固定标题：

## 交付后请确认

1. **内容待确认 / 可调整：** 问题清单路径、未关 id；已落地/故意不做的可一句带过。不要宣称授权或格式审查已过。
2. **下一步 / 旁路：** 未满三轮且仍有须人处理的 `open` → 可说「按清单改」或「会稿」。已 `terminal_max_rounds` 或第 3 轮停后 → 列出残留条目和路径，请人接手，**禁止**再派工。不要在此节把审查答复或政策简报列为下一步。

`validate_docket.py` + `emit_tracker.py`。
