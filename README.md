# Obsidian Solo

[![License: MIT](https://img.shields.io/badge/License-MIT-2ea44f.svg)](LICENSE)
[![Codex Skill](https://img.shields.io/badge/Codex-Skill-111827.svg)](SKILL.md)
[![Obsidian](https://img.shields.io/badge/Obsidian-Knowledge%20System-7c3aed.svg)](https://obsidian.md/)

一个面向 Codex 与 Obsidian 的中文知识系统 Skill。它负责检查 Claudian/Codex 连接条件、搭建通用中文知识库、配置 Horizon 信息收集，并建立每三天一次的增量知识迭代机制。

整个流程保留用户原始资料，密钥不进入聊天或 Markdown，安装过程不调用 computer-use，也不会代替用户操作 Obsidian 界面。

## 功能

- 初始化时只检查当前仓库缺少的 Claudian 配置，并提供本机可用的 Codex CLI 路径。
- 不创建 Claudian 测试对话，不读取模型列表，不要求模型请求测试成功。
- 建立中文通用知识结构，适用于学习、行业研究、项目管理、产品开发和个人资料整理。
- 从 GitHub 安装并配置 [Horizon](https://github.com/Thysrael/Horizon)，启用无需 Token 的公开来源。
- Windows 与 macOS 均通过本机终端收集模型服务商和 API Key。
- 每日收集信息，每三天增量整理知识，并保留来源、证据、置信度和待确认问题。
- 安全升级旧知识库：清理未修改的旧受管文件，保护用户修改过的内容。
- 全库验收会识别旧业务目录、废弃模块、失效链接和误写入笔记的密钥。

## 工作流程

```mermaid
flowchart LR
    A[初始化检查] --> B[用户配置 Claudian]
    B --> C[搭建中文知识库]
    C --> D[配置 Horizon]
    D --> E[首次信息收集]
    E --> F[增量知识整理]
    F --> G[项目与成果]
    G --> H[复盘与新输入]
    H --> F
```

知识闭环：

`输入 → 理解 → 知识 → 项目 → 成果 → 复盘 → 再输入`

## 环境要求

- [Codex](https://developers.openai.com/codex/) 桌面端或具备 Skills 功能的 Codex 环境
- [Obsidian](https://obsidian.md/)
- Obsidian 社区插件 [Claudian](https://github.com/YishenTu/claudian)
- Windows 10/11 或 macOS
- Horizon 所使用模型服务商的 API Key

Claudian 是唯一必需的 Obsidian 社区插件。Skill 不会要求 Dataview、Tasks、Templater 或其他工作台插件。

## 安装

### 使用 Skill Installer

在 Codex 中发送：

```text
请使用 $skill-installer 安装 https://github.com/Seb1900/obsidian-solo
```

安装完成后重新启动 Codex，使 Skill 被重新发现。

### 手动安装

Windows PowerShell：

```powershell
git clone https://github.com/Seb1900/obsidian-solo.git "$env:USERPROFILE\.codex\skills\obsidian-solo-os"
```

macOS：

```bash
git clone https://github.com/Seb1900/obsidian-solo.git ~/.codex/skills/obsidian-solo-os
```

也可以使用 GitHub Desktop 克隆仓库，再将仓库目录放到 Codex 的 `skills/obsidian-solo-os` 位置。

## 使用

### 1. 初始化检查

打开准备作为 Obsidian 仓库的 Codex 项目，然后发送：

```text
初始化
```

Skill 会检测：

- 当前路径是否为已经初始化的 Obsidian 仓库；
- Claudian 是否已安装并启用；
- 当前用户环境中可用的 Codex CLI 路径。

它只会告诉你仍缺少的操作。已经完成的配置不会重复提示。

### 2. 完成 Claudian 配置

如果检查提示缺少 Claudian，请在 Obsidian 中自行完成：

1. 打开“设置 → 第三方插件”。
2. 需要时关闭受限模式。
3. 安装并启用 Claudian。
4. 在 Claudian 中选择 Codex，并填写 Skill 检测到的 Codex CLI 路径。

无需创建对话或测试模型。完成后回复：

```text
初始化完成，开始搭建知识库
```

### 3. 配置 Horizon

Horizon 配置阶段会打开本机终端窗口。选择模型服务商并粘贴 API Key，输入内容以星号显示。

- API Key 只保存在 Horizon 的 `.env` 文件中。
- 密钥不会写入 Obsidian 笔记、Codex 聊天或自动化报告。
- GitHub 使用匿名抓取额度。
- X/Twitter 默认关闭。
- Hacker News、RSS、Reddit 公开接口、Telegram 公开频道、OSS Insight、GDELT 和 Google News 默认启用。

## 生成的知识库

```text
00_输入/
├── 输入池.md
└── 原始资料/
    └── 资讯日报/
01_理解/
├── 理解记录.md
02_知识/
├── 知识库.md
├── 知识条目/
├── 索引/
└── 健康检查/
03_项目/
├── 项目库.md
04_成果/
├── 成果库.md
05_复盘/
├── 复盘记录.md
└── 待确认队列.md
06_系统/
├── 系统规则.md
├── 自动化任务.md
├── 迭代状态.md
└── 知识库迭代机制.md
附件/
模板/
```

模板包括：输入、理解、知识条目、项目、成果、复盘、每日记录、周复盘和方法模板。Properties 字段与状态均使用中文。

## 自动迭代

Skill 会尝试创建两个 Codex 自动化任务：

| 任务 | 时间 | 内容 |
| --- | --- | --- |
| 知识库-每日信息收集 | 每天 08:00 | 运行 Horizon 并导入新日报 |
| 知识库-三天增量迭代 | 每三天 20:30 | 整理新增输入、更新知识条目与索引、执行健康检查 |

自动化功能不可用时，Skill 会在 `06_系统/自动化任务.md` 中保留待创建状态，并告诉用户需要完成的一项操作。

## 增量知识方法

知识整理遵循以下原则：

1. 原始资料保持不变。
2. 事实、引用、解释、不确定内容和行动分开记录。
3. 新证据只更新受影响的知识条目。
4. 相同概念更新原条目，边界清晰的新概念再创建新条目。
5. 自动修复范围限于索引、双向链接、元数据、格式和摘要。
6. 事实冲突、不确定合并、无来源结论、删除和大范围改写进入待确认队列。

该机制参考了 [Andrej Karpathy 关于增量编译知识库的思路](https://x.com/karpathy/status/2039805659525644595)。

## 升级保护

升级时会合并新旧 manifest 和内置历史哈希目录：

- 受管文件内容未被修改：更新或清理旧版本。
- 用户修改过文件：保留原文件，并将新版放入升级候选目录。
- 已废弃的受管文件：哈希一致时安全删除。
- 无法确认的旧文件：继续保留清理依据，验收明确列出路径。
- 旧英文业务目录存在时，包含空目录，验收都会失败。

Skill 不会静默覆盖用户修改，也不会删除无法确认归属的笔记。

## 完成后的使用方式

知识库搭建完成后，可以继续告诉 Codex：

```text
我的身份是独立开发者，关注 AI 工具和个人产品。我想持续了解新工具、用户需求和可能的产品机会。
```

或：

```text
我是跨境电商从业者，希望跟踪平台政策、竞品动态和海外消费趋势，并每周形成一份可执行的研究总结。
```

Codex 会据此调整 Horizon 关键词、信息来源、分类方式和迭代重点。

## 安全边界

- 不调用 computer-use、浏览器控制或 Chrome 控制完成安装。
- 不编辑 Obsidian 插件注册表来伪造安装状态。
- 不把 API Key、Token、Cookie、密码和登录信息写入 Markdown。
- 不覆盖用户编辑过的文件。
- 不自动接受事实冲突、删除建议和大范围改写。
- 原始来源与整理结果分开保存。

## 常见问题

### 为什么初始化只显示 Codex CLI 路径？

检测到 Obsidian 仓库和 Claudian 已经就绪时，初始化只提供经过验证的 CLI 路径，然后可以直接继续搭建。

### Claudian 的模型测试失败还能继续吗？

可以。初始化条件不包含模型列表或模型请求测试。中转服务的兼容情况不会阻止知识库搭建。

### 为什么 Skill 不自动安装 Claudian？

Obsidian 社区插件由用户通过可见界面安装和启用，避免后台修改插件配置。

### 可以用于自媒体之外的领域吗？

可以。默认结构没有选题库、脚本库、制作看板或发布模块，项目类型与资料分类由用户的身份和目标决定。

### 会修改已有知识库吗？

会复用现有仓库，并保护用户文件。受管模板只有在内容仍与已安装版本一致时才会更新；冲突会进入升级候选目录。

## 项目结构

```text
obsidian-solo/
├── SKILL.md
├── agents/
├── assets/
│   ├── horizon-profile/
│   └── vault-template/
├── references/
├── scripts/
├── LICENSE
└── README.md
```

## 相关项目

- [Obsidian](https://obsidian.md/)
- [Claudian](https://github.com/YishenTu/claudian)
- [Horizon](https://github.com/Thysrael/Horizon)
- [Codex Skills 文档](https://developers.openai.com/codex/skills)

## 许可证

[MIT License](LICENSE) © 2026 Seb1900
