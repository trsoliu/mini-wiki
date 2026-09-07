# 公式：材料优先，范式库仅起草

发明交底在写 **3.4.1** 前须落盘 **`formula_plan.yaml`**。  
**材料里已有的公式优先转录**（`origin: source`）；本目录范式库只给 **材料没有、需要技能补写** 的式（`origin: agent`）当起草菜单。

| 文件 | 作用 |
|------|------|
| [`paradigms.yaml`](paradigms.yaml) | 无原文时的起草菜单 + 全局规则（禁装饰音等，约束 agent 式） |
| [`../schemas/formula_plan.schema.yaml`](../schemas/formula_plan.schema.yaml) | 案件级 `formula_plan.yaml` 合同（含 `origin` / `omitted`） |

## 加载顺序（后者覆盖同 `id`）

1. 仓库 `references/formulas/paradigms.yaml`
2. 环境变量 `PATENT_FORMULA_PARADIGMS` 指向的 YAML/JSON
3. 案件目录 `formula_paradigms.yaml` 或 `formula_paradigms.json`（与交底输出同级）

查看合并结果：

```bash
python tools/formula_paradigms.py list
python tools/formula_paradigms.py list --case-dir outputs/某案
python tools/formula_paradigms.py show weighted_sum
```

校验案件公式计划：

```bash
python tools/check_formula_plan.py -i outputs/某案/formula_plan.yaml
python tools/check_formula_plan.py -i outputs/某案/formula_plan.yaml --eval
```

`--eval`：对可解析的简单式（`+ - * / min max`）代入 `numeric_example` 核对 `result`；求和/范数/分位等跳过并警告。  
`chemistry` 标签或 `\ce{` / 反应箭头：检查简单反应式原子守恒。`physics`/`si`：符号表单位族粗检（警告）。  
**禁止**把 source 复杂式改写成库内简单式，只为让 `--eval` 通过。

## 如何扩展一条范式

在覆盖文件中追加（保留 `version` / 可选 `rules`），供 **agent 起草** 使用：

```yaml
version: 1
paradigms:
  - id: my_shop_floor_oee
    name_zh: 产线 OEE 合成
    tags: [score, manufacturing]
    when_zh: 可用率×表现×质量
    latex: 'OEE = A \\cdot P \\cdot Q'
    notes_zh: A,P,Q ∈ (0,1]
```

`id` 用小写+下划线；写清 `when_zh` / `notes_zh`，否则易被误选。  
`combos` 可同样追加。

## 成文纪律（摘要）

- 每条式标记 `origin: source | agent`。source 对材料；agent 的 `paradigm_id`（及可选 `combo_id`）须∈合并后的库。
- 材料式多：按专利点勾选进 `equations`；不采用的写 `omitted`（出处 + 原因）。
- 默认 `rules.forbid_accents: true`：**agent 式**正文不要用 `\tilde`/`\hat`/`\bar` 等。source 式保真，装饰音校验为警告。
- 含 agent 式时须有可代入数值例。全为 source 时鼓励给，复杂式可不强求。
