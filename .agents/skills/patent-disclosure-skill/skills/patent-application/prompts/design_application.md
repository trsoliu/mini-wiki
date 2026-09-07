# 申请文件 · 外观

`type=design` 后只走本文件。不要写发明式权要。不要导出 TIFF。

沿用交底 `appearance_schema` 的 `claimed_faces` / `omitted_views`（非默认六视）和 `figure_plan`。

## 产出

- `视图选择.md`：入文图序、各图对应 `claimed_faces`；`omitted_views` 列出并写原因（相同、对称、无要点），**不要**为省略面补图。
- `简要说明.md`：产品名称、设计要点（可见造型/图案/色彩）、视图名称。省略视图用「后视图与主视图对称，省略后视图」这类用语，不要写功能、结构、材料工艺。
- `实拍与线稿对应表.md`：同一视的干净实拍与线稿成对；`photo_scene` 营销图不入。
- `问题清单.md`

## 对照（交付前）

- 入文视图集合 = `figure_plan` 中 `use_in_disclosure: true` 的条目，且能覆盖 `claimed_faces`；缺面记问题清单，不要默补六视。
- `omitted_views` 在简要说明中均有对应一句。
- 实拍未标成线稿；CAD 未入申请视图。

申请侧对入文线稿/实拍用 `compose_application_figure.py` 升格到产出 `figures/`（黑白、按内容截取，图号只在简要说明），不要直接扔交底原图进 Word。
