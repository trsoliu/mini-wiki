# 申请文件 · 迭代

用户在**已有申请产出目录**上改权要、附图、说明书、摘要或点名补图时走本文，不要整案从门禁空写。用户明确要求「按交底重新出一套」时除外。

先 **`Read`** `prompts/iteration_context.md`。

## 何时

| 意图 | `--kind` |
|------|----------|
| 补图、补表、补实施例、按用户点名嵌入场景图 | `merge` |
| 改独权步骤、从图框文、从属层、摘要字数、对照表对不上 | `correct` |

不要求用户说出「迭代」。

## 落盘

以用户指出的上一版目录为基准（`outputs/patent-application/{案件}_{旧时间戳}/`）。

1. 新建 **`outputs/patent-application/{案件标识}_{YYYYMMDDHHmmss}/`**，不要覆盖旧目录。
2. 拷贝需保留的 Markdown / YAML / 图，再改本轮涉及的文件。
3. 动过附图：发明重跑 `render_invention_figures.py`；实用新型重跑 `compose_application_figure.py`；**外观不改原图、不跑 compose**，不合格只更新 `问题清单.md`。动过权要则重跑 `audit_claims.py`；交付前跑 `check_support.py`（外观可跳过权要/对照脚本）。
4. `emit_application_docx.py` 出本目录 Word。
5. 按 `issues.md` 写本目录 `问题清单.md`，对话末尾提醒。
6. 追加修订记录：

```bash
python skills/patent-application/tools/iteration_dialog_log.py \
  --case-dir <新产出目录> \
  --kind merge \
  --user "{用户说明摘要}" \
  --summary "{摘要摘录}" \
  --artifacts "权利要求书.md,说明书.md,说明书摘要.md"
```

`--kind` 纠正用 `correct`。日志文件名默认 `申请文件修订对话记录.md`（写在**新产出目录**；同一案件多轮则同时向**上一版所在父目录**下 `{案件标识}_申请文件修订对话记录.md` 追加一份，脚本会处理）。

## 对话

同一条回复须有 **「合并摘要（留档）」** 或 **「纠正摘要（留档）」**（2～5 句：改了什么、是否重跑对照/出图、问题清单是否已更新），然后再做 `issues.md` 的清单提醒。
