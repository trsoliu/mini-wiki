# 申请文件 · 外观

`type=design` 后只走本文件。权要按外观书式写。视图检查与出图用本包脚本。

先 **`Read`** 本包 `references/design_view_cnipa.md`（与交底同文）。

沿用交底 `appearance_schema` 的 `claimed_faces` / `omitted_views` / `line_scope`（非默认六视）和 `figure_plan`。`claimed_faces` / 图题用官方全称（主视图、后视图、左视图、右视图、俯视图、仰视图、立体图）。

## 产出

- `视图选择.md`：选定**全线稿或全实拍**（同一件不得图片与照片混用）；入文图序、各图对应 `claimed_faces`；`omitted_views` 列出并写原因（相同、对称、无要点），**不要**为省略面补图。
- `简要说明.md`：产品名称、设计要点（可见造型/图案/色彩）、视图名称。省略视图用「后视图与主视图对称，省略后视图」这类用语，不要写功能、结构、材料工艺。不要写入检查清单。图题在文内图外正下方，不烧进像素。
- `实拍与线稿对应表.md`：同一视的干净实拍与线稿成对（交底对照用）；递交集合以 `视图选择.md` 为准。`photo_scene` 营销图不入。
- `视图检查清单.md`：漏视 / 虚线不一致 / 新事项风险。用本包脚本，不改像素。
- `问题清单.md`
- `figures/`：交底入文图**原样复制**（便于 Word 引用）。**禁止** `compose_application_figure.py`，禁止裁边、缩放、改 DPI、改像素。

## 对照（交付前，同一清单）

先跑本包检查（交底目录为 `--case-dir`，清单写到本申请产出目录）：

```bash
python skills/patent-application/tools/check_design_views.py \
  --case-dir <交底目录> \
  --out outputs/patent-application/{案件}_{时间戳}/视图检查清单.md
```

再用 `design_view_cnipa.md` 人工核一眼。不合格只写入清单与 `问题清单.md`，**不改原材料**：

- 入文视图集合能覆盖 `claimed_faces`；缺面记清单，不要默补六视或假面。
- `line_scope` 各视实线/虚线同一口径；未锁定记待核。
- `omitted_views` 在简要说明中均有对应一句，用语符合指南。
- 递交集合图照片不混；实拍未标成线稿；CAD 未入申请视图。
- 正投影关系、各视比例、图幅/DPI（JPEG、不超过 150mm×220mm、72–300 DPI）；线稿无尺寸线/中心线/阴影线、图内无图号。
- 透视棚拍未当合格正投影；`photo_clean` 符合 4.2.3。
- 故意省略面或源材料未见的面入了文 → 新事项风险，禁止补假面。
