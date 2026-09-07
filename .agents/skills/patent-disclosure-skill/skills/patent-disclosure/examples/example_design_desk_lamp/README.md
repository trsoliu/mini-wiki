# 示例案件：折臂台灯外观（外观设计）

**教学案件**，专利类型：**外观设计**。仅含 `knowledge/`，用于交底 / AppearanceSchema 填表演练。

> 附图已替换为国内媒体**真实产品实拍**（明基 WiT / 米家台灯 Pro，少数派 CDN）。设计 brief 仍为教学虚构，与实拍产品仅作外观识图演练对照。

## 目录

| 路径 | 说明 |
|------|------|
| `knowledge/docs/design_brief.md` | 设计说明 |
| `knowledge/assets/view_perspective.jpg` | 桌面场景立体实拍 |
| `knowledge/assets/views_ortho.jpg` | 另一角度场景实拍 |
| `knowledge/assets/view_arm_detail.jpg` | 灯臂/灯头连接局部 |
| `knowledge/assets/view_joint_detail.jpg` | 环形调节关节局部 |
| `knowledge/assets/view_packaging.jpg` | 包装盒外观 |
| `knowledge/assets/mi_desk_lamp_pro.jpg` | 米家台灯 Pro 补充实拍 |

> 不提供预填 AppearanceSchema / figure_plan：须按 `fill_appearance_schema.md` 识图自填，产出写入工作目录（勿写回 `knowledge/`）。成文只嵌 `figure_plan` 中入文图（场景图默认低优先级）。

## Agent 话术

```text
请按 patent-disclosure-skill 交底书流程执行：
- 专利类型：外观设计
- 项目扫描目录：skills/patent-disclosure/examples/example_design_desk_lamp/knowledge/
- 先 Read prompts/fill_appearance_schema.md 填 AppearanceSchema，并写出 figure_plan.yaml（识图打分；干净实拍+线稿都入文，写入 md 与 Word；CAD 不入文；入文多视补 relates_to）
- 成文前线稿必做（不问我）：Read image_gen.md + design_lineart_assist.md；已有合格线稿则入文，否则图生图或文生图
- 再按 skills/patent-disclosure/prompts/design/ 成文（只嵌 figure_plan 入文图）
- 查新：cnipa_epub_search.py --type design …
```

## 附图来源与下载链接

图片来自少数派文章内嵌图（国内 `cdnfile.sspai.com`，下载较快）。仅供教学识图，勿用于商业再发布。

| 本地文件 | 来源文章 | 直链 |
|----------|----------|------|
| `view_perspective.jpg` | [明基 WiT 上手](https://sspai.com/post/81747) | https://cdnfile.sspai.com/2023/08/03/article/58410f27568ccd9df0d9d8b6893bc5e9?imageView2/2/w/1400/q/90/interlace/1/ignore-error/1 |
| `views_ortho.jpg` | 同上 | https://cdnfile.sspai.com/2023/08/03/article/2841967c7a0bd40ef062a281350b0561?imageView2/2/w/1400/q/90/interlace/1/ignore-error/1 |
| `view_arm_detail.jpg` | 同上 | https://cdnfile.sspai.com/2023/08/03/article/cd955177eb766eff79d9fe1ce990e893?imageView2/2/w/1400/q/90/interlace/1/ignore-error/1 |
| `view_joint_detail.jpg` | 同上 | https://cdnfile.sspai.com/2023/08/03/article/6960c15717c38cecfeb6c533a672154d?imageView2/2/w/1400/q/90/interlace/1/ignore-error/1 |
| `view_packaging.jpg` | 同上 | https://cdnfile.sspai.com/2023/08/03/article/4adf940a108373a2aa76e88093dd353a?imageView2/2/w/1400/q/90/interlace/1/ignore-error/1 |
| `mi_desk_lamp_pro.jpg` | [米家台灯 Pro](https://sspai.com/post/52856) | https://cdnfile.sspai.com/2019/02/12/69013154e9c566e4f8651d6d645484cf.jpg?imageView2/2/w/1400/q/90/interlace/1/ignore-error/1 |

### 可选：外观设计 PDF 演练

```bash
python skills/patent-reader/tools/extract/fetch_patent_pdf.py --pub CN309939145S -o skills/patent-disclosure/examples/example_design_desk_lamp/knowledge
```
