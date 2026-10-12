# 分诊

`phase` 必须是 `triage`。先 **`Read` `references/issue_taxonomy.md`** 与 `references/dispositions.yaml`。

## 输入

- `paths.issues_md`（申请包 `问题清单.md`）。没有该文件 → 不得假装无问题；回 `wait_application` 或 `ask_human`。
- 需要判断「是不是真问题」时，**`Read` 清单里点到的交底/申请文件片段**（按路径），不要凭记忆。

## 动作

1. 把清单条目映射为 `issues[]`（稳定 `id`：`I-01` 起；已有 id 则复用，不要每轮重编号导致无法对照）。
2. 每条填 `kind`、`disposition`、`blocking`、`status`、`round_opened`、`summary`（一句）、`evidence`（文件路径+标题，可选）。
3. 机器检查类抄清单原意，不要放大成授权结论。
4. 跑 `validate_docket.py` 与 `emit_tracker.py`。

## 下一 phase

按**未关闭条目**的最高优先级（上者优先）：

1. 任一条 `ask_human` 且 `blocking` 且 `open` → `ask_human`
2. 任一条 `disclosure_fix` 且 `open` → `dispatch_disclosure`
3. 任一条 `application_fix` 且 `open` → `dispatch_application`
4. 仅有 `defer` / `ignore` / 已 `done`，或仅有非阻塞 `ask_human` 仍 `open`（如发明人未填）→ `round_close`
5. 全部 `done` 或 `ignore` → `round_close`（将走向 `terminal_complete`）

本步**只改案卷**，不改交底、不改申请正文。
