# 外观设计 · 模版参考

与 `disclosure_builder.md` 配套。

## 设计要点列表示例

1. 台灯整体由圆盘底座、多关节折臂与弯月形（或梯形）灯头构成。  
2. 底座为正圆形，中央设立柱/凸台接口。  
3. 灯头为细长弧面；灯臂与灯头连接处可具环形调节件等可见造型特征。

## 视图清单示例

原材料路径仅供识图；**交底入文**以 `figure_plan.yaml` 为准。干净实拍与线稿都入文（md + Word）；场景图默认 `use_in_disclosure: false` 或 `role: reference`。CAD 不入文。

| fig | role | 示例 path | kind | 入文？ | relates_to（示意） |
|-----|------|-----------|------|--------|-------------------|
| 1 | perspective | `assets/view_perspective.jpg`（裁产品区更佳） | photo_clean | 是 | `same_state` → 2 |
| 2 | perspective | `lineart_assist/view_perspective_lineart.png` | lineart | 是 | `same_state` → 1 |
| 3 | ortho | `assets/views_ortho.jpg` | photo_clean | 是 | `alternate_view` → 1 |
| 4 | ortho | `lineart_assist/view_ortho_lineart.png` | lineart | 是 | `same_state` → 3 |
| 5 | detail | `assets/view_arm_detail.jpg` | photo_clean | 是 | `detail_of` → 1 |
| — | reference | `assets/mi_desk_lamp_pro.jpg` 等重场景 | photo_scene | 否 | 可不写 |

先判立体/平面与要点落面，再定正投影；仅要点涉及六个面才收齐六面。相同/对称/无要点的面写入 `omitted_views` 供简要说明，不要默认六视。要点落面缺源图才用 `uncertain`。多视联读关系写入 `figure_plan.relates_to`。

## 与在先差异短句示例

> 相对直杆台灯，本案折臂折线与弯月灯头轮廓更明显（须经查新核实，勿贬低未检索对象）。

教学样例：`examples/example_design_desk_lamp/`（brief + 国内媒体实拍；须自填 AppearanceSchema + figure_plan；brief 为教学虚构）。
