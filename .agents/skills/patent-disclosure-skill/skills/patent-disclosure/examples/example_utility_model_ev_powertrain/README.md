# 示例案件：集成式电驱桥壳体（实用新型 · 文生图）

**教学案件**，专利类型：**实用新型**。主题为乘用车/轻商用车**电驱动总成（e-axle）壳体分腔与可抽拔电机**。  
仅含 `knowledge/` 文字 + **一张**公开实拍，**没有**现成专利线稿、也**没有** STEP。用于演练：扫描 brief → 填 StructureSchema → 按 brief **文生图**出结构线稿（图生图仅当把实拍当参考；实拍本身不入实用新型正文）。

> 结构说明为教学虚构，保护点落在分腔壳体、花键滑脱抽拔、水套限于电机腔。实拍来自 Wikimedia 展台照片，车型与本案无关。附图类型划分参考 [汽车专利附图：动力总成、电池包、ADAS 与线束](https://patentfig.ai/zh/blog/automotive-patent-drawings-powertrain-battery-adas)（剖视 / 爆炸 / 局部）。

## 目录

| 路径 | 说明 |
|------|------|
| `knowledge/docs/structure_brief.md` | 结构交底底稿（扫描主文档，含部件表与建议四视图） |
| `knowledge/assets/photo_motor_pcu.jpg` | 电机与 PCU 剖开展台实拍（仅此一张；不入实用新型正文） |

> 不提供预填 StructureSchema / figure_plan：须按 `fill_structure_schema.md` 根据 **brief 文字**自填（实拍只帮助建立外形直觉）。产出写入工作目录（勿写回 `knowledge/`）。成文只嵌合格 **线稿**。

## Agent 话术（可复制）

```text
请按 patent-disclosure-skill 交底书流程执行：
- 专利类型：实用新型
- 项目扫描目录：skills/patent-disclosure/examples/example_utility_model_ev_powertrain/knowledge/
- 技术主题：集成式电驱桥壳体、电机腔可抽拔、冷却水套
- 先 Read prompts/fill_structure_schema.md，主要依据 structure_brief.md 填 StructureSchema，并写出 figure_plan.yaml（实拍标 photo_scene / photo_clean，不入文；无合格线稿）
- 成文前线稿：Read image_gen.md + structure_lineart_assist.md + structure_lineart_compose.md。本案例走文生图（或实拍图生图失败后先描述再文生图）；按 brief 第 8 节出总装、纵剖、爆炸、局部；按 parts 写出子 SVG 再拼总图、再 overlay 件号
- 再按 skills/patent-disclosure/prompts/utility_model/ 挖点与成文（只嵌 figure_plan 入文线稿）
- 查新：cnipa_epub_search.py --type utility_model ，关键词含电驱桥、壳体、水套
```

产出落到 `outputs/{案件标识}/`。细则见 `skills/patent-disclosure/prompts/utility_model/disclosure_builder.md`。

## 实物图来源

Wikimedia Commons，仅供教学识图，勿用于商业再发布。下载使用 `Special:FilePath`。

| 本地文件 | 说明 | 页面 | 直链 |
|----------|------|------|------|
| `photo_motor_pcu.jpg` | Toyota Mirai 电机与 PCU 剖开展台 | [File:Toyota Mirai power control unit and electric motor SAO 2016 9019.jpg](https://commons.wikimedia.org/wiki/File:Toyota_Mirai_power_control_unit_and_electric_motor_SAO_2016_9019.jpg) | https://commons.wikimedia.org/wiki/Special:FilePath/Toyota_Mirai_power_control_unit_and_electric_motor_SAO_2016_9019.jpg |

作者与许可见文件页（Mariordo，CC BY-SA 展台照片）。展车含燃料电池与车身，**不是**本案零件。

### 公开专利文字对照（无本地附图；查新演练）

| 主题 | 公开号 | 页面 |
|------|--------|------|
| 电动车桥总成（桥壳内电机/减速器/差速器） | CN206327151U | https://patents.google.com/patent/CN206327151U/zh |
| 电驱动总成、集成水套（说明书附图标记） | — | https://www.xjishu.com/zhuanli/50/202110277717.html |

```bash
python skills/patent-reader/tools/extract/fetch_patent_pdf.py --pub CN206327151U -o skills/patent-disclosure/examples/example_utility_model_ev_powertrain/knowledge
```
