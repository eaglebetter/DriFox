# Video Outline

> **主题**：待选定（Checkpoint Plan 中对齐）
> **总时长**：约 8 分 30 秒（口播 ~2125 字 ÷ 4 字/秒 ≈ 531s）
> **章节数**：5 章 / 34 步

---

## 1. hooks — Hooks 系统：AI 工作流的守门人（8 steps · ~120s）

**信息池**（chapter agent 按需挂角标 / 副标 / pull-quote / mono cue）：
- 数字：7 个事件钩子（SessionStart / PreUserMessage / PostUserMessage / PreAssistantMessage / PostAssistantMessage / PreToolUse / PostToolUse） —— article §一
- 对比：PreToolUse 是唯一能 BLOCK 操作的事件 —— article §一
- 三种 Hook 类型：command / http / python —— article §一
- Matcher 示例：`tool:webfetch` / `.*帮助.*` —— article §一
- 条件维度：env / file / tool / regex —— article §一
- 技能 Hook vs 全局 Hook：只读 vs 可编辑 —— article §一
- 配置路径：`.drifox/hooks/hooks.json` —— article §一
- 真实案例：using-superpowers 技能的 SessionStart hook —— article §一

**开发计划**：

- step 1 (~12s) — 开场钩子："AI 偷偷调了一个你不希望的工具" + 7 事件全链图
- step 2 (~12s) — 7 个事件名称依次亮起，从 SessionStart 到 PostToolUse
- step 3 (~16s) — PreToolUse 高亮 + BLOCK 决策路径图（exit 2 → 拦截）
- step 4 (~16s) — 三种 Hook 类型对比：command / http / python 各一行演示
- step 5 (~14s) — Matcher 精度控制：tool:webfetch 示例 + 正则示例
- step 6 (~14s) — 条件系统四维度：env / file / tool / regex
- step 7 (~18s) — 技能 Hook vs 全局 Hook：只读标记 + 同组展示
- step 8 (~18s) — 配置界面演示 + 热重载 + 输出注入上下文

口播节选：
> 你的 AI 助手在后台偷偷调了一个你不希望它用的工具，怎么办？DriFoxx 的 Hooks 系统就是干这个的。

---

## 2. mcp — MCP 系统：让 AI 连接一切工具（7 steps · ~118s）

**信息池**：
- 全称：Model Context Protocol —— article §二
- 三种连接方式：stdio / sse / http —— article §二
- 工具前缀：`mcp__{server}__{tool}` —— article §二
- MCPClientManager 全局单例 + 后台 asyncio Task —— article §二
- 自动发现：Claude Desktop / Cursor / Windsurf 配置 —— article §二
- 工具调用路径：LLM → ToolExecutor → MCPClientManager → ClientSession → 返回 —— article §二
- 聊天中 MCP 工具显示：🌐 图标 + 青色标题 —— article §二
- 配置五分钟搞定 —— article §二

**开发计划**：

- step 1 (~14s) — 开场钩子："AI 突然能用浏览器了" + MCP 名称展开
- step 2 (~16s) — 三种连接方式图示：stdio 本地进程 / sse 远程 / http 流式
- step 3 (~16s) — 连接建立动画：配置 → 连接 → 自动发现工具列表
- step 4 (~18s) — 工具前缀机制：Playwright server 的工具如何注入 AI schema
- step 5 (~16s) — 自动发现：从 Claude Desktop / Cursor 配置导入
- step 6 (~20s) — 调用全链路：AI → mcp__Playwright__browser_click → 服务器 → 结果
- step 7 (~18s) — 配置界面 + 连接状态 + 五分钟搞定

口播节选：
> 你的 AI 助手突然能用浏览器了、能操作文件系统了、能查数据库了。这不是魔法，这是 MCP。

---

## 3. autoloop — AutoLoop 系统：全自动任务执行引擎（8 steps · ~118s）

**信息池**：
- 两阶段设计：Planning → Executing —— article §三
- SHARED_TASK_NOTES.md 接力文档 —— article §三
- 规划阶段只允许 scan/glob/grep/list/read/write —— article §三
- 步骤格式：`- [ ] [步骤 N] 描述 | 文件 | 验证方式` —— article §三
- 执行阶段一轮一步 + 强制验证 —— article §三
- 连续验证失败 3 次自动跳过 —— article §三
- 安全三道防线：50 轮 / 50 万 token / 2 小时 —— article §三
- DONE 信号连续 3 次确认 —— article §三
- 日志目录：`.autoloop/logs/round_XXX.md` —— article §三

**开发计划**：

