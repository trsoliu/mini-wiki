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

## 1.1 比对表（实用新型）

与发明同一套表式（见 `../invention/template_reference.md` §1.1 与 **`disclosure_builder.md` §7.10「Fk 出场」**）：编号单独成列，「本案怎么做」写部件与连接；表后特征一览。**禁止**「是（F1）」叠在最后一列，**禁止**列名叫「本专利权要」。第三章、第六章用件号，不用 Fk 当主语。第四章写完整效果句，句末可括注（F1）。

| 编号 | 对比点 | 对比文献 | D1 / 对比文献怎么做 | 本案怎么做 |
|------|--------|----------|---------------------|------------|
| F1 | 接触压力传递路径 | D1 | 螺钉穿散热器，螺母与弹性件调节预紧 | 倒U形弹性压紧桥跨越导热压板，两端经两侧弹性支撑柱传到基板承力区 |
| F2 | 罩体与基板连接 | D1 | 未公开罩设于压紧组件外侧的可拆导流罩 | 防尘导流罩顶板设孔阵列，下缘卡扣与基板可拆卸配合 |
| F3 | 罩体与压紧件的气流关系 | D1 | 无跨越压板的桥式压紧件，也无罩—桥间隙 | 导流罩顶板与压紧桥之间预留气流间隙 |

**特征一览**：F1 弹性承力路径；F2 可拆导流罩；F3 绕流间隙。

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
