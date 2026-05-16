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

## 热更新画布流程

使用专用服务器启动画布，实现热更新开发流程。

### 完整流程

```
1. bg_start 启动画布服务器 (C:/tmp/canvas)   ← server.py
       ↓
2. write config.json 写入画布配置
       ↓
3. bash 打开浏览器 (start http://localhost:8081/agent_canvas.html)
       ↓
4. 画布自动加载 config.json（有则直接显示，无则兜底默认流程）
       ↓
5. 用户在画布上编辑（拖拽节点、修改配置、增删连线）
       ↓
6. 1.5 秒防抖后画布自动 POST 保存到 feedback.json，Toast 提示「💾 已自动保存」
       ↓
7. 用户告诉大模型"改好了"
       ↓
8. 大模型 read feedback.json 获取修改内容
       ↓
9. 大模型修复后 write config.json
       ↓
10. 画布每3秒轮询检测到 config.json 变化 → 自动刷新 ✅
```

### 启动服务器

```xml
<bg_start command="cmd.exe /c \"cd /d C:\tmp\canvas && python server.py\"" />
```

> ⚠️ cwd 参数在 cmd.exe 中不生效，必须在命令里 `cd /d C:\tmp\canvas`

### 写入配置（大模型用）

大模型修改设计后写入 `config.json`，画布 3 秒后自动刷新：

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

### 读取画布编辑结果（大模型用）

用户编辑画布后自动保存到 `feedback.json`，大模型通过 GET 接口或直接读文件获取：

```bash
# 方式一：GET 接口（推荐）
webfetch url="http://localhost:8081/get-state"

# 方式二：直接读文件
read path="C:/tmp/canvas/feedback.json"
```

### 打开浏览器

```xml
<bash command="start http://localhost:8081/agent_canvas.html" />
```

### 读取用户修改

用户点击「📤 导出反馈」后，画布自动 POST 到 `/save-feedback`，直接保存到 `C:/tmp/canvas/feedback.json`。

**大模型读取反馈的流程**：
```bash
# 每次画布编辑后自动保存，用户只需说"改好了"
# 大模型直接读取 feedback.json 获取最新编辑结果
read path="C:/tmp/canvas/feedback.json"

# 处理完成后删除（可选，防止重复读取）
bash command="del \"C:\tmp\canvas\feedback.json\""
```

> 💡 不再需要手动点导出！编辑完成后 1.5 秒自动保存，大模型可直接读取

### 停止服务器

先查 bg_list 找到任务 ID，再 bg_stop：

```xml
<bg_list />  ← 找到 server.py 的 task_id
<bg_stop task_id="bg_xxxxxxxx" />
```

也可用 `netstat -ano | findstr :8081` 找到 PID 后 `taskkill /F /PID xxx`

### 文件位置

```
C:/tmp/canvas/
├── server.py           # 专用服务器（支持保存）
├── agent_canvas.html   # 画布主文件
├── config.json         # 当前配置（大模型写入）
└── feedback.json       # 用户导出（大模型读取）
```

### server.py 源码

```python
#!/usr/bin/env python3
"""
画布专用服务器 — 支持热重载
- GET   /*          服务静态文件
- POST  /save-feedback  保存用户反馈到 feedback.json
- POST  /save-config    保存配置到 config.json（供大模型写回）
"""

import http.server
import socketserver
import json
import os

PORT = 8081
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class CanvasHandler(http.server.SimpleHTTPRequestHandler):

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip('/')
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)

        if path == '/save-feedback':
            self._save_file('feedback.json', body)
        elif path == '/save-config':
            self._save_file('config.json', body)
        else:
            self.send_response(404)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'not found'}).encode())

    def _save_file(self, filename, data):
        """保存文件并返回 JSON 响应"""
        try:
            json.loads(data)  # 验证 JSON 合法性
            with open(os.path.join(BASE_DIR, filename), 'wb') as f:
                f.write(data)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'success': True, 'size': len(data)}).encode())
            print(f'✅ 已保存 {filename} ({len(data)} bytes)')
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())

    def do_GET(self):
        if self.path == '' or self.path.endswith('/'):
            self.send_response(302)
            self.send_header('Location', '/agent_canvas.html')
            self.end_headers()
            return
        return super().do_GET()

    def log_message(self, format, *args):
        print(f'[画布] {self.client_address[0]} - {format % args}')


if __name__ == '__main__':
    os.chdir(BASE_DIR)
    print(f'🚀 画布服务器: http://localhost:{PORT}/agent_canvas.html')
    print(f'   POST /save-feedback → feedback.json')
    print(f'   POST /save-config   → config.json')
    with socketserver.TCPServer(('0.0.0.0', PORT), CanvasHandler) as httpd:
        httpd.serve_forever()
```

> ⚠️ 必须使用 `server.py` 而不是 `python -m http.server`，后者不支持 POST 保存文件

### 画布交互

- **📂 加载配置** - 手动重新加载 config.json
- **📤 导出反馈** - POST 到服务器保存到 `C:/tmp/canvas/feedback.json`，底部弹出 Toast 通知
- **自动保存** - 画布每次编辑后 1.5 秒自动 POST 到 `/save-config`，无需手动导出，大模型可直接读取
- **自动加载** - 打开画布直接加载 config.json（不存在则显示默认流程）
- **热更新** - 每 3 秒自动检查 config.json 变化，有更新自动刷新

### 注意事项

1. Python 在 Windows 上 `C:/tmp` 解析为 C:\tmp
2. 画布每 3 秒自动检查 config.json 更新
3. 每次修改配置后，用户刷新页面即可看到新配置
4. 导出的是完整的画布 JSON，包含节点位置和连线信息

---

## 已知问题与调试

### 连线无法显示

**症状**：从 config.json 加载后，节点显示正常但连线缺失。

**原因**：`loadConfigData` 函数中 `createNode` 返回的是节点 ID 字符串，但后续代码错误地把它当成节点对象访问 `.eps` 属性。

**修复**：通过节点 ID 在 `nodes` 数组中查找真正的节点对象：
```javascript
var sourceId = nodeIdMap[conn.sourceId];
var targetNode = nodes.find(function(n) { return n.id === sourceId; });
```

**验证**：刷新画布后，检查浏览器控制台是否有 "连接失败" 日志。

### 浏览器控制台调试

画布运行时会输出以下日志：
- `✅ 已加载配置: xxx` — 配置加载成功
- `🔄 检测到配置更新，重新加载...` — 热更新触发
- `连接失败: {sourceId, targetId}` — 连线创建失败

**调试方法**：按 `F12` 打开开发者工具 → Console 面板

### 画布与技能目录同步

画布主文件位于两个位置：
- `C:/tmp/canvas/agent_canvas.html` — 开发调试用
- `DriFox/app/skills/agent-canvas-designer/assets/agent_canvas.html` — 技能发布用

修改画布后需要同步到技能目录：
```bash
copy /Y "C:\tmp\canvas\agent_canvas.html" "D:\work\DriFox\app\skills\agent-canvas-designer\assets\agent_canvas.html"
```