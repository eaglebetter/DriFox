<!-- README.md -->
<p align="center">
  <img width="50%" align="center" src="images/drifoxlogo.png" alt="logo">
</p>

<div align="center">
  <h1>DriFox - 智能编程助手</h1>

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

DriFox（飘狐）是一个基于大语言模型的智能编程助手，采用 OpenCode 风格的 Agent 架构，提供全面的工具系统和长期记忆能力。支持多 Provider（OpenAI、DeepSeek、Claude 等）切换，可独立运行或集成到 CanvasMind 画布中，实现智能化编程工作流。

<img src="images/drifoxtext.png" width="100%" height="100%"><br>

---

## 🌟 核心特性

### 🤖 多 Provider 支持
- **OpenAI** / **DeepSeek** / **Anthropic (Claude)** / **硅基流动** / **Groq** / **Ollama** / **MiniMax** 等
- 支持 **Azure OpenAI** 和 **自定义 API Endpoint**
- 模型配置持久化，支持 per-session 切换
- 流式输出 + 非流式输出自适应

### 🧠 OpenCode 风格 Agent 系统
- **多 Agent 架构**：Primary / Subagent / Hidden 三种模式
- **灵活配置**：支持 Markdown (YAML frontmatter) 或 YAML 文件定义 Agent
- **Permission 系统**：细粒度工具权限控制（allow / deny / ask）
- **Agent Profiles**：自定义 temperature、top_p、max_steps、模型选择
- **内置 Agents**：plan、build、explore、skillful、general、summary、compaction、title

| Agent | 用途 |
|-------|------|
| `plan` | 任务规划与分解 |
| `build` | 代码编写与修改 |
| `explore` | 项目探索与分析 |
| `skillful` | 技能调用专家 |
| `general` | 通用对话 |
| `summary` | 会话总结 |
| `compaction` | 内容压缩 |

### 🛠️ 全面的工具系统 (30+)
| 类别 | 工具 |
|------|------|
| **文件操作** | `read`, `write`, `edit`, `multiedit`, `patch`, `grep`, `glob`, `list`, `diff_files` |
| **终端** | `bash`, `run_verify` |
| **Web** | `webfetch`, `websearch` |
| **代码分析** | `get_diagnostics` (Python/JS/TS/Shell) |
| **任务管理** | `todowrite`, `todoread`, `ask_question` |
| **Skills** | `skill`, `list_skills`, `scan_repo`, `stage_files` |
| **记忆** | `memory_list`, `memory_search`, `memory_save`, `memory_consolidate` |
| **子智能体** | `task` (分发任务到 build/plan/skillful/explore) |

### 💾 长期记忆系统
- **会话持久化**：SQLite 数据库存储历史会话
- **跨会话记忆**：置信度评分 + 冲突管理
- **分类组织**：任务偏好、项目约束、用户习惯
- **自动汇总**：从对话中自动提取关键事实

### 🎨 Skills 技能系统
- **brainstorming** – 头脑风暴与创意激发
- **gk-optimizer** – 工况寻优范围调整（工业专家规则）
- **writing-plans** – 计划文档编写

### 🌐 API 服务
- **FastAPI** 后端，支持独立 API 服务
- 会话管理 + 隔离上下文支持
- Swagger 文档自动生成

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
  write: allow
  edit: allow
  bash: allow
---
# Build Agent

你是一个经验丰富的工程师，专注于代码实现...

## 偏好技能
以下是部分用户偏好的智能体技能，如果以下技能不能满足用户需求，可以使用 `list_skills` 技能加载完整技能列表：
```

### Permission 规则
```yaml
permission:
  "*": "allow"          # 默认允许
  read: "allow"
  write: "allow"
  bash: "deny"          # 禁用 bash
  task:
    "build": "allow"    # 允许调用 build 子智能体
    "*": "deny"         # 拒绝其他子智能体
```

---

## 🛠️ 工具权限说明

| 权限值 | 行为 |
|--------|------|
| `allow` | 自动执行，无需确认 |
| `ask` | 执行前询问用户 |
| `deny` | 禁止执行 |

---

## 🎮 使用指南

### 基本操作
1. **选择 Provider** – 顶部下拉框选择 LLM 服务商
2. **选择模型** – 选择具体模型（如 gpt-4o、deepseek-chat）
3. **输入消息** – 底部输入框发送消息
4. **查看结果** – 消息卡片实时渲染，支持代码高亮

### 高级功能
- **切换 Agent** – 工具栏切换不同 Agent 模式
- **工具调用** – 侧边栏显示工具执行状态
- **文件预览** – 工具调用结果支持差异对比
- **历史记录** – 侧边栏查看历史会话
- **记忆管理** – 管理长期记忆内容

### 快捷键
- `Enter` – 发送消息
- `Shift+Enter` – 换行
- `Ctrl+L` – 清除当前会话

---

## 🗂️ 项目结构

```
DriFox/
├── main.py                    # 独立运行入口
├── requirements.txt          # 依赖列表
├── build.py                   # PyInstaller 打包脚本
├── app/
│   ├── llm_chatter/          # 核心 LLM 模块
│   │   ├── core/             # 核心引擎
│   │   │   ├── agent.py      # Agent 管理器
│   │   │   ├── chat_engine.py    # 聊天引擎
│   │   │   ├── tool_executor.py  # 工具执行器
│   │   │   └── memory_manager.py # 记忆管理器
│   │   ├── agents/           # Agent 定义 (Markdown/YAML)
│   │   ├── skills/           # 技能定义
│   │   ├── tools/            # 工具实现
│   │   ├── widgets/          # UI 组件
│   │   └── utils/            # 工具函数
│   ├── sqlite_database/      # SQLite 数据库模块
│   ├── utils/                # 通用工具
│   └── widgets/              # 通用 UI 组件
├── canvas_files/            # 画布文件目录
│   ├── sessions.db           # 会话数据库
│   └── workflows/            # 工作流存储
└── icons/                    # 图标资源
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

### 添加自定义 Tool
在 `app/llm_chatter/tools/` 目录下的对应模块中添加：
```python
from app.llm_chatter.tools import register_tool

@register_tool
def my_custom_tool(arg1: str) -> str:
    """我的自定义工具"""
    return f"处理: {arg1}"
```

---

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

### 开发环境搭建

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

# 5. 运行测试（如有）
pytest
```

---

## 📖 文档

更多文档正在编写中...

---

## 💬 获取帮助

- 📋 [提交 Issue](https://github.com/martin98-afk/DriFox/issues) - 报告问题或请求功能
- 💬 [Discussions](https://github.com/martin98-afk/DriFox/discussions) - 提问和交流

---

## 📄 许可证

本项目基于 [GPLv3 License](LICENSE) 开源。

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
