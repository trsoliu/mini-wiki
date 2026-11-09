# 专利地图 · 录入

执行前须先 **`Read`** `prompts/guardrails.md`。

## 何时进入

用户显式提到：专利地图、案例地图、打开已读图、`/专利地图`、`/patent-map`。

**禁止**因「读专利 / 写交底」进入。

## 库不够时

库内还没有解读笔记：仍可启动（图为空），提醒先用通俗解读入库；不要改去读一篇专利除非用户点名。

## 启动

工作区根执行：

```bash
python skills/patent-map/tools/serve_map.py
```

把 stdout 的 `MAP_URL:` 发给用户。端口随机，不要手填。  
需要打开浏览器时加 `--open`（仅本机）。

可选依赖（语义地形）：

```bash
pip install -r skills/patent-map/tools/requirements.txt
```

模型装到 `{Documents}/patent-disclosure-skill/patent-map/models/`（与 oa 同级），只要 ONNX，不要下到当前工作区，也不要为本技能装 PyTorch。
