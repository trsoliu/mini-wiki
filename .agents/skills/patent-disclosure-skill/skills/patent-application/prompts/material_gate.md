# 申请文件 · 材料门禁

只拦**缺文件**。内容争议不要在这一步停。

```bash
python skills/patent-application/tools/material_gate.py --case-dir <交底目录>
```

可选：`--disclosure`、`--type invention|utility_model|design`。

以退出码和 `APPLICATION_GATE:` 为准。PowerShell 红字不是失败。

| 退出码 | 动作 |
|--------|------|
| 0 | 继续 |
| 2 | **终止**，列出缺失项，引导交底技能 |
| 1 | 修正路径后再跑 |

| 类型 | 必须存在 |
|------|----------|
| 发明 | 交底书 `.md` 或 `.docx` |
| 实用新型 | 交底 + `structure_schema` + `figure_plan` + 入文线稿文件 |
| 外观 | 交底 + `appearance_schema` + `figure_plan` + 入文线稿 + 入文实拍 |
