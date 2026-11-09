# 问人

`phase: ask_human`。把 `issues` 中 `disposition: ask_human` 且 `open` 的条目列成用户可直接回答的问题（每条一个问题，带 id）。

## 纪律

- 一次对话把当前 **`blocking: true`** 且 `open` 的项问完，不要拆成多次「先问一个」。
- 仅上述阻塞项未得到回答时，不得 `dispatch_disclosure` / `dispatch_application`，不得 `round += 1`。
- **发明人姓名、申请人、文头联系人**默认非阻塞：可列在回复里，文头保持「待填写」，**不**因此停留本 phase。
- 用户明确「跳过/以后再说」→ 该条 `status: deferred`，`disposition: defer`，可离开阻塞。
- 用户给了事实 → 记在 `evidence` 或 `human_queue` 备注，`status` 仍 `open` 直到交底/申请手落地后再标 `done`。若答案足够且只需申请手改书式，改 `disposition: application_fix` 后回 `triage`。

## 回案卷

更新 yaml → `validate_docket.py` → `emit_tracker.py`。下一 phase：`triage`（仍有阻塞则继续本 phase）或用户消失则 `terminal_blocked`。
