# 案卷接入

在 guardrails 之后执行。目标：定 `start_mode`、`case_id`、`patent_type`，并决定下一份 prompt。

## 1. 是否已有案卷

在工作区搜 `outputs/docket/**/docket.yaml`。用户点名了案件 slug 则只看 `outputs/docket/{slug}/`。

- 找到且用户要继续 → `start_mode: resume`，**`Read` `prompts/resume.md`**，结束本文件。
- 找到但用户要另开一案 → 新 `case_id`，不要覆盖旧 yaml。

## 2. 材料探测（不要问「是否进入案卷」）

按用户给出的路径与对话，判断：

| 条件 | `start_mode` |
|------|----------------|
| 无交底书时间戳 md、无申请四件套、要从头写 | `from_zero` |
| 有交底产出目录（含时间戳 md），无 `outputs/patent-application/` 下本案件四件套 | `from_disclosure` |
| 有申请产出目录且存在 `问题清单.md` | `from_application` |
| 交底和申请都有、用户说会稿/按清单闭环 | `from_application`（以最新申请目录为准） |

专利类型：用户口头指定优先；否则交底 intake 默认发明。从零且用户未说类型 → 记 `invention`，在 tracker 写「类型未口头指定，按发明调度；要实用/外观请说明」。

`case_id`：用户案件名或目录 slug，ASCII 连字符，不要空格。

## 3. 立案

```bash
python skills/patent-docket/tools/init_docket.py --case-id "{slug}" --mode {from_zero|from_disclosure|from_application} --type {invention|utility_model|design}
```

已有路径则追加：

```bash
python skills/patent-docket/tools/init_docket.py --case-id "{slug}" --mode from_disclosure --disclosure-dir "outputs/…"
python skills/patent-docket/tools/init_docket.py --case-id "{slug}" --mode from_application --application-dir "outputs/patent-application/…" --disclosure-dir "outputs/…"
```

成功：stderr/stdout 有 `DOCKET_DIR:` 与 `DOCKET_YAML:`。然后 **`Read` `docket.yaml`**，再进入：

- `from_zero` → `prompts/bootstrap.md`
- `from_disclosure` → 把 phase 视为将 `bootstrap_application`，读 `prompts/dispatch_application.md`（仍先过 bootstrap 里「缺申请」一节）
- `from_application` → `prompts/triage.md`

缺项目路径又要从零：在对话里要材料目录或粘贴说明，**不要**空跑交底挖点。材料不足记 `ask_human`，phase 可 `terminal_blocked`。
