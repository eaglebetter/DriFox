<!-- README.md -->
<p align="center">
  <img width="16%" align="center" src="images/drifoxlogo.png" alt="logo">
</p>
<p align="center">
  <img width="40%" align="center" src="images/drifoxtext.png" alt="logo">
</p>

<div align="center">

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![License](https://img.shields.io/github/license/martin98-afk/DriFox)
![Stars](https://img.shields.io/github/stars/martin98-afk/DriFox)
![Downloads](https://img.shields.io/github/downloads/martin98-afk/DriFox/total)
![Last Commit](https://img.shields.io/github/last-commit/martin98-afk/DriFox)

</div>

<h1 align="center">DriFox 飘狐 — 一个轻量化 AI 桌面对话助手</h1>

![对话框界面](images/上下文压缩.png)



---

## 设计理念

**不做大而全的 IDE。** DriFox 只是一个对话框 —— 随时调出，随意提问，随性分支。

| 特性 | 说明 |
|------|------|
| 🎯 **极简界面** | 仅一个悬浮置顶对话框，无项目概念，随开随用 |
| 🔀 **分支会话** | 问题分叉，多个窗口并行探索不同答案，互不干扰 |
| 🧠 **长记忆** | 越用越懂你的偏好、习惯、禁忌 |
| 🛠️ **代码工具** | 30+ 工具：读、写、搜索、执行、diff |
| 🔌 **多模型** | OpenAI / Claude / DeepSeek / 通义 等随时切换 |

---

## 快速开始

### 环境要求
- Python 3.8+
- PyQt5 >= 5.15.0

### 安装

```bash
git clone https://github.com/martin98-afk/DriFox.git
cd DriFox

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt
```

### 运行

```bash
python main.py
```

---

## 使用方式

### 基本操作
1. **提问** – 底部输入框发送消息，回车即发
2. **分支** – 标题栏点击「分支」按钮，从当前对话创建并行窗口
3. **复制窗口** – 创建多个独立对话框，同时处理不同任务

### 窗口操作
| 操作 | 说明 |
|------|------|
| 点击标题栏「分支」| 从当前对话分叉，创建新窗口继续探索 |
| 点击标题栏「复制」| 创建当前窗口的独立副本 |
| 拖拽标题栏 | 移动窗口位置 |
| `Ctrl+L` | 清除当前会话 |

---

## 架构一览

```
┌─────────────────────────────────────────────────────────┐
│                     DriFox 架构                         │
├─────────────────────────────────────────────────────────┤
│  UI 层                                                  │
│  ├── 悬浮对话框（消息卡片、输入框、工具浮窗）            │
│  ├── 分支/复制窗口机制                                   │
│  └── 上下文用量环                                       │
├─────────────────────────────────────────────────────────┤
│  引擎层                                                  │
│  ├── ChatEngine – 对话上下文组装                         │
│  ├── ToolExecutor – 工具执行（文件/终端/网络）          │
│  └── AgentManager – Agent 定义与权限控制                │
├─────────────────────────────────────────────────────────┤
│  存储层                                                  │
│  ├── SessionManager – 会话管理                          │
│  ├── MemoryManager – 长期记忆（SQLite）                 │
│  └── HistoryManager – 归档与检索                        │
└─────────────────────────────────────────────────────────┘
```

### Agent 系统

采用 Primary / Subagent / Hidden 三层设计：

| 类型 | Agent | 用途 |
|------|-------|------|
| **Primary** | `plan` | 任务规划（只读，不改文件）|
| **Primary** | `build` | 代码编写（全工具权限）|
| **Subagent** | `explore` | 代码库探索 |
| **Subagent** | `general` | 通用任务并行执行 |
| **Hidden** | `summary/compaction/title` | 自动调用：摘要/压缩/标题 |

### 工具系统（30+）

| 类别 | 工具 |
|------|------|
| 文件 | read / write / edit / multiedit / patch / grep / glob / list / diff |
| 执行 | bash / run_verify |
| 网络 | webfetch / websearch |
| 代码 | get_diagnostics |
| 记忆 | memory_save / memory_search / memory_list |
| 任务 | todowrite / todoread / ask_question / task / skill |

### 记忆系统

自动学习用户偏好，支持置信度评分、冲突管理、分类组织（偏好/约束/习惯）。

---

## 项目结构

```
DriFox/
├── main.py                    # 运行入口
├── requirements.txt          # 依赖
├── app/
│   ├── llm_chatter/          # 核心模块
│   │   ├── core/             # 引擎（chat/engine, agent, tool, memory）
│   │   ├── agents/           # Agent 定义
│   │   ├── skills/           # Skills 技能
│   │   └── widgets/          # UI 组件
│   └── widgets/              # 通用组件
├── .drifox/                  # 应用数据
│   └── sessions.db           # SQLite 会话与记忆
├── icons/                    # 图标资源
└── images/                   # Logo 等图片
```

---

## 开发者指南

### 自定义 Agent

在 `app/llm_chatter/agents/` 创建 `.md` 文件：

```markdown
---
name: my_agent
mode: primary
permission:
  read: allow
  bash: ask
---
# My Agent
你的描述...
```

### 自定义 Skill

在 `.drifox/skills/<name>/` 下添加 `SKILL.md`。

---

## 许可证

MIT License

---

## 致谢

- [PyQt-Fluent-Widgets](https://github.com/zhiyiYo/PyQt-Fluent-Widgets) – UI 库
- [Loguru](https://github.com/Delgan/loguru) – 日志
- [OpenAI Python Client](https://github.com/openai/openai-python) – API 客户端
- [FastAPI](https://github.com/tiangolo/fastapi) – Web 框架

---

## Star History

<a href="https://www.star-history.com/#martin98-afk/DriFox&type=date&legend=top-left">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=martin98-afk/DriFox&type=date&theme=dark&legend=top-left" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=martin98-afk/DriFox&type=date&theme=dark&legend=top-left" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=martin98-afk/DriFox&type=date&legend=top-left" />
 </picture>
</a>