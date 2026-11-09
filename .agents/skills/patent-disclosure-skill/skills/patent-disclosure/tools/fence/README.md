# 专利布局 / 保护型 1+N 脚本

与 `prompts/fence/`、`references/scorecards/` 配套。查新仍用上级 `crawl/`，不要从这里调其他子技能 `tools/`。说明稿由模型按 `prompts/fence/plan.md` 直接写 `专利布局.md`（立项校验表按 `prompts/fence/score.md` 回写），不要用脚本从 yaml 生成。

| 脚本 | 作用 |
|------|------|
| `check_layout.py` | 校验 decompose / design_around / matrix / family |
| `check_scorecard.py` | 立项后弱校验（默认表可整表替换） |
| `layout_lib.py` / `family_lib.py` / `scorecard_lib.py` | 给上面入口用，不要单独当 CLI |

```bash
python skills/patent-disclosure/tools/fence/check_layout.py --decompose outputs/案/fence/decompose.yaml
python skills/patent-disclosure/tools/fence/check_layout.py --family outputs/案/fence/family.yaml --matrix outputs/案/fence/matrix.yaml
python skills/patent-disclosure/tools/fence/check_scorecard.py -i outputs/案/fence/scorecard.yaml --case-dir outputs/案
```

单独拷走本包时：`python tools/fence/check_layout.py …`。
