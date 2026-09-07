# 审查答复 · 实务书蒸馏为经验手册

前置：`guardrails.md`、`intake.md`。  
**输入只接受本地文件路径**，禁止书的 URL。  
手册写入 `{vault}/oa/playbooks/{slug}/`，**不进** `search_cases` / 案例向量。

## 步骤（必须按序）

### 1. 预读门槛（先做，未过关不得安装、不得蒸馏）

```bash
python skills/patent-oa/tools/ingest_playbook.py peek --path "本地书.pdf或.txt或.md"
```

`Read` 返回 JSON 里的 `text`（不要只看 `hint`）。判断两件事：

1. **是否审查答复相关**（审查意见/意见陈述/创造性或新颖性评述/权利要求修改/补正/审查指南实务等）。交底撰写、外观美学、营销、小说、菜谱等 **不算**。  
2. **是否值得蒸馏**（有可复用打法/决策/反模式；不是只有目录或扫描件无字）。

`hint`：`likely` / `unclear` / `unlikely` / `too_short` 仅供参考。扫描件 `too_short` 或几乎无审查答复信号 → **拒绝**，说明原因，停止。

**强烈要求**才可越过门槛：用户明确说「强制蒸馏 / 仍然要蒸 / 不管是否相关也要入库」等。此时 `--force`，`peek_decision=force`。未达此强度不得继续。

### 2. 确保外挂 book-to-skill

```bash
python skills/patent-oa/tools/ingest_playbook.py ensure-skill
```

脚本会：探测本机 skill 目录 → 已装则用；未装则请求 GitHub [`virgiliojr94/book-to-skill`](https://github.com/virgiliojr94/book-to-skill) 的最新 README 安装命令并自动安装；失败则降级 `npx --yes skills add virgiliojr94/book-to-skill`，再失败则 `git clone` 到 `~/.agentsskills/book-to-skill`。

JSON 里的 `skill_path` 指向**转换器** skill。**`Read` 该目录 `SKILL.md`**，按它的步骤把**本地书文件**蒸馏成一本新 skill（框架/决策表/反模式/分章，不要整本复述）。

蒸馏输出目录通常在用户 skills 下以书名为 slug 的文件夹（含 `SKILL.md`、`cheatsheet.md`、`patterns.md`、`chapters/`）。记下该路径。

转换器安装失败：把 GitHub 页与命令交给用户，**不要**改去拉书的 URL。

### 3. 自动转写进 Obsidian（无人逐章确认）

```bash
python skills/patent-oa/tools/ingest_playbook.py ingest \
  --from-skill-dir "蒸馏输出目录" \
  --source-path "本地书路径" \
  --slug "短标识" \
  --title "手册标题"
# 若用户强烈要求越过预读：追加 --force --peek-decision force
```

成功则 `oa/playbooks/{slug}/` 有 `_playbook.md` 与 cheatsheet 等，并刷新 `_OA索引`。stderr 前缀 `PLAYBOOK:`。

### 4. 报告

告诉用户：手册路径、**未进入案例检索**、写答复时按缺陷 Read cheatsheet。不要把手册条目写成 `case_id`。本轮是蒸馏，**不要**再按 `soft_nudge.md` 提示「去蒸馏」。

## 自检

- [ ] 先 peek 再蒸馏；不合适已拒绝，或仅在强烈要求下 `--force`  
- [ ] 未使用书的 URL  
- [ ] 手册在 `oa/playbooks/`，未写入 `cases/history`、未重建进案例向量  
- [ ] 已 Read 转换器 SKILL.md 完成蒸馏，再 ingest  
