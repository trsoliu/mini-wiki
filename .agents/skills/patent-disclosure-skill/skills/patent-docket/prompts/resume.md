# 续跑已有案卷

`outputs/docket/{case_id}/docket.yaml` 已存在时用本文，不要 `init_docket.py` 覆盖。

1. **`Read` `docket.yaml`** 与 `TRACKER.md`（若缺则 `emit_tracker.py` 补）。
2. `python skills/patent-docket/tools/validate_docket.py --yaml {路径}`。失败则先修 yaml，禁止带病派工。
3. `phase` 已是 `terminal_*`：只向用户报告终态与残留 issues，**不要**自动开第 4 轮。用户明确「新开一轮案卷」才新 `case_id` 或用户点名重置（须新 yaml，旧文件保留）。
4. `phase` 为 `ask_human`：先 **`Read` `prompts/ask_human.md`**。用户本轮已回答则改条目 status，回到 `triage`。
5. 其他 phase：按根 `SKILL.md` 阶段表 **只读一份** 对应 prompt，从中断点继续。
6. 核对 `paths.*` 是否仍指向最新时间戳目录；若用户又交了更新的交底/申请，改 yaml 再校验，不要沿用过期路径。

禁止把 resume 当成 from_zero 重跑 Step 1–8。
