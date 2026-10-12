# 派工申请文件

适用 `phase`：`bootstrap_application`、`dispatch_application`、`wait_application`。

先 **`Read` `references/handoff_contract.md`**。

## 读哪个申请入口

**只 `Read` `skills/patent-application/SKILL.md`**，并指定 **`paths.disclosure_dir`**。缺交底目录不得开写。

| 本包 phase | 申请侧 |
|------------|--------|
| `bootstrap_application` | 全套四件套（对方 intake → 门禁 → 成稿 → 问题清单） |
| `dispatch_application` | 已有申请产出则走对方 **迭代**（新时间戳目录）；用户要求整案按新交底重出则按对方 SKILL 重跑成稿，仍另存 |

本轮 `application_fix` 的 issue id 一并交给申请手。`disclosure_fix` 刚完成时，申请手必须以**新交底路径**为准，不要沿用旧交底摘要。

## 回来之后

1. 填 `paths.application_dir`、`paths.issues_md`
2. 若本轮是新的一套申请交付：把该次记入 `rounds`（见 `max_rounds.md`），必要时 `round` 加 1（仅在「第 2、3 套申请」时；首套保持 1）
3. `phase: wait_application` → `triage`
4. 校验 + emit tracker
5. **`Read` `prompts/triage.md`**

申请包因未点名而拒绝：案卷语境下用户已经在走会稿，视为已点名申请文件；仍须有交底目录。若对方 prompt 写死「须用户点名」而你在同一会话，以用户触发案卷为准继续读申请 SKILL 执行。
