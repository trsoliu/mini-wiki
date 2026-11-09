# 问题分诊口径

先读申请目录里的 `问题清单.md`，再逐条写入 `docket.yaml` 的 `issues[]`。不要把清单整文件贴进交底或申请正文。

## 是不是真问题

| 判断 | 做法 |
|------|------|
| 机器前缀已失败（PNG / OMML / 对照表 / 权要审计）且路径上文件确实缺或报错 | **真问题**，按类派工 |
| 清单写「保护范围过宽」但交底第五章已限定、独权与 3.x 一致 | 可 `ignore`，写一句依据（引用交底/权要路径+标题，不要编条款） |
| 交底没写的结构、参数、步骤，申请却当缺口要「补全」 | **真问题**，但只能 `ask_human` 或 `disclosure_fix`（有材料可补时）；禁止代发明人编 |
| 发明人姓名、申请人、交底文头联系人（电话/邮箱） | 记入清单，`ask_human` 且 **`blocking: false`**。文头可写「待填写」。**不**挡交底/申请交付，**不**挡后续轮次 |
| 点名场景图是否入文 | **必须问人**，`blocking: true` |
| 用户已要求改独权但未说明怎么改 | **必须问人**，`blocking: true` |
| 清单上的范围备选、是否维持现独权 | `ask_human`，**`blocking: false`**；已按交底第五章选定一种写法即可继续轮次 |
| 同一格式问题连续两轮同文案再出现 | 第三轮改为 `ask_human` 或 `defer`，不要为销项空转 |

## kind → 默认 disposition

| kind | 含义 | 默认 disposition |
|------|------|------------------|
| `machine_format` | PNG、OMML、摘要字数、对照表、件号审计 | `application_fix` |
| `claim_form` | 所述前置、独权步骤、从属层、书式 | `application_fix` |
| `scope_strategy` | 保护范围过宽/过窄、权要备选 | `ask_human`，默认 **`blocking: false`**。仅当用户已要求改独权却未说明怎么改时 `blocking: true`。用户已点名写法才可 `application_fix` |
| `disclosure_gap` | 交底歧义、缺连接/实施例/步骤、查新未复做 | `disclosure_fix`；材料里没有对应事实则改 `ask_human` |
| `human_fact` | 发明人/申请人/文头联系人；点名图是否入文 | `ask_human`。著录项目默认 **`blocking: false`**；点名图是否入文默认 **`blocking: true`** |
| `noise` | 重复、已过时、与本案无关 | `ignore` |

## disposition

见 `dispositions.yaml`。`disclosure_fix` 做完必须 `dispatch_application`。`application_fix` 不回交底。仅当 `ask_human` 且 **`blocking: true`** 且 `open` 时，不得加 round、不得 `dispatch_*`。非阻塞问人（含发明人未填）可留在清单上，轮次照常走。
