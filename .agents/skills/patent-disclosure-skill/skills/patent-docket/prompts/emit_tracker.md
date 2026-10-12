# 案卷落盘

改 `docket.yaml` 的字段之后**必须**跑校验与 tracker，禁止只改 md 或只改 yaml。

```bash
python skills/patent-docket/tools/validate_docket.py --yaml outputs/docket/{case_id}/docket.yaml
python skills/patent-docket/tools/emit_tracker.py --yaml outputs/docket/{case_id}/docket.yaml
```

`TRACKER.md` 由脚本覆盖生成。不要长期手改 TRACKER 导致与 yaml 分叉；要改条目就改 yaml。

新开案卷只用 `init_docket.py`，不要手写残缺 yaml。
