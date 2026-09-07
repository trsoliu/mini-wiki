# 实用新型 · 模版参考

与 `disclosure_builder.md` 配套；填表示例，非强制数值。

## 部件表（示例）

| 件号 | 名称 | 形状要点 |
|------|------|----------|
| 1 | 散热基板 | 板状 |
| 2 | 鳍片 | 垂直阵列 |
| 3 | 弹性卡扣臂 | 向下延伸 |
| 4 | 钩部 | 向内弯折 |

## 连接关系表（示例）

| 自 | 至 | 类型 | 位置 |
|----|----|------|------|
| 2 | 1 | 一体成型 | 上表面 |
| 4 | 5 | 卡扣 | 板缘缺口 |

## 欲保护点短句示例

> 一种散热片安装结构，包括基板与自基板两侧向下延伸的弹性卡扣臂，臂末端设向内钩部，用于与电路板缘缺口咬合……

## 附图引用示例

正文插图**只来自**案件目录 `figure_plan.yaml` 中 `use_in_disclosure: true` 的条目（按 `fig`）。

```yaml
# figure_plan 片段示例（非完整合同）
figures:
  - fig: 1
    role: assembly
    path: knowledge/assets/fig1_assembly_side.png
    covers: ["1","2","3"]
    kind: lineart
    score: 90
    use_in_disclosure: true
    reason: 装配关系清晰
    relates_to: []
  - fig: 2
    role: detail
    path: knowledge/assets/fig2_snap_detail.png
    covers: ["3","4","5"]
    kind: lineart
    score: 85
    use_in_disclosure: true
    reason: 卡扣局部
    relates_to:
      - fig: 1
        relation: detail_of
        note: 图1卡扣局部放大
```

```markdown
如图1所示，基板1上表面设鳍片2……；如图2为图1的局部放大，钩部4与板缘缺口咬合……。
```

教学样例目录：`examples/example_utility_model_ev_powertrain/`（电驱桥 brief + 展台实拍；须自填 StructureSchema + figure_plan；线稿文生图；brief 为教学虚构）。
