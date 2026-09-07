# Obsidian 库模板

本目录是仓库源稿。入库脚本会把文件拷进用户的 Obsidian 库。

## Bases 扩展名

部分技能市场不允许提交 `.base`。因此仓库里只保留 `*.base.yaml`：

| 仓库源稿 | 拷进库后 |
|----------|----------|
| `patents.base.yaml` | `{papers_dir}/patents.base` |
| `glossary.base.yaml` | `{glossary_dir}/glossary.base` |
| `oa.base.yaml` | `oa/_OA看板.base` |

Obsidian Bases 仍只认 `.base`。不要在库内用 `.base.yaml`，也不要把库内 wikilink（如 `![[…/patents.base#…]]`）改成 yaml 后缀。
