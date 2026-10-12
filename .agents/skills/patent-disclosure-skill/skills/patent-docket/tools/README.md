# 案卷脚本

本包只维护 `outputs/docket/` 的 yaml / TRACKER。**禁止**从这里调用交底或申请文件的 `tools/`。

| 脚本 | 作用 |
|------|------|
| `init_docket.py` | 新建案卷目录与 `docket.yaml` |
| `validate_docket.py` | 校验阶段、轮次、议题枚举 |
| `emit_tracker.py` | 由 yaml 覆盖生成 `TRACKER.md` |

依赖仓库根 `PyYAML`。
