# 专利地图 · 总则

## 定位

把**已经解读入库**的案例摊成图，给代理师找相近案子、看申请人重叠和文内引证。  
不是全库检索沙盘；空白点只表示「库里没读到」。

## 硬性禁止

- 把图上的邻近写成侵权、无效或 FTO 结论。
- 把未读专利的灰节点当成已通读。

## 取数

1. **磁盘（主路径）**：解读同一库根下 `Research/Patents/**/*_解读_*.md` 的 frontmatter（含 `tech_means` / `tech_effects` / `tech_effect_pairs`）。技术功效矩阵：先读这些字段；再收第七节里**已经是短标签**的箭头句；再不行用 **IPC 小类 × 领域**占位（`te_source=fallback`），不要把长句/markdown 当轴标签。  
2. **Obsidian CLI（可选）**：`obsidian` 在 PATH 且应用已打开时，`vaults` 核对库名；`base:query file=patents.base` 可作交叉校验。CLI `read` 一次一篇，不适合批量，正文仍读磁盘。  
3. **加速副本**：SQLite 放在操作系统文档目录 `{Documents}/patent-disclosure-skill/patent-map/index.sqlite`，与审查答复 `oa/` **同级**，不写进 vault。`PATENT_MAP_HOME` 可覆盖。笔记 `mtime`/`size` 变了才重解析。可整夹删除，下次会重建。  
4. **向量模型**：fastembed 加载名 `BAAI/bge-small-zh-v1.5`，磁盘只装 **Qdrant ONNX**（`Qdrant/bge-small-zh-v1.5` 的 `model_optimized.onnx`）。权重用 ONNX，不用 BAAI 原仓的 PyTorch（`.bin` / `.safetensors`），也不依赖本机 PyTorch。目录只使用 `{Documents}/patent-disclosure-skill/patent-map/models/`（与 sqlite 同级）。若模型还在 `~/.patent-disclosure-skill/patent-map/models/` 仍会读到。下载端点仅：`hf-mirror.com` → `www.modelscope.cn/models` → `huggingface.co`，用 `huggingface_hub` 拉 ONNX。  
5. 库空或尚无解读笔记：页面只显示已读（可以为空），并提醒先用通俗解读入库。

## 结束时

把 `MAP_URL` 发给用户。需要停服务时结束对应进程即可。
