# Wiki 自动生成技能（中文版）

本文件为中文用户提供技能使用说明。

## 输出目录结构

```
.mini-wiki/
├── config.yaml              # 配置
├── meta.json                # 元数据
├── cache/                   # 增量更新缓存
├── wiki/                    # 主 Wiki 内容
│   ├── index.md
│   ├── architecture.md
│   ├── getting-started.md
│   ├── modules/
│   ├── api/
│   └── assets/
└── i18n/                    # 多语言版本
    ├── en/
    └── zh/
```

## 执行流程

### 1. 初始化检查

检查 `.mini-wiki/` 是否存在：
- **不存在**: 运行 `scripts/init_wiki.py` 创建目录结构
- **存在**: 读取 `config.yaml` 和缓存，执行增量更新

### 2. 插件发现

检查 `plugins/` 目录中已安装的插件：
1. 读取 `plugins/_registry.yaml` 获取已启用插件
2. 读取每个插件的 `PLUGIN.md` 清单
3. 注册钩子：`on_init`, `after_analyze`, `before_generate`, `after_generate`

### 3. 项目分析

运行 `scripts/analyze_project.py` 或手动分析：

1. **识别技术栈**: 检查 package.json, requirements.txt 等
2. **发现入口文件**: src/index.ts, main.py 等
3. **识别模块**: 扫描 src/ 目录结构
4. **发现现有文档**: README.md, CHANGELOG.md 等
5. **执行 `after_analyze` 钩子**

保存结构到 `cache/structure.json`。

### 4. 变更检测

运行 `scripts/detect_changes.py` 对比文件校验和：
- 新增文件 → 生成文档
- 修改文件 → 更新文档
- 删除文件 → 标记废弃

### 5. 内容生成

执行 `before_generate` 钩子，然后：

1. **首页**: 项目概览、导航、统计
2. **架构文档**: Mermaid 图表、技术栈、模块说明
3. **模块文档**: 概述、公开接口、使用示例
4. **API 文档**: 函数签名、参数、返回值、代码链接

执行 `after_generate` 钩子。

### 6. 代码链接

为代码块添加源码链接：
```markdown
### `functionName` [📄](file:///path/to/file.ts#L42)
```

### 7. 保存

- 写入 wiki 文件到 `.mini-wiki/wiki/`
- 更新 `cache/checksums.json`
- 更新 `meta.json` 时间戳

## 插件系统

### 插件命令

| 命令 | 说明 |
|------|------|
| `列出插件` | 显示已安装插件 |
| `安装插件 <路径/URL>` | 从路径或URL安装 |
| `启用插件 <名称>` | 启用插件 |
| `禁用插件 <名称>` | 禁用插件 |
| `卸载插件 <名称>` | 移除插件 |

### 插件脚本

```bash
python scripts/plugin_manager.py list
python scripts/plugin_manager.py install <source>
python scripts/plugin_manager.py enable <name>
python scripts/plugin_manager.py disable <name>
```

### 创建插件

见 `references/plugin-template.md` 了解插件格式。

支持的钩子：
- `on_init` - 初始化时运行
- `after_analyze` - 添加分析数据
- `before_generate` - 修改提示词
- `after_generate` - 后处理输出
- `on_export` - 格式转换

## 脚本参考

| 脚本 | 用途 |
|------|------|
| `scripts/init_wiki.py <path>` | 初始化 .mini-wiki 目录 |
| `scripts/analyze_project.py <path>` | 分析项目结构 |
| `scripts/detect_changes.py <path>` | 检测文件变更 |
| `scripts/generate_diagram.py <wiki-dir>` | 生成 Mermaid 图表 |
| `scripts/extract_docs.py <file>` | 提取代码注释 |
| `scripts/generate_toc.py <wiki-dir>` | 生成目录 |
| `scripts/plugin_manager.py <cmd>` | 管理插件 |

## 参考资料

详细模板和提示词见 `references/` 目录：
- **[prompts.md](prompts.md)**: AI 提示词模板
- **[templates.md](templates.md)**: Wiki 页面模板
- **[plugin-template.md](plugin-template.md)**: 插件开发指南

## 配置文件

`.mini-wiki/config.yaml` 格式：

```yaml
generation:
  language: zh          # zh / en / both
  include_diagrams: true
  include_examples: true
  link_to_source: true

exclude:
  - node_modules
  - dist
  - "*.test.ts"
```
