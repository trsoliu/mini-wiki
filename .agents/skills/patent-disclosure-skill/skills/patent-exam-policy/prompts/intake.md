# 政策简报 · 录入（Intake）

执行前须先 **`Read`** `skills/patent-exam-policy/prompts/guardrails.md`。

## 何时进入

用户显式提到例如：政策简报、政策雷达、审查政策更新、交底口径是否过时、`/政策简报`、`/patent-brief`、`/patent-exam-policy`。  
「技能进化」「自进化」「`/patent-evolve`」「`/技能进化`」也进入本流程，但仍**先出简报**；改技能只当旁路，须再点名。

**禁止**因「写交底 / 读专利」自动进入本流程。

## 可选确认（信息不足时问 1–2 个）

```
1) 关注范围：审查工具 / 申请客体 / 程序通识 / 实用新型 / 外观 / 全部（默认）？
2) 时间窗：近 12 个月（默认） / 近 6 个月 / 自定义起止？
```

可跳过；跳过则默认：**全部范围 + 近 12 个月**，以中国国知局为主。  
默认「全部」必须覆盖实用新型明显创造性、局部外观 / GUI / 相似外观、实施细则，并做施行日历（已公布未施行单独成表）。  
若工作区已有交底定稿（`outputs/` 下带时间戳的 `.md`），简报须尝试对照本稿，不必再问。

## 输出约定

- 目录：`outputs/exam-policy/`（已被 gitignore）  
- 文件：`POLICY-YYYYMMDD-HHMM.md`（本地时区；分钟两位；内容是政策简报）  
- 默认**不**写 `.status.md`、**不**改 prompts  
- 技能进化旁路仅在用户点名后走 `apply_after_confirm.md`

## 下一步

1. **`Read`** `skills/patent-exam-policy/prompts/research.md` → A/B 分层种子、增量、施行日历、抓取  
2. **`Read`** `skills/patent-exam-policy/prompts/emit_backlog.md` → 写简报（含施行日历）  
3. 展示简报结束话术（见 guardrails）；**不要**把「全部采纳」当成默认下一步
