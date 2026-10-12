# 从零 / 缺申请时的首轮调度

仅当 `start_mode` 为 `from_zero` 或 `from_disclosure`，且 `phase` 为 `intake` 刚结束或 `bootstrap_disclosure` / `bootstrap_application`。

## from_zero

1. 写 `paths.materials_dir`（用户项目或材料路径）。没有材料且用户只说「帮我写专利」→ `ask_human`（要领域、交底类型、任何草稿），不要编技术方案。
2. 将 `phase` 改为 `bootstrap_disclosure`，`round: 1`。`validate_docket.py` + `emit_tracker.py`。
3. **`Read` `prompts/dispatch_disclosure.md`**。初稿走交底全流程（对方 SKILL 的 Step 1–8），不是 merger。
4. 交底时间戳 md + docx 落盘后：填 `paths.disclosure_dir` / `disclosure_md`，`phase: wait_disclosure` → `bootstrap_application`。
5. **`Read` `prompts/dispatch_application.md`**。申请手必须带上交底目录。
6. 申请目录与 `问题清单.md` 出现后：写入 `paths.application_dir` / `issues_md`，在 `rounds` 追加第 1 轮记录，`phase: triage`，**`Read` `prompts/triage.md`**。

## from_disclosure

跳过第 3–4 步。确认交底目录可门禁（缺 schema/线稿则仍要交底包自己停，案卷记 `ask_human` 或 `dispatch_disclosure` 补材料）。然后从上面第 5 步申请手开始，仍记第 1 轮。

## 本文件禁止

- 在案卷包里直接写交底章节或权要。
- 首轮未出问题清单就 round_close。
- 从零直接 `bootstrap_application`。
