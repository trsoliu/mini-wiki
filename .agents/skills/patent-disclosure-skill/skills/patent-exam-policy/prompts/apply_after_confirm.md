# 技能进化旁路 · 确认后应用

**仅当**用户已明确回复「按简报改交底技能」「全部采纳」或「采纳 E…」后执行。  
默认政策简报 **走不到这里**。执行前再 Read `guardrails.md` 与 `references/topic_prompt_map.md`。

## 默认可写白名单

只改这些（路径必须带包前缀，且主题能在 `topic_prompt_map.md` **交底表**对上）：

- `skills/patent-disclosure/prompts/**`
- `skills/patent-disclosure/references/**`
- `skills/patent-disclosure/SKILL.md`

仓库根 `SKILL.md`：**不**随「全部采纳」；仅当被点名的 E* 影响面=路由。  
`skills/patent-application/`：**不改**（即使点名 E*；申请书式只在简报第 4 节说明）。  
其他子包与本包：仅当用户点名的 E* 已写明该包完整路径。

## 步骤

1. 打开对应 `outputs/exam-policy/POLICY-*.md` 附录 E*，只处理本次确认范围内的行。  
   - 「全部采纳」/「按简报改交底技能」= 影响面=交底、路径均在白名单内、且交底表有对应主题。其余 **搁置**。  
   - 「采纳 E…」= 只改点名编号；超出白名单则跳过并说明。  
2. 将建议落实为对白名单文件的 **最小必要改动**（勿借机大重构）。  
3. 在同目录写 `POLICY-YYYYMMDD-HHMM.status.md`：

```markdown
# POLICY-… 采纳状态
- 确认时间：…
- 用户指令：…
- 已采纳：E…
- 已搁置：E…
- 已改文件：
  - path — 一句话
- 未改原因（若有）：…
```

4. 若用户要求「沉淀到 docs/」：将简报 **复制** 到本包 `docs/POLICY-….md`（可提交）；**不要**把整个 `outputs/` 取消 ignore。  
5. 向用户汇报改了哪些文件；提醒：法规解读≠法律意见，重要案件仍须代理人复核。

## 禁止

- 简报尚未点名改技能时进入本文件并改 prompts  
- 扩大采纳范围到用户未点名的 E*  
- 「全部采纳」时改解读 / 检索 / 审查答复 / 申请包 / 本包 / 根 `SKILL.md`  
- 向 `skills/patent-application/` 写入（申请书式只说明、不进化）  
- 根据 C 级信源改技能  
- 仅根据 B 源（发布会、答问、典型案例、司法解释）改技能  
- 把未施行局令写成当前交底硬性要求  
- 写入欺瞒审查或对抗审查系统的话术