- step 1 (~14s) — 开场钩子："给 AI 一个任务，它自己规划自己执行" + 两阶段总览
- step 2 (~16s) — 规划阶段：只拆步骤不写代码 + PLANNING_COMPLETE 信号
- step 3 (~14s) — SHARED_TASK_NOTES.md 接力文档结构展示
- step 4 (~16s) — 执行阶段：一轮一步 + 验证 + 勾选 [x]
- step 5 (~14s) — 保护区：任务概述和执行计划禁止修改
- step 6 (~14s) — 安全三道防线：轮数 / token / 时长
- step 7 (~16s) — 配置卡 + 运行卡彩虹边框 + 进度实时显示
- step 8 (~14s) — 最大价值：强制验证 + 审计日志

口播节选：
> 给 AI 一个任务，它自己规划、自己执行、自己验证，循环往复直到完成。这就是 AutoLoop。

---

## 4. project-mgmt — 项目管理系统：让 AI 记住你的项目上下文（6 steps · ~88s）

**信息池**：
- 三个子系统：项目笔记 / 关键文档 / 项目根目录 —— article §四
- edit_project_note 精确字符串替换（非覆盖） —— article §四
- 关键文档支持拖拽添加 + 文件夹作为工作目录 —— article §四
- 项目根目录决定相对路径基准 / 搜索范围 / AutoLoop 工作目录 —— article §四
- 记忆卡片三标签页：条目记忆 / 项目笔记 / 关键文档 —— article §四
- SQLite 持久化 —— article §四
- stage_files 自动关联关键文档 —— article §四

**开发计划**：

- step 1 (~14s) — 开场钩子："AI 最怕的不是算力不够，是不知道你在做什么"
- step 2 (~16s) — 项目笔记：Markdown 编辑器 + AI 自动读写 + 精确替换
- step 3 (~16s) — 关键文档：拖拽添加 + 文件夹变工作目录
- step 4 (~14s) — 项目根目录：切换后 AI 上下文跟着变
- step 5 (~14s) — 记忆卡片三标签页 + SQLite 持久化
- step 6 (~14s) — stage_files 自动关联 + 工具操作流程

口播节选：
> AI 最怕的不是算力不够，是不知道你在做什么项目。DriFoxx 的项目管理系统解决的就是这个。

---

## 5. theme-font — 主题与字体：让界面属于你（5 steps · ~58s）

**信息池**：
- 四套主题：深海蓝黑 / 曜石紫 / 松林暗绿 / 石墨铜 —— article §五
- 每套主题 40+ 颜色 token —— article §五
- 字体三档：小(13px) / 中(14px) / 大(16px) + 间距联动 —— article §五
- 主题切换实时生效 —— article §五
- 全局字体可选 —— article §五

**开发计划**：

- step 1 (~12s) — 开场钩子："四套暗色主题，不是简单换个底色"
- step 2 (~14s) — 四套主题色卡对比：蓝黑 / 紫 / 绿 / 铜
- step 3 (~12s) — 40+ token 覆盖全链路示意
- step 4 (~12s) — 字体三档 + 间距联动
- step 5 (~8s) — 实时切换 + 全局字体

口播节选：
> DriFoxx 四套暗色主题，从窗口背景到输入框边框都有完整的色彩体系，不是简单的换个底色。

---

## 素材清单

### 1. hooks
- ✓ Hooks 配置界面截图（可从应用截图）
- ✓ 7 事件全链路图（需绘制）
- ✓ BLOCK 决策路径图（需绘制）
- ⚠️ using-superpowers SessionStart hook 实例（可从代码提取）

### 2. mcp
- ✓ MCP 连接配置界面截图（可从应用截图）
- ✓ 三种连接方式图示（需绘制）
- ✓ 工具调用全链路图（需绘制）
- ⚠️ Claude Desktop / Cursor 自动发现截图（可从应用截图）

### 3. autoloop
- ✓ AutoLoop 配置卡 + 运行卡截图（可从应用截图）
- ✓ 两阶段流程图（需绘制）
- ✓ SHARED_TASK_NOTES.md 文档结构图（需绘制）
- ⚠️ 彩虹边框动画视频片段（需录屏）

### 4. project-mgmt
- ✓ 记忆卡片三标签页截图（可从应用截图）
- ✓ 拖拽添加关键文档截图（可从应用截图）
- ⚠️ 项目切换流程截图（可从应用截图）

### 5. theme-font
- ✓ 四套主题色卡（可从 design_tokens.py 提取）
- ⚠️ 主题切换实时效果视频片段（需录屏）
