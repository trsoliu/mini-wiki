# 审查答复辅助 · 总则

## 定位

可选、默认关闭。显式触发后进入；**主场景是问和答、出草稿**：

1. **审查文档问答 / 自动答复草稿**（检索黄金案例；同点多策略相对分，分差+保范围门槛选定后直接出稿；事后摘要；可换策略另存新稿；**用户确认采纳后**才套模板出意见陈述 Word）  
2. **案例脱敏入库**（历史通知书/答复 → Obs 笔记；向量可选；库薄时写入 **`## 交付后请确认`**）

**不**替代专利代理签字与正式递交；默认产出为内部草稿。Word 仅为确认后的陈述正文，不是官方电子表单。

## 禁止

- 未脱敏入库含客户名、电话、未公开核心参数的原文  
- 无检索命中（或未说明库为空）就长篇「糊弄」意见陈述  
- 修改超原申请记载范围却不标注风险  
- 无人审确认即将草稿当作已递交文件，或未确认就出意见陈述 Word  
- 将 API Key 写入仓库或在回复中回显完整密钥  
- 把非历史案材料写入 `cases/history` 或案例向量，并当作 `case_id` 引用  
- 把相对分写成授权率或授权概率；无门槛时按稳妥分最高一路写稿

## 配置（对话交互 · 向量可选）

**必须 `Read`** `skills/patent-oa/prompts/configure_embedding.md`，按问答收集后写文件：

1. `python skills/patent-oa/tools/config.py recommend`  
2. 问用户：跳过 / 推荐智谱 / 其他预设 / 自定义（URL+模型+维度+Key）  
3. 用户提供后：  
   - `config.py skip-vector`，或  
   - `config.py set --preset … --api-key …`（自定义则带 `--base-url --model --dimensions`）  
4. **设置后必须自检**：`set` 默认含 `selftest`；也可 `config.py selftest`  
5. 自检通过且需重建时，人确认后 `rebuild_vectors.py --confirm`  
6. 向量超时/失败：检索回退标签（`tags_fallback`），流程不中断  

配置：`{Documents}/patent-disclosure-skill/oa/embedding.config.yaml`  
密钥：同目录 `embedding.secrets.yaml`（仅本机）

## 草稿交付（事后摘要，不中断）

写完草稿后用简短摘要交代各条主策略、同点相对分与换策略方式。摘要里写明本稿是内部草稿，复核后才能递交。

用户说换策略（如「按修改权利要求再出一稿」）→ 另存新时间戳草稿，保留旧稿。Word 仍等用户采纳。

用户明确采纳某一份草稿（「用这一稿 / 出 Word / 可以定稿 / 采纳」）→ **`Read`** `assets/opinion_statement.md`，写成 `outputs/oa/{案件}/{会话}/意见陈述_{时间戳}.md` 后跑本包 `tools/emit_opinion_docx.py`。递交稿只写给审查员：不写内部策略分、`case_id`、对照表或 `Fk`。

新颖性/创造性且通知书列了对比文件时，出草稿后用本包 `write_intake.py` / `emit_chart.py` 把对照表写到同一会话目录。表留在 xlsx，不写入陈述正文。

摘要之后按 **`skills/patent-oa/prompts/soft_nudge.md`** 决定是否在对话末尾加库厚度提示（至多 2 句；不入草稿正文）。
