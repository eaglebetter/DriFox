---
name: agent-canvas-designer
description: >
  将任意业务需求可视化为智能体编排流程图，生成可导入画布模拟器的 JSON 配置。
  覆盖：节点选型 → 提示词编写 → 布局规划 → 配置输出 → 自检验收。
  Use when 用户说"设计智能体流程"、"画布设计"、"智能体编排"、"编排智能体"、
  "workflow design"、"agent pipeline"、"生成画布JSON"、"workflow design"。
---

# 智能体画布设计技能

将业务需求转化为可视化的智能体编排流程，生成可导入画布模拟器的 JSON 配置。

**重要**：技能完成后必须提供 md 格式的 HTML 链接供用户点击打开画布。

---

## 快速开始

**输入**：业务场景描述（如"客服工单路由"、"数据分析报告生成"）

**输出**：
```json
{
  "version": "2.0",
  "flow": "custom",
  "meta": {"title": "流程名"},
  "nodes": [...],
  "connections": [...]
}
```

**示例对话**：
```
你：帮我设计一个客服智能体流程
我：了解！请描述业务场景：入口用户输入是什么？要处理哪些类型的请求？最终输出给谁？
```

---

## 工作流总览

```
Phase 1: 需求理解
    → 识别用户场景类型
    ↓
[Checkpoint] ← 确认节点数量/复杂度
    ↓
Phase 2: 节点选型与布局
    → 选定节点类型组合
    → 规划坐标布局
    ↓
Phase 3: 配置编写
    → 编写 system_prompt / user_prompt
    → 填写节点参数
    ↓
[Checkpoint] ← 自检验收
    ↓
Phase 4: 输出交付

→ 生成 JSON（粘贴到对话中或保存为 .json 文件）
→ 提供预览建议
→ **⚠️ 必须输出 md 链接**：
  ```
  [👉 点击打开画布](替换为 agent_canvas.html 的实际路径)
  ```
  示例（相对路径）：`[👉 点击打开画布](./skills/agent-canvas-designer/assets/agent_canvas.html)`
  
  用户点击链接后可在画布中导入 JSON 配置预览效果

**重要**：完成技能后必须自动打开画布文件供用户预览。技能完成后执行：

```bash
explorer "{skill_path}\assets\agent_canvas.html"
```

---

## Phase 1: 需求理解
```

---

## Phase 1: 需求理解

**必问**：
1. 入口是什么？（用户输入/API触发/定时）
2. 有哪些决策分支？（分类/条件判断）
3. 需要哪些外部能力？（知识库/数据库/API）
4. 输出形式？（对话回复/报告/文件/触发动作）

**输出**：确认流程类型（路由型/RAG型/流水线型/人在回路型）

---

## Phase 2: 节点选型

| 场景 | 推荐节点组合 |
|------|-------------|
| 简单问答 | start → llm → reply → end |
| 分类路由 | start → classifier → [分支x3] → reply → end |
| RAG 增强 | start → knowledge → llm → reply → end |
| 多步分析 | start → llm → agent → code → llm → reply → end |
| 人在回路 | start → agent → container → llm → reply → end |

详见 → [references/NODE-GUIDE.md](references/NODE-GUIDE.md)

---

## Phase 3: 提示词编写

**三段式 system_prompt**：
```
你是[角色]。负责[一句话职责]。

需要输出：
1. [输出项1]：[说明]
2. [输出项2]：[说明]

规则：
1. [硬约束]
2. [硬约束]
3. 只输出JSON，不要额外文字
```

**变量引用**：
- `{{sys.query}}` — 用户原始输入
- `{{n3.output}}` — 节点 n3 的完整输出
- `{{n3.output.field}}` — 节点 n3 输出中的指定字段

详见 → [references/PROMPT-TEMPLATE.md](references/PROMPT-TEMPLATE.md)

---

## Phase 4: 布局规则

**坐标规范**：
- 原点左上角，x → 右，y → 下
- 默认节点：180×60px，容器：320×180px
- 水平间距：240px，垂直间距：80px

**多流程排列**：
- 流程1: y = 240
- 流程2: y = 480
- 流程3: y = 700

详见 → [references/LAYOUT-RULE.md](references/LAYOUT-RULE.md)

---

## 输出格式

```json
{
  "version": "2.0",
  "flow": "custom",
  "meta": {"title": "流程名", "description": "说明"},
  "nodes": [
    {"id":"n1","type":"start","label":"开始","x":80,"y":240,"config":{}},
    {"id":"n2","type":"llm","label":"问题分析","x":320,"y":225,"config":{...}}
  ],
  "connections": [
    {"sourceId":"n1","targetId":"n2"}
  ]
}
```

**硬约束**：
- 所有 config 值是字符串（数字也写成 "5"）
- tools 引号转义 `\"`
- y ≥ 80

详见 → [references/OUTPUT-FORMAT.md](references/OUTPUT-FORMAT.md)

---

## 自检验收清单

完成 JSON 输出后强制自检：

| 检查项 | 合格标准 |
|--------|----------|
| start/end | 每个流程有且仅有一个 start 和 end |
| 连接闭合 | 所有非 end 节点都有出边 |
| 坐标不越界 | y ≥ 80，x ≥ 80 |
| config 合法 | 所有字符串值无转义错误 |
| tools 转义 | `"[\"A\",\"B\"]"` 格式 |
| 变量引用正确 | `{{节点ID.output.field}}` 格式 |

详见 → [references/PITFALLS.md](references/PITFALLS.md)

---

## 相关资源

