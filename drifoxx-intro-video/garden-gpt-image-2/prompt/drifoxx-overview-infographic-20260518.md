{
  "type": "便当格 / Bento grid 高密度模块化信息图",
  "goal": "生成一张 DriFoxx AI 编程助手的核心功能介绍 overview 图，像 Apple keynote / Notion dashboard 风格，一图说清 7 大核心能力",
  "canvas": {
    "aspect_ratio": "3:4 portrait",
    "background": "deep dark navy #0E1428",
    "global_corner_radius": "20px",
    "module_gap": "14px"
  },
  "header": {
    "main_title": "DriFoxx",
    "subtitle": "AI 编程助手的七大核心能力｜Hooks · MCP · AutoLoop · 项目管理 · 主题 · 工具 · 技能",
    "title_position": "top-left, large bold sans-serif",
    "title_color": "#F3F6FC",
    "subtitle_color": "#8B98AD"
  },
  "palette": {
    "primary": "#F3F6FC",
    "accent": "#66C6FF",
    "accent_warm": "#C9A85C",
    "accent_green": "#57D29A",
    "module_tints": [
      "dark slate #1A2238",
      "deep indigo #1E2A47",
      "charcoal #2A2A35",
      "dark teal #1A3038",
      "deep purple #221A38"
    ],
    "rule": "module backgrounds rotate among the dark tints; accent blue for Hooks; warm gold for AutoLoop; green for Skills"
  },
  "layout": {
    "style": "asymmetric bento with one hero module",
    "module_count": 9,
    "grid": "irregular: 1 hero module (2x1, top-full-width) + 4 feature modules (1x1 each, row 2) + 4 feature modules (1x1 each, row 3) + 1 footer module (2x1, bottom-full-width)",
    "alignment": "all modules share same corner radius and gap; module edges align to an invisible grid"
  },
  "modules": [
    {
      "id": "M1-hero",
      "size": "large (2x1)",
      "role": "品牌主视觉 / 标语",
      "content": "DriFoxx 品牌大字居中，AI 编程助手 tagline + 狐狸图标/logo，价值主张「不只是聊天，更是你的开发搭档」"
    },
    {
      "id": "M2",
      "size": "small (1x1)",
      "role": "Hooks 系统",
      "content": "标题「⛓️ Hooks」+ 要点列表：7 个事件钩子拦截全链路 / 3 种类型(command/http/python) / Matcher 精确匹配(tool:xxx / 正则) / 支持 BLOCK 决策拦截。底部 tag 标签：「流程守门人」蓝色强调"
    },
    {
      "id": "M3",
      "size": "small (1x1)",
      "role": "MCP 系统",
      "content": "标题「🔌 MCP」+ 要点：Model Context Protocol 协议 / 三种连接(stdio/sse/http) / 自动发现Claude Desktop等配置 / 全局单例+后台事件循环。底部标签：「连接一切工具」"
    },
    {
      "id": "M4",
      "size": "small (1x1)",
      "role": "AutoLoop 系统",
      "content": "标题「🔄 AutoLoop」+ 要点：两阶段设计(规划→执行) / SHARED_TASK_NOTES.md 接力文档 / 强制验证机制 / 安全三道防线(轮数/token/时长)。底部标签：「全自动执行引擎」金色强调"
    },
    {
      "id": "M5",
      "size": "small (1x1)",
      "role": "项目管理系统",
      "content": "标题「📁 项目管理」+ 要点：项目笔记(Markdown编辑) / 关键文档(拖拽添加/文件夹作工作目录) / 项目根目录切换 / SQLite 持久化。底部标签：「让AI记住上下文」"
    },
    {
      "id": "M6",
      "size": "small (1x1)",
      "role": "主题与字体",
      "content": "标题「🎨 主题与字体」+ 四色块横排(深海蓝黑/曜石紫/松林暗绿/石墨铜) + 三档字号(13/14/16px) + 40+颜色token。底部标签：「四套暗色主题」"
    },
    {
      "id": "M7",
      "size": "small (1x1)",
      "role": "工具系统(Tools)",
      "content": "标题「🧰 工具系统」+ 要点列表：文件工具(read/write/edit/patch/grep/glob) / 终端工具(bash/bg任务) / 网络工具(webfetch/websearch) / 任务工具(task_batch/子智能体) / MCP工具(动态注入)。底部标签：「20+内置工具」青色强调"
    },
    {
      "id": "M8",
      "size": "small (1x1)",
      "role": "技能系统(Skills)",
      "content": "标题「📚 技能系统」+ 要点：以 @技能名 触发 / Permission权限控制(allow/deny/ask) / 20+内置技能(TDD/脑暴/diagnose等) / 侧边栏技能面板 / Hook集成。底部标签：「即插即用能力包」绿色强调"
    },
    {
      "id": "M9",
      "size": "medium (2x1)",
      "role": "技术栈",
      "content": "技术标签行：Python · PyQt5 · QFluientWidgets · MiniMax / OpenAI 兼容 · GPT-4o · Claude · asyncio MCP 协议 · SQLite · loguru。最下一行版本号和版权信息"
    }
  ],
  "module_internal_style": {
    "padding": "16-20px inside each module",
    "typography": "sans-serif (Inter / SF Pro Display / 思源黑体); module title in bold 16px; body 12px; tag 10px with rounded background pill",
    "rule": "each module is self-contained with clear hierarchy: icon-top → title → bullet list → tag badge",
    "imagery": "small icons / color swatches; each feature module has a distinctive emoji icon at top-left",
    "list_item_style": "bullet-less, compact, line height 1.5"
  },
  "constraints": {
    "must_keep": [
      "所有模块统一圆角 20px",
      "深色科技风暗色背景，每个模块用不同明度的暗色调区分",
      "每个模块左上方都有对应 emoji 图标（品牌模块居中）",
      "底部模块展示技术栈标签（小字横排）",
      "金色仅用于 AutoLoop 模块，蓝色用于 Hooks，绿色用于 Skills"
    ],
    "avoid": [
      "模块尺寸全部一样（失去 bento 的轻重缓急）",
      "浅色/白色背景（整体保持暗色科技感）",
      "超过5种主色",
      "紫粉渐变 / 圆角彩色边框 / AI 味视觉指纹",
      "模块间距不一致",
      "纯文字模块（每个模块至少要有视觉元素）"
    ]
  }
}