# IPC 小类表维护管线

地图运行时**只读**编译结果 `skills/patent-map/data/ipc_subclasses_2026.01.csv`，不联网。  
换版或补中文时，在本目录重新跑一遍下载 → 解析 → 输出。

## 一次更新

在仓库根目录：

```bash
pip install -r skills/patent-map/tools/ipc_scheme/requirements.txt
python skills/patent-map/tools/ipc_scheme/build.py
```

或：

```bash
cd skills/patent-map/tools
python -m ipc_scheme
```

默认把 CSV 写到 `skills/patent-map/data/ipc_subclasses_{IPC_VERSION}.csv`（当前为 `ipc_subclasses_2026.01.csv`）。  
下载的 zip / XML / PDF 落在本目录 `cache/`（已 gitignore）。

只检查 WIPO 英文小类、不拉中文：

```bash
python skills/patent-map/tools/ipc_scheme/build.py --skip-zh
```

## 数据从哪来

| 步骤 | 源 | 用途 |
| --- | --- | --- |
| 1 | [WIPO MasterFiles `ipc_scheme_*.zip`](https://www.wipo.int/classifications/data/ipc/ITSupport_and_download_area/20260101/MasterFiles/) | 解析 EN XML，`kind="u"` 即小类代号 + 英文标题 |
| 2 | [ipcpub.wipo.int](https://ipcpub.wipo.int/) CDN `…/IPC/scheme/{lang}/json/` | **尝试**拉中文 scheme。官方 IPCPUB 目前只有 `en` / `fr` / `enfr`，`zh` 为 403 |
| 3 | [国知局 2026.01 分类表](https://www.cnipa.gov.cn/art/2025/12/31/art_3161_203422.html) A–H PDF | 中文短标题（轴上用） |

WIPO 权威文本是英、法文。中文以国知局译制分类表为准，不要用英文字面直译，也不要调用 IPCPUB 的在线翻译。

换年版时改 `config.py` 里的 `IPC_VERSION` / `IPC_VERSION_DATE`，输出文件名会变成 `ipc_subclasses_{IPC_VERSION}.csv`，并视情况更新 `CNIPA_TABLE_PAGE`。

## 口径

- 轴标题约 4–24 字：取国知局小类标题第一分句，去掉括号和附注
- 引得表小类（B29K、B29L、C10N、C12R、F21W、F21Y）→ `引得表`
- `*99Z` → `本部其他未列入的技术主题`
- 地图缺码只显示分类号，运行时不补译

## 文件

| 文件 | 作用 |
| --- | --- |
| `build.py` / `cli.py` | 入口 |
| `download.py` | 拉 zip、探 IPCPUB、拉国知局 PDF |
| `parse.py` | EN XML / IPCPUB JSON / 国知局 PDF |
| `emit.py` | 写出 `code,zh,en` CSV |
| `config.py` | 版次与 URL |
