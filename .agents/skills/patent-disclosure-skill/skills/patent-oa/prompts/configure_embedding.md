# 审查答复 · 向量配置（对话交互）

执行前可先 `python skills/patent-oa/tools/config.py recommend`。  
**向量可选**；用户可跳过。密钥**只写本机文档目录** `embedding.secrets.yaml`，**禁止**写入仓库内 yaml、禁止在回复里回显完整 Key。

## 对话脚本（Agent 逐步问，用户答完再写文件）

### 第 1 问 · 是否启用向量

```
向量检索可选。请选：
0) 跳过（仅用 Obsidian 标签/字段检索）
1) 用推荐：智谱 embedding-3
2) 其他预设：dashscope / minimax / local / openai
3) 自定义：我提供 base_url + model + dimensions + API Key
```

- 选 **0** → `python skills/patent-oa/tools/config.py skip-vector` → 结束（无需自检）。  
- 选 **1/2/3** → 继续。

### 第 2 问 · 参数与密钥

| 选项 | Agent 要问清 |
|------|----------------|
| 预设 1/2 | API Key（线上）；MiniMax 另问 GroupId；local 不问 Key |
| 自定义 3 | `base_url`、`model`、`dimensions`、API Key |

用户给出后执行（示例）：

```bash
# 推荐智谱
python skills/patent-oa/tools/config.py set --preset zhipu --api-key "用户提供的Key"
# 自定义
python skills/patent-oa/tools/config.py set --provider openai_compatible \
  --model embedding-3 --dimensions 1024 \
  --base-url "https://open.bigmodel.cn/api/paas/v4" \
  --api-key "用户提供的Key"
# MiniMax
python skills/patent-oa/tools/config.py set --preset minimax --api-key "…" --secret-group-id "…"
```

- 模型/URL → `{Documents}/…/oa/embedding.config.yaml`  
- API Key / GroupId → `{Documents}/…/oa/embedding.secrets.yaml`（`set --api-key` 自动写）  
- `set` **默认会跑 selftest**（结果在 JSON `selftest` 字段）

### 第 3 步 · 自检（必须）

若 `set` 未带出自检结果，再跑：

```bash
python skills/patent-oa/tools/config.py selftest
```

- `ok: true` → 告知用户「配置已写入并自检通过」；若 `rebuild.needed`，再问是否 `rebuild_vectors.py --confirm`。  
- `ok: false` → 展示错误摘要（勿贴全 Key），请用户改 URL/Key/模型后重试；**不阻断**后续标签检索流程。

### 中途开启 / 换模型

同样走本对话；换模型后若需重建，人确认再重建。

## 禁止

- 把 API Key 写入仓库 `docs/oa/embedding.config.yaml`  
- 在聊天记录外的可提交文件中明文落 Key  
- 自检失败却声称「向量已就绪」