| 文件 | 用途 |
|------|------|
| [NODE-GUIDE.md](references/NODE-GUIDE.md) | 14 种节点类型详解与选型决策树 |
| [PROMPT-TEMPLATE.md](references/PROMPT-TEMPLATE.md) | 各场景提示词模板与变量引用规范 |
| [LAYOUT-RULE.md](references/LAYOUT-RULE.md) | 坐标系统、间距规则、多流程排列 |
| [CONFIG-REFERENCE.md](references/CONFIG-REFERENCE.md) | 各节点类型的 config 字段详解 |
| [OUTPUT-FORMAT.md](references/OUTPUT-FORMAT.md) | JSON 结构规范与示例 |
| [PITFALLS.md](references/PITFALLS.md) | 常见错误与避坑指南 |
| [EXAMPLES/customer-service.json](references/EXAMPLES/customer-service.json) | 客服场景完整示例 |
| [EXAMPLES/data-analysis.json](references/EXAMPLES/data-analysis.json) | 数据分析场景完整示例 |

---

## 热更新画布流程 v3.0

**架构升级**：v3.0 使用 SSE（Server-Sent Events）实现秒级热推送，替代旧版 3s 轮询。

### 技术栈

| 层 | 技术 | 说明 |
|----|------|------|
| 前端 | TypeScript + React + React Flow + Vite | 组件化画布 |
| 热更新 | SSE (Server-Sent Events) | 500ms 文件监控 + 即时推送 |
| 后端 | Python HTTP Server | 静态服务 + POST 保存 + SSE |
| 状态管理 | Zustand | 轻量响应式 store |
| 画布引擎 | @xyflow/react (React Flow v12) | 专业节点编排 |

### 完整流程（人在回路）

```
1. 首次部署: cd canvas-app && deploy.bat（构建 dist + 复制到 C:\tmp\canvas）
       ↓
2. bg_start 启动画布服务器
       ↓
3. write config.json 写入画布配置
       ↓
4. bash 打开浏览器 (start http://localhost:8081)
       ↓
5. 画布通过 SSE 实时加载 config.json（秒级）
       ↓
6. 用户在画布上编辑（拖拽节点、修改配置、增删连线、键盘 Delete 删除）
       ↓
7. 300ms 防抖后自动 POST /save-config → 状态指示器显示「💾 保存中... → ✅ 已保存」
       ↓
8. 用户告诉大模型"改好了"
       ↓
9. 大模型读取当前状态（GET /get-state 或直接 read config.json）
       ↓
10. 大模型修复后 write config.json
       ↓
11. 服务器文件监控（500ms）检测到变化 → SSE 推送到浏览器
       ↓
12. 画布毫秒级更新 + Toast「🤖 大模型已更新画布」✅
```

### 首次部署

```bash
# 进入画布项目目录
cd D:\work\DriFoxx\app\skills\agent-canvas-designer\canvas-app

# 安装依赖（仅首次）
npm install

# 一键部署：构建 + 复制到 C:\tmp\canvas
deploy.bat
```

### 启动服务器

```xml
<bg_start command="cmd.exe /c \"cd /d C:\tmp\canvas && python server.py\"" />
```

### 写入配置（大模型用）

```xml
<write path="C:/tmp/canvas/config.json">
<content><![CDATA[
{
  "version": "2.0",
  "flow": "custom",
  "meta": {"title": "流程名"},
  "nodes": [...],
  "connections": [...]
}
]]></content>
</write>
```

> 💡 **无需等待轮询**：服务器 500ms 内检测到文件变化，SSE 即时推送到浏览器，画布秒级刷新。

### 读取画布编辑结果（大模型用）

```bash
# 方式一：GET 接口（推荐，直接获取当前状态）
webfetch url="http://localhost:8081/get-state"

# 方式二：直接读文件
read path="C:/tmp/canvas/config.json"
```

### 打开浏览器

```xml
<bash command="start http://localhost:8081" />
```

### 状态指示器

画布顶部工具栏实时显示同步状态：

| 状态 | 含义 |
|------|------|
| ✅ 已就绪 | 画布等待编辑 |
| 💾 保存中... | 正在保存到服务器 |
| ✅ 已保存 | 最新编辑已同步 |
| ❌ 保存失败 | 保存出错 |
| 🤖 LLM 已更新 | 大模型推送了新配置 |
| 👤 已修改 | 用户做了编辑 |

### 停止服务器

```xml
<bg_list />  ← 找到 server.py 的 task_id
<bg_stop task_id="bg_xxxxxxxx" />
```

### 文件位置

```
C:/tmp/canvas/
├── dist/               # Vite 构建产物（前端）
│   ├── index.html
│   └── assets/
├── server.py           # 专用服务器（SSE + 文件监控）
├── config.json         # 当前配置（大模型写入 / 画布自动保存）
└── feedback.json       # 用户导出反馈（兼容旧版）
```

### 开发模式（本地修改代码时）

```bash
cd D:\work\DriFoxx\app\skills\agent-canvas-designer\canvas-app
npm run dev
# → Vite HMR 开发服务器 http://localhost:5173
# → 自动代理 API 到 http://localhost:8081
```

---

## 已知问题与调试

### 画布无法加载

**症状**：`http://localhost:8081` 返回 404

**解决**：确保 `deploy.bat` 已执行，`C:/tmp/canvas/dist/` 存在构建产物。

### 热更新不工作

**症状**：大模型写入 config.json 后画布不刷新

**排查**：
1. 浏览器控制台查看 SSE 连接状态（Network → EventStream）
2. 服务器控制台查看 `🔄 检测到 config.json 变化` 日志
3. 确认 config.json 写入路径为 `C:/tmp/canvas/config.json`

### 重新构建

修改前端代码后重新部署：

```bash
cd D:\work\DriFoxx\app\skills\agent-canvas-designer\canvas-app
npm run build
# 然后复制 dist/ 到 C:\tmp\canvas\dist\
```