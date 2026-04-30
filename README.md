<!-- README.md -->
<p align="center">
  <img width="50%" align="center" src="images/drifoxlogo.png" alt="logo">
</p>

<img src="images/drifoxtext.png" width="100%" height="100%"><br>

<div align="center">
  <h1>飘狐</h1>

  [🇨🇳 中文](README.md)

</div>

<div align="center">

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![License](https://img.shields.io/github/license/martin98-afk/DriFox)
![Stars](https://img.shields.io/github/stars/martin98-afk/DriFox)
![Downloads](https://img.shields.io/github/downloads/martin98-afk/DriFox/total)
![Last Commit](https://img.shields.io/github/last-commit/martin98-afk/DriFox)
![Issues](https://img.shields.io/github/issues/martin98-afk/DriFox)

</div>

飘狐是一个基于大语言模型的智能编程助手，采用 OpenCode 风格的 Agent 架构，提供全面的工具系统和长期记忆能力。支持多 Provider（OpenAI、DeepSeek、Claude 等）切换，可独立运行或集成到 CanvasMind 画布中，实现智能化编程工作流。
---

## 🌟 核心特性

### 🤖 多 Provider 支持

| Provider | 模型示例 | API 地址 |
|----------|----------|----------|
| **OpenAI** | gpt-4o, gpt-4o-mini, gpt-4-turbo | api.openai.com |
| **Anthropic (Claude)** | claude-sonnet-4, claude-3-5-sonnet | api.anthropic.com |
| **DeepSeek** | deepseek-chat, deepseek-coder | api.deepseek.com |
| **Google Gemini** | gemini-2.0-flash, gemini-1.5-pro | generativelanguage.googleapis.com |
| **阿里通义 (DashScope)** | qwen3-max, qwen3-plus | dashscope.aliyuncs.com |
| **智谱AI** | glm-4-flash, glm-4-plus | open.bigmodel.cn |
| **硅基流动** | Qwen2.5-7B, glm4-9b-chat | api.siliconflow.cn |
| **MiniMax** | MiniMax-M2.7, MiniMax-M2.5 | api.minimax.chat |
| **Groq** | llama-3.3-70b, qwen3-32b | api.groq.com |
| **百度千帆** | ernie-3.5-8k, ernie-speed-128k | qianfan.baidubce.com |
| **Ollama** | llama3, qwen2.5, mistral | localhost:11434 |
| **LMStudio** | 本地模型 | localhost:1234 |

- 支持 **Azure OpenAI** 和 **自定义 API Endpoint**
- 模型配置持久化，支持 per-session 切换
- 流式输出 + 非流式输出自适应
- 自动识别 Provider 类型和上下文窗口限制

### 🧠 OpenCode 风格 Agent 系统

采用 **Primary / Subagent / Hidden** 三层架构：

#### Primary Agents（主智能体，面向用户）
| Agent | 用途 | 特点 |
|-------|------|------|
| `plan` | 任务规划与分解 | **只读**，不直接修改文件，专注规划 |
| `build` | 代码编写与修改 | 全工具权限，专注实现 |

#### Subagent（子智能体，并行执行）
| Agent | 用途 | 特点 |
|-------|------|------|
| `explore` | 代码库探索 | 只读，深入分析项目结构 |
| `general` | 通用任务执行 | 并行处理复杂任务 |

#### Hidden（隐藏智能体，自动调用）
| Agent | 用途 | 触发条件 |
|-------|------|----------|
| `summary` | 会话摘要生成 | 新会话创建时 |
| `compaction` | 上下文压缩 | Token 接近限制时 |
| `title` | 会话标题生成 | 新会话创建时 |

#### Permission 权限系统
```yaml
permission:
  "*": "allow"          # 默认规则
  read: "allow"        # 允许读取
  write: "allow"       # 允许写入
  bash: "ask"          # 执行前询问
  task:
    "build": "allow"   # 允许调用 build
    "*": "deny"        # 拒绝其他子智能体
```

| 权限值 | 行为 |
|--------|------|
| `allow` | 自动执行，无需确认 |
| `ask` | 执行前询问用户 |
| `deny` | 禁止执行 |

### 🛠️ 完整的工具系统（30+ 工具）

#### 文件操作
| 工具 | 功能 |
|------|------|
| `read` | 读取文件内容，支持行号和偏移 |
| `write` | 创建或覆盖文件 |
| `edit` | 精确字符串替换 |
| `multiedit` | 批量编辑同一文件 |
| `patch` | unified diff 格式修改 |
| `grep` | 正则表达式搜索 |
| `glob` | 通配符模式查找文件 |
| `list` | 列出目录内容 |
| `diff_files` | 文件差异对比 |

#### 终端与执行
| 工具 | 功能 |
|------|------|
| `bash` | 执行 Shell 命令 |
| `run_verify` | 运行验证/测试命令 |

#### 网络工具
| 工具 | 功能 |
|------|------|
| `webfetch` | 获取网页内容 |
| `websearch` | 网络搜索 |

#### 代码分析
| 工具 | 功能 |
|------|------|
| `get_diagnostics` | Python/JS/TS/Shell 语法检查 |

#### 任务管理
| 工具 | 功能 |
|------|------|
| `todowrite` / `todoread` | 待办事项管理 |
| `ask_question` | 向用户提问 |

#### Skills 与子智能体
| 工具 | 功能 |
|------|------|
| `skill` | 加载技能模块 |
| `list_skills` | 列出可用技能 |
| `scan_repo` | 项目结构扫描 |
| `stage_files` | 文件标记 |
| `task` | 分发任务给子智能体 |

#### 长期记忆
| 工具 | 功能 |
|------|------|
| `memory_list` | 列出记忆 |
| `memory_search` | 搜索记忆 |
| `memory_save` | 保存记忆 |
| `memory_consolidate` | 从会话提炼记忆 |

### 💾 长期记忆系统

```
┌─────────────────────────────────────────────────────────┐
│                    记忆存储层                           │
├─────────────────────────────────────────────────────────┤
│  SQLite (.drifox/sessions.db)                          │
│  ├── 会话历史 (messages)                                │
│  └── 长期记忆 (user_memories)                           │
├─────────────────────────────────────────────────────────┤
│                    记忆管理层                           │
├─────────────────────────────────────────────────────────┤
│  置信度评分 │ 冲突管理 │ 分类组织 (偏好/约束/习惯)      │
├─────────────────────────────────────────────────────────┤
│                    自动提炼                            │
├─────────────────────────────────────────────────────────┤
│  session → compact → summarize → memory_save           │
└─────────────────────────────────────────────────────────┘
```

### 🎨 Skills 技能系统

内置技能可通过 `list_skills` 查看，`skill <name>` 加载使用：

| Skill | 用途 |
|-------|------|
| `brainstorming` | 头脑风暴与创意激发 |
| `caveman` | 简单直白的需求分析 |
| `find-skills` | 技能查找专家 |
| `git-commit` | Git 提交信息生成 |
| `skill-creator` | 自定义技能创建 |
| `writing-plans` | 计划文档编写 |

技能搜索路径（优先级递减）：
1. `.drifox/skills/`
2. `app/llm_chatter/skills/`
3. `~/.agents/skills/`

### 🌐 API 服务（可选）

- **FastAPI** 后端，支持独立 API 服务运行
- 会话管理 + 隔离上下文支持
- Swagger 文档自动生成 (`http://localhost:<port>/docs`)
- 可通过配置启用/禁用

---

## 🚀 快速开始

### 环境要求
- Python 3.8+
- PyQt5 >= 5.15.0

### 安装

```bash
# 克隆仓库
git clone https://github.com/martin98-afk/DriFox.git
cd DriFox

# 创建虚拟环境（推荐）
python -m venv .venv

# 激活虚拟环境
# Linux/Mac:
source .venv/bin/activate
# Windows:
.venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 运行

```bash
python main.py
```

---

## 📋 Agent 定义示例

### Markdown 格式 (agents/build.md)
```markdown
---
name: build
description: 代码编写专家，负责实现具体功能
mode: primary
temperature: 0.3
steps: 30
model: gpt-4o
permission:
  "*": allow
---

# Role
你是一个经验丰富的工程师，专注于代码实现...

## 偏好技能
以下是部分用户偏好的智能体技能...
```

---

## 🎮 使用指南

### 基本操作
1. **选择 Provider** – 顶部下拉框选择 LLM 服务商
2. **选择模型** – 选择具体模型（如 gpt-4o、deepseek-chat）
3. **输入消息** – 底部输入框发送消息
4. **查看结果** – 消息卡片实时渲染，支持代码高亮

### 高级功能
- **切换 Agent** – 工具栏切换不同 Agent 模式（plan/build）
- **工具调用** – 浮窗显示工具执行状态
- **文件预览** – 工具调用结果支持差异对比
- **历史记录** – 侧边栏查看历史会话
- **记忆管理** – 管理长期记忆内容
- **复制窗口** – 将当前窗口复制为独立弹窗
- **上下文用量** – 显示当前上下文窗口使用率

### 快捷键
| 快捷键 | 功能 |
|--------|------|
| `Enter` | 发送消息 |
| `Shift+Enter` | 换行 |
| `Ctrl+L` | 清除当前会话 |

---

## 🗂️ 项目结构

```
DriFox/
├── main.py                    # 独立运行入口
├── requirements.txt          # 依赖列表
├── build.py                   # PyInstaller 打包脚本
├── generate_icon_qrc.py       # 图标资源生成
├── app.config                 # 应用配置
│
├── app/
│   ├── llm_chatter/          # 核心 LLM 对话模块
│   │   ├── core/             # 核心引擎
│   │   │   ├── agent.py          # Agent 管理器 + Permission 解析
│   │   │   ├── chat_engine.py     # 聊天引擎（流式/非流式）
│   │   │   ├── tool_executor.py   # 工具执行器
│   │   │   ├── memory_manager.py # 长期记忆管理
│   │   │   ├── sub_agent_executor.py  # 子智能体执行器
│   │   │   ├── provider_profile.py    # Provider 能力配置
│   │   │   └── task_state.py     # 任务状态管理
│   │   ├── agents/           # Agent 定义 (Markdown/YAML)
│   │   ├── skills/           # Skills 技能定义
│   │   ├── tools/            # 工具实现
│   │   ├── widgets/          # UI 组件
│   │   ├── api/              # API 服务
│   │   └── utils/            # 工具函数
│   │
│   ├── sqlite_database/      # SQLite 数据库模块
│   ├── utils/                # 通用工具
│   │   ├── config.py             # 配置管理
│   │   ├── utils.py              # 工具函数
│   │   └── icons_rc.py           # 图标资源
│   │
│   └── widgets/              # 通用 UI 组件
│       ├── basic_widget/         # 基础组件
│       ├── card_widget/          # 卡片组件
│       └── dialog_widget/        # 弹窗组件
│
├── .drifox/                  # 应用数据目录
│   ├── sessions.db           # 会话数据库
│   ├── backups/              # 自动备份
│   └── archived/             # 归档文件
│
├── canvas_files/            # 画布文件目录
├── icons/                   # SVG 图标
├── images/                  # 图片资源
└── logs/                    # 日志文件
```

---

## 🧪 开发说明

### 添加自定义 Agent
在 `app/llm_chatter/agents/` 目录下创建 `.md` 文件：

```markdown
---
name: my_agent
description: 我的自定义 Agent
mode: primary
temperature: 0.7
permission:
  read: allow
  bash: ask
---
# My Agent

你的 Agent 描述...
```

### 添加自定义 Skill
创建目录 `app/llm_chatter/skills/<skill_name>/`，添加 `SKILL.md` 文件：

```markdown
---
name: my-skill
description: 我的自定义技能
---

# My Skill

技能描述...
```

### 添加新 Provider
在 `app/llm_chatter/constants.py` 的 `PROVIDER_MODELS` 和 `FREE_PROVIDERS` 中添加配置。

---

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

```bash
# 1. Fork 并克隆仓库
git clone https://github.com/martin98-afk/DriFox.git
cd DriFox

# 2. 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 运行开发版本
python main.py
```

---

## 💬 获取帮助

- 📋 [提交 Issue](https://github.com/martin98-afk/DriFox/issues) - 报告问题或请求功能
- 💬 [Discussions](https://github.com/martin98-afk/DriFox/discussions) - 提问和交流

---

## 📄 许可证

本项目基于 MIT License 开源。

---

## 🙏 致谢

- [PyQt-Fluent-Widgets](https://github.com/zhiyiYo/PyQt-Fluent-Widgets) – Fluent Design UI 库
- [Loguru](https://github.com/Delgan/loguru) – 优雅的 Python 日志库
- [OpenAI Python Client](https://github.com/openai/openai-python) – OpenAI API 客户端
- [FastAPI](https://github.com/tiangolo/fastapi) – 现代 Python Web 框架

---

## Star History

<a href="https://www.star-history.com/#martin98-afk/DriFox&type=date&legend=top-left">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=martin98-afk/DriFox&type=date&theme=dark&legend=top-left" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=martin98-afk/DriFox&type=date&theme=dark&legend=top-left" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=martin98-afk/DriFox&type=date&legend=top-left" />
 </picture>
</a>
