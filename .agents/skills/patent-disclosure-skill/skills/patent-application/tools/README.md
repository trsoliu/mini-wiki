# 申请文件工具

| 脚本 | 前缀 | 退出码 |
|------|------|--------|
| `material_gate.py` | `APPLICATION_GATE:` | 0 齐全；2 缺材料；1 用法错误 |
| `audit_claims.py` | `APPLICATION_CLAIMS:` | 0 无 ERROR；1 有 ERROR |
| `check_numeral_register.py` | `APPLICATION_NUMERALS:` | 0 无 ERROR；1 有 ERROR |
| `render_invention_figures.py` | `APPLICATION_FIG:` | 0 已出 SVG；PNG 失败不单独当致命（看 png_fail） |
| `check_support.py` | `APPLICATION_SUPPORT:` | 0 无 ERROR；1 有 ERROR |
| `compose_application_figure.py` | `APPLICATION_FIG:` | 0 已出 SVG（PNG 看 png=） |
| `iteration_dialog_log.py` | `LOG_FILE=` | 0 已追加 |
| `emit_application_docx.py` | `DOCX:` / `APPLICATION_DOCX:` | 0 全部写出 |

```bash
python skills/patent-application/tools/material_gate.py --case-dir outputs/{案件}
python skills/patent-application/tools/render_invention_figures.py \
  --plan outputs/patent-application/{案}/figures/invention_figures.yaml \
  --out-dir outputs/patent-application/{案}/figures
python skills/patent-application/tools/audit_claims.py outputs/patent-application/{案}/权利要求书.md
python skills/patent-application/tools/check_support.py --dir outputs/patent-application/{案}
python skills/patent-application/tools/compose_application_figure.py \
  --source <线稿或场景图> --fig 3 --out-dir outputs/patent-application/{案}/figures
python skills/patent-application/tools/emit_application_docx.py --dir outputs/patent-application/{案}
```

宣传语词库：`references/promo_terms.yaml`（`lexicon.py` 加载；权要与摘要共用）。增删词条不必改脚本。
