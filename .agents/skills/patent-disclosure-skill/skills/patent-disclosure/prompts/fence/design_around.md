# 保护型 1+N · 突围路径

分解已落盘。对拟定**核心独权**逐条必要特征做全面覆盖 / 等同列表：**先列表，再决定立项，不是对抗生成循环，也不是 GAN。**

只根据交底与材料判断，不改稿、不编新结构。

对每个核心特征问：别人做同类产品时，会不会

- `replace` 换成便宜件/等价结构  
- `omit` 省掉这一步仍能用  
- `equivalent` 换说法或换检测点仍落到同一效果  

| 字段 | 取值 |
|------|------|
| `commercial` | `yes` 商业上真会走 / `no` / `unknown` |
| `disposition` | `satellite` 值得单独立项 / `dependent` 放核心从属 / `drop` 材料不够或无商业意义 |

规则：

- `unknown` → 默认 `dependent`，**不得** `satellite`  
- 材料撑不住单独实施 → `drop`  
- 核心独权下位（参数、实施例细节）→ `dependent`，禁止 `satellite`  
- 只有商业上真会走、且能单独实施的路径，才进入后面的外围候选  

落盘 `outputs/{案件}/fence/design_around.yaml`：

```yaml
version: 1
core_ref: D1
rows:
  - feature: …
    move: replace
    commercial: yes
    disposition: satellite
    note: 换铰链仍能锁合
  - feature: …
    move: omit
    commercial: unknown
    disposition: dependent
    note: 是否省略未知，留从属
```

校验：

```bash
python skills/patent-disclosure/tools/fence/check_layout.py --around outputs/{案件}/fence/design_around.yaml
```

成功须见 `LAYOUT_OK:around`。然后 **`Read` `matrix.md`**。
