# 保护型 1+N · 技术分解

用户已答应做保护型 1+N（或点名「专利布局 / 专利围栏 / 族树」强开）。**先分解，不要直接立项、不要先打分、不要批量写交底。**

对照**已定稿首篇交底 + 项目材料**，拆成可指认的层，不编新结构。

| layer | 写什么 |
|-------|--------|
| `principle` | 原理 / 必要特征层（未来核心独权候选） |
| `module` | 可替换模块、局部结构 |
| `chain` | 上下游：检测、接口、制备、装配、使用方法 |
| `scenario` | 应用场景、工况、产品形态 |

每条必须有 `source`（交底章节标题或材料路径）。禁止无出处节点。同一独权的下位参数不要拆成独立节点。

落盘 `outputs/{案件}/fence/decompose.yaml`：

```yaml
version: 1
source_disclosure: outputs/…/….md
nodes:
  - id: D1
    layer: principle
    summary: …
    source: 第五章 / 3.4
  - id: D2
    layer: scenario
    summary: …
    source: 第二章背景
```

校验：

```bash
python skills/patent-disclosure/tools/fence/check_layout.py --decompose outputs/{案件}/fence/decompose.yaml
```

成功须见 `LAYOUT_OK:decompose`。然后 **`Read` `design_around.md`**。
