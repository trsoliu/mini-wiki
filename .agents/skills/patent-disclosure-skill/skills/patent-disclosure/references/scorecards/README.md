# 交底旁路评分表（可外挂替换）

默认表 [`gbt42748_fence.yaml`](gbt42748_fence.yaml)：法律 / 技术 / 经济（GB/T 42748 三维）+ 围栏可行性。  
用于保护型 1+N **立项之后**的弱校验（至少一篇可写外围、材料够），**不**决定要不要问用户做布局。  
人读的作答表、门槛表和结论写在同案 `fence/专利布局.md` 的 **立项校验** 章。  
**未决不得正分。** 不发「高价值专利」证书，说明稿与对话也不写「高价值达标」。

## 加载顺序（后者整表替换，不按题合并）

1. 仓库 `references/scorecards/gbt42748_fence.yaml`
2. 环境变量 `PATENT_DISCLOSURE_SCORECARD` 指向的 YAML
3. 案件目录 `fence_scorecard.yaml`（与交底产出同级，或 `fence/` 下）

换表时保持 `id` / `items` / `thresholds` 形状，见 `references/schemas/scorecard.schema.yaml`。

```bash
python skills/patent-disclosure/tools/fence/check_scorecard.py --table
python skills/patent-disclosure/tools/fence/check_scorecard.py -i outputs/某案/fence/scorecard.yaml
```
