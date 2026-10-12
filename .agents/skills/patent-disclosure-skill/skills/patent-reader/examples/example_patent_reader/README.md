# 专利通俗解读 · 示例 PDF（镜像下载）

本目录材料**不入库**，请自行下载到 `source/` 后做解读 / 关联测试。

> **说明**：下列示例专利**仅用于本技能的功能测试与效果演示**，不代表技术优劣、权利状态或商业立场，亦不构成任何推荐或评价。

## 下载方式（推荐）

通用入口（技能已固化，勿另写脚本）：

```bash
python skills/patent-reader/tools/extract/fetch_patent_pdf.py --pub CN119961396A -o skills/patent-reader/examples/example_patent_reader
# → skills/patent-reader/examples/example_patent_reader/source/CN119961396A.pdf
```

源优先级与备选说明：`references/patent_pdf_sources.yaml`。

## Google Patents CDN（已知镜像直链 · 与 yaml 同步）

| 公开号 | 用途 | PDF / 页面镜像 |
|--------|------|----------------|
| `CN119961390A` | 主示例（发明公布 · 软件/RAG 类解读） | https://patentimages.storage.googleapis.com/58/1b/9b/07a9f35635df34/CN119961390A.pdf |
| `CN119961396A` | 近似专利（关联 / 同域对照） | https://patentimages.storage.googleapis.com/3f/29/d0/a2461c5080d73d/CN119961396A.pdf |
| `CN114552122A` | **按图裁切解读** | https://patentimages.storage.googleapis.com/c2/6c/51/75412585086edf/CN114552122A.pdf |
| `CN209861402U` | **实用新型**解读（散热片卡扣安装 · Schema 挂钩） | https://patentimages.storage.googleapis.com/39/b7/d6/0050a57f67b004/CN209861402U.pdf |
| `CN309939145S` | **外观设计**解读（台灯 · Schema 挂钩） | 常无 PDF CDN → 用 `fetch_design_views.py` 从国知局取视图（见下） |

### 实用新型 / 外观（类型挂钩 · Schema）

用 `fetch_patent_pdf.py` 拉取后解读；入库前在 workdir 写 schema（见 `skills/patent-reader/prompts/type_hooks.md`）。

| 类型 | 公开号 | 下载 |
|------|--------|------|
| 实用新型 | `CN209861402U` | `python skills/patent-reader/tools/extract/fetch_patent_pdf.py --pub CN209861402U -o skills/patent-reader/examples/example_patent_reader` |
| 外观设计 | `CN309939145S` | `python skills/patent-reader/tools/extract/fetch_design_views.py --pub CN309939145S -o skills/patent-reader/examples/example_patent_reader` |

本地建议：`source/<公开号>.pdf`。解读触发示例：

```text
请按专利通俗解读流程读 CN209861402U（公开号即可；类型由种类码自动判为实用新型，填 structure_schema 后入库）。
请按专利通俗解读流程读 CN309939145S（自动判为外观设计，填 appearance_schema 后入库）。
```


### 按图裁切（CN114552122A）

提供该 PDF 做通俗解读时，技能会按 `patent_plain_reader.md` **自动**跑附图抽取：有可选中图注则按图号裁切写入「特征—附图对照」；扫描件则回退整页预览。无需手动执行抽取脚本。
