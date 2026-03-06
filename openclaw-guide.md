# OpenClaw 完全新手指南

> 个人 AI 助手本地部署与配置权威指南

🦞 **EXFOLIATE! EXFOLIATE!**

---

## 目录

- [什么是 OpenClaw？](#什么是-openclaw)
- [安装指南](#安装指南)
- [快速开始](#快速开始)
- [Workspace 工作空间](#workspace-工作空间)
- [配置 openclaw.json](#配置-openclawjson)
- [配置对话终端](#配置对话终端channels)
- [配置多智能体](#配置多智能体multi-agent)
- [技能安装](#技能安装)
- [常用 CLI 命令](#常用-cli-命令)
- [安全最佳实践](#安全最佳实践)
- [故障排除](#故障排除)
- [资源链接](#资源链接)
- [总结](#总结)

---

## 🚀 什么是 OpenClaw？

OpenClaw 是一款**个人 AI 助手**，运行在你自己的设备上。它可以通过你已经在使用的通讯渠道（WhatsApp、Telegram、Slack、Discord、Google Chat、Signal、iMessage、Microsoft Teams、WebChat 等）与你交互，还支持语音对话、Canvas 可视化等高级功能。

OpenClaw 是一个**本地优先**的 AI 助手网关，它的核心设计理念是：

- **个人化**：为你个人服务，而非企业级多用户系统
- **本地运行**：Gateway 运行在你的设备上（macOS、Linux、Windows WSL2）
- **多渠道接入**：支持几乎所有主流通讯平台
- **功能丰富**：浏览器控制、Canvas 可视化、语音交互、定时任务等

### 架构概览

```
WhatsApp / Telegram / Slack / Discord / Google Chat / Signal / iMessage / WebChat
                   │
                   ▼
    ┌───────────────────────────────┐
    │            Gateway            │
    │       (控制平面 - 核心)        │
    │     ws://127.0.0.1:18789      │
    └──────────────┬────────────────┘
                   │
                   ├─ AI 智能体 (Agent)
                   ├─ CLI 命令行工具
                   ├─ WebChat 网页界面
                   ├─ macOS/iOS/Android 客户端
                   └─ 浏览器控制 (Chrome CDP)
```

---

## 📦 安装指南

### 系统要求

- **Node.js ≥ 22**（必须）
- **操作系统**：macOS、Linux、Windows (WSL2)
- **包管理器**：npm、pnpm 或 bun

### 快速安装（推荐）

#### macOS / Linux

```bash
curl -fsSL https://openclaw.ai/install.sh | bash
```

#### Windows (PowerShell)

```bash
iwr -useb https://openclaw.ai/install.ps1 | iex
```

#### npm 安装

```bash
# 使用 npm
npm install -g openclaw@latest

# 或使用 pnpm
pnpm add -g openclaw@latest
```

### 运行引导向导

```bash
# 完整安装向导 + 安装系统服务
openclaw onboard --install-daemon

# 仅运行配置向导
openclaw onboard
```

### 检查安装

```bash
# 查看 Gateway 状态
openclaw gateway status

# 打开控制面板
openclaw dashboard
```

---

## ⚡ 快速开始

### 1. 启动 Gateway

```bash
# 前台运行（适合调试）
openclaw gateway --port 18789 --verbose

# 使用守护进程（后台运行）
openclaw gateway start
```

### 2. 打开控制面板

```bash
openclaw dashboard
# 或直接在浏览器访问：
# http://127.0.0.1:18789
```

### 3. 发送测试消息

```bash
openclaw message send --to +15555550123 --message "Hello from OpenClaw"
```

### 4. 与智能体对话

```bash
# 命令行直接对话
openclaw agent --message "帮我总结今天的会议" --thinking high
```

---

## 📁 Workspace 工作空间

Workspace 是 OpenClaw 智能体的**工作目录**，也是它读取上下文、保存记忆、执行工具操作的唯一位置。

### Workspace 结构

```
~/.openclaw/
├── openclaw.json                      # 主配置文件
├── workspace/                         # 默认工作空间
│   ├── AGENTS.md                      # 操作指令和记忆
│   ├── SOUL.md                        # 人格、边界、语气
│   ├── TOOLS.md                       # 工具使用笔记
│   ├── IDENTITY.md                    # 助手名称/头像/表情
│   ├── USER.md                        # 用户信息
│   ├── MEMORY.md                      # 长期记忆（仅主会话加载）
│   └── skills/                        # 工作空间级技能
├── agents/                            # 多智能体会话存储
├── skills/                            # 全局技能
└── credentials/                       # 凭证存储
```

### 核心文件说明

| 文件 | 用途 | 加载时机 |
|------|------|----------|
| `AGENTS.md` | 操作指令、连续性规则、重要记忆 | 每会话首条消息 |
| `SOUL.md` | 人格定义、语气、边界 | 每会话首条消息 |
| `TOOLS.md` | 环境特定的工具说明 | 每会话首条消息 |
| `USER.md` | 用户信息、偏好、项目背景 | 每会话首条消息 |
| `IDENTITY.md` | 助手身份（名称、表情、头像） | 每会话首条消息 |
| `MEMORY.md` | 长期记忆（安全敏感内容） | 仅主会话 |

---

## ⚙️ 配置 openclaw.json

`~/.openclaw/openclaw.json` 是 OpenClaw 的核心配置文件，使用 **JSON5** 格式（支持注释和尾随逗号）。

### 最小配置示例

```json
{
  "agents": {
    "defaults": {
      "workspace": "~/.openclaw/workspace"
    }
  },
  "channels": {
    "telegram": {
      "enabled": true,
      "botToken": "123456:ABC...",
      "dmPolicy": "pairing",
      "allowFrom": ["tg:123456789"]
    }
  }
}
```

### Agents 配置

```json
{
  "agents": {
    "defaults": {
      "workspace": "~/.openclaw/workspace",
      "model": {
        "primary": "anthropic/claude-sonnet-4-5",
        "fallbacks": ["openai/gpt-5.2"]
      },
      "heartbeat": {
        "every": "30m",
        "target": "last"
      }
    }
  }
}
```

### Session 会话管理

```json
{
  "session": {
    "dmScope": "per-channel-peer",
    "reset": {
      "mode": "daily",
      "atHour": 4,
      "idleMinutes": 120
    }
  }
}
```

---

## 💬 配置对话终端（Channels）

### DM 安全策略

| 策略 | 说明 | 适用场景 |
|------|------|----------|
| `pairing` | 未知发送者获得配对码，需主人批准 | **默认，最安全** |
| `allowlist` | 仅允许列表中的发送者 | 已知联系人 |
| `open` | 允许所有入站 DM | 公开机器人 |
| `disabled` | 忽略所有 DM | 仅群组使用 |

### Telegram 配置

```json
{
  "channels": {
    "telegram": {
      "enabled": true,
      "botToken": "your-bot-token",
      "dmPolicy": "pairing",
      "allowFrom": ["tg:123456789"],
      "streaming": "partial"
    }
  }
}
```

---

## 🤖 配置多智能体（Multi-Agent）

```json
{
  "agents": {
    "defaults": {
      "workspace": "~/.openclaw/workspace"
    },
    "list": [
      {
        "id": "main",
        "description": "通用助手"
      },
      {
        "id": "coder",
        "workspace": "~/.openclaw/workspace-coder",
        "description": "编程专家"
      }
    ]
  }
}
```

---

## 🧩 技能安装

> 💡 **提示**：技能让你可以一键添加新能力，如图像生成、天气查询、GitHub 操作、视频处理等，无需手动配置每个工具。

OpenClaw 使用**技能系统**来扩展功能。技能是可复用的功能模块，可以通过 ClawHub CLI 从 [clawhub.com](https://clawhub.com) 安装。

### 安装 ClawHub CLI

首先确保已安装 ClawHub 命令行工具：

```bash
npm install -g clawhub
```

### 搜索技能

在 ClawHub 上搜索你需要的技能：

```bash
# 搜索关键词
clawhub search "postgres backups"
clawhub search "image generation"
clawhub search "weather"
```

### 安装技能

找到想要的技能后，使用以下命令安装：

```bash
# 安装最新版本
clawhub install baoyu-image-gen

# 安装指定版本
clawhub install baoyu-image-gen --version 1.2.3
```

### 管理技能

ClawHub CLI 常用命令

| 命令 | 说明 | 示例 |
|------|------|------|
| `clawhub list` | 列出已安装的技能 | 查看当前工作空间的所有技能 |
| `clawhub update <skill>` | 更新指定技能到最新版本 | `clawhub update baoyu-image-gen` |
| `clawhub update --all` | 更新所有技能 | 批量更新所有已安装技能 |
| `clawhub update --force` | 强制更新（忽略版本检查） | 解决版本冲突时使用 |

### 常用推荐技能

热门 OpenClaw 技能推荐

| 技能名称 | 功能 | 安装命令 |
|----------|------|----------|
| `baoyu-image-gen` | AI 图像生成（OpenAI、Google、Replicate 等） | `clawhub install baoyu-image-gen` |
| `weather` | 天气查询和预报 | `clawhub install weather` |
| `github` | GitHub 操作（Issues、PR、代码审查） | `clawhub install github` |
| `video-frames` | 视频帧提取和剪辑 | `clawhub install video-frames` |
| `xurl` | X (Twitter) API 操作 | `clawhub install xurl` |
| `find-skills` | 帮助发现和安装技能 | `clawhub install find-skills` |

### 技能工作原理

技能是包含以下内容的文件夹：

```
my-skill/
├── SKILL.md                           # 技能定义和使用说明
└── 其他文件                            # 脚本、配置等
```

> ✅ **注意**：安装后，OpenClaw 会自动识别技能能力，并在相关任务触发时自动调用。无需额外配置。

### 发布自己的技能

如果你有自己开发的技能，可以发布到 ClawHub 分享：

```bash
# 登录 ClawHub
clawhub login

# 发布技能
clawhub publish ./my-skill \
  --slug my-skill \
  --name "My Skill" \
  --version 1.0.0 \
  --changelog "Initial release"
```

> ⚠️ **注意**：技能默认注册表为 https://clawhub.com，可通过 `CLAWHUB_REGISTRY` 环境变量或 `--registry` 参数覆盖。

---

## ⌨️ 常用 CLI 命令

### Gateway 管理

```bash
# 查看状态
openclaw gateway status

# 启动/停止/重启
openclaw gateway start
openclaw gateway stop
openclaw gateway restart
```

### 配置管理

```bash
# 运行配置向导
openclaw onboard

# 获取/设置配置值
openclaw config get agents.defaults.workspace
openclaw config set agents.defaults.model.primary "openai/gpt-5.2"
```

### 诊断工具

```bash
# 健康检查
openclaw doctor

# 自动修复
openclaw doctor --fix

# 查看日志
openclaw logs --follow
```

---

## 🔒 安全最佳实践

> ⚠️ **警告**：**永远不要**在未经保护的情况下公开 DM：使用 `dmPolicy: "pairing"` 或 `allowlist` 而非 `open`

### 多用户环境

```json
{
  "session": {
    "dmScope": "per-channel-peer"
  }
}
```

### 沙盒执行

```json
{
  "agents": {
    "defaults": {
      "sandbox": {
        "mode": "non-main",
        "scope": "agent"
      }
    }
  }
}
```

---

## 🔧 故障排除

常见错误及解决方案

| 错误 | 原因 | 解决 |
|------|------|------|
| `Config validation failed` | 配置格式错误 | 运行 `openclaw doctor` |
| `Unauthorized` | API Key 无效 | 检查 `auth` 配置 |
| `Session not found` | 会话已过期 | 发送 `/new` 重置 |

---

## 🔗 资源链接

- **官网**: [openclaw.ai](https://openclaw.ai)
- **文档**: [docs.openclaw.ai](https://docs.openclaw.ai)
- **GitHub**: [github.com/openclaw/openclaw](https://github.com/openclaw/openclaw)
- **Discord**: [discord.gg/clawd](https://discord.gg/clawd)
- **技能市场**: [clawhub.com](https://clawhub.com)

---

## 📝 总结

OpenClaw 是一个功能强大、灵活的个人 AI 助手平台。关键要点：

1. **Gateway 是核心** - 所有功能都围绕 Gateway 展开
2. **Workspace 是工作空间** - 保持文件整洁，控制 token 使用
3. **配置即代码** - `openclaw.json` 定义一切行为
4. **安全第一** - 默认使用配对模式，谨慎开放 DM
5. **多智能体支持** - 可以为不同任务创建专门的助手

---

祝使用愉快！🦞