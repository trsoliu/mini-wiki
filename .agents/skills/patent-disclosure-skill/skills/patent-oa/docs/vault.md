# 审查答复案例库

运行时数据优先落在操作系统**默认文档目录**（可用 `PATENT_OA_HOME` 覆盖）：

| 路径 | 用途 |
|------|------|
| `{Documents}/patent-disclosure-skill/oa/embedding.config.yaml` | 嵌入模型与 sqlite 路径（首次须用户确认） |
| `{Documents}/patent-disclosure-skill/oa/data/oa_vectors.sqlite` | sqlite-vec 向量库 |
| `{Documents}/patent-disclosure-skill/oa/` | 无 Obsidian 库时的 oa 回退根 |
| 本目录 `embedding.config.yaml` | **仓库模板种子**（`config.py seed` 复制到文档目录） |

正式案例优先写入 **Obsidian**（方案 C）：

```
{vault}/oa/
  _OA索引.md
  _OA看板.base
  _OA关联.canvas
  cases/history/   # status=history，可检索
  pending/         # 待答复
  drafts/          # 人审草稿
  playbooks/       # 实务书蒸馏手册（不进案例检索）
```

刷新：`python skills/patent-oa/tools/refresh_vault.py`  
只读统计（不写索引）：`python skills/patent-oa/tools/refresh_vault.py --inventory`  
查看实际路径：`python skills/patent-oa/tools/config.py recommend`。  
仓库源稿是 `assets/obsidian/oa.base.yaml`（部分技能市场不允许提交 `.base`）；写入库时仍为 `_OA看板.base`。  
流程见 `skills/patent-oa/prompts/` 与 [SKILL.md](../SKILL.md)。
