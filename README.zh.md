# Mini-Wiki

> 🤖 AI 驱动的项目 Wiki 自动生成技能

[![skills.sh](https://img.shields.io/badge/skills.sh-compatible-blue)](https://skills.sh)
[![Version](https://img.shields.io/badge/version-2.0.0-green)](#)

## 简介

Mini-Wiki 是一个 [skills.sh](https://skills.sh) 兼容的技能包，帮助 AI Agent 自动分析项目结构，生成结构化的项目 Wiki 文档。

灵感来源:
- [DeepWiki](https://github.com/AsyncFuncAI/deepwiki-open)
- [OpenRepoWiki](https://github.com/daeisbae/open-repo-wiki)
- [Qoder Repo Wiki](https://docs.qoder.com/user-guide/repo-wiki)

## 特性

- 🔍 **智能分析** - 自动识别技术栈和模块结构
- 🔄 **增量更新** - 仅更新变更文件的文档
- 📊 **架构图** - 自动生成 Mermaid 依赖图
- 🔗 **代码链接** - 文档中代码块直接链接源码
- 🌐 **多语言** - 支持中英文 Wiki 生成
- 🔌 **插件系统** - 支持自定义插件扩展

## 安装

### 方式 1：使用 npx（推荐）

```bash
npx skills add trsoliu/mini-wiki
```

### 方式 2：下载技能包

从 [Releases](https://github.com/trsoliu/mini-wiki/releases) 下载 `wiki-generator.skill` 文件。

### 方式 3：克隆仓库

```bash
git clone https://github.com/trsoliu/mini-wiki.git
```

## 使用

安装后，对 AI Agent 说：

```
生成 wiki
创建项目文档
更新 wiki
```

### 插件命令

```
列出插件
安装插件 <路径/URL>
启用插件 <名称>
禁用插件 <名称>
```

## 输出结构

所有内容生成到项目的 `.mini-wiki/` 目录：

```
.mini-wiki/
├── config.yaml              # 配置
├── cache/                   # 增量缓存
├── wiki/                    # Wiki 内容
│   ├── index.md
│   ├── architecture.md
│   ├── modules/
│   └── api/
└── i18n/                    # 多语言
    ├── en/
    └── zh/
```

## 技能结构

```
mini-wiki/
├── SKILL.md           # 主指令（英文）
├── scripts/           # Python 脚本
├── references/        # 提示词、模板、中文文档
├── assets/            # 配置模板
└── plugins/           # 插件目录
    ├── _registry.yaml
    └── _example/
```

## 相关项目

- [DeepWiki](https://github.com/AsyncFuncAI/deepwiki-open)
- [OpenRepoWiki](https://github.com/daeisbae/open-repo-wiki)
- [Qoder](https://docs.qoder.com/user-guide/repo-wiki)

## 许可证

MIT

## 作者

- 微信: trsoliu
- 二维码:

![WeChat QR](assets/wechat-qr.png)
