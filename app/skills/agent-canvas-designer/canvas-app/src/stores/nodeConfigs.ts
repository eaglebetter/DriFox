import { NodeType, NodeConfigMeta } from '../types/canvas';

/**
 * 所有节点类型的配置字段定义
 * TODO: 后续支持从外部配置动态注册
 */
const NODE_CONFIGS: Record<NodeType, NodeConfigMeta> = {
  start: {
    fields: [
      {
        key: 'title', label: '节点名称', type: 'text', default: '开始',
      },
      {
        key: 'params', label: '输入参数', type: 'textarea',
        default: 'sys.query = 用户输入的问题描述\nsys.files = 用户上传的文件',
        hint: '根节点，sys.query 为用户原始输入',
      },
    ],
  },
  end: {
    fields: [
      {
        key: 'title', label: '节点名称', type: 'text', default: '结束',
      },
      {
        key: 'outputs', label: '输出参数', type: 'textarea',
        default: 'result = 最终输出结果',
        hint: '流程终点',
      },
    ],
  },
  reply: {
    fields: [
      {
        key: 'title', label: '节点名称', type: 'text', default: '回复',
      },
      {
        key: 'reply_type', label: '回复类型', type: 'select',
        opts: ['直接回复', '使用模板'], default: '直接回复',
      },
      {
        key: 'content', label: '回复内容', type: 'textarea',
        default: '根据分析结果，回复用户以下内容：\n- 问题定位已完成\n- 已生成对应模型规则\n- 请确认是否需要进一步调整',
        hint: '支持变量引用，如 {{sys.query}}',
      },
    ],
  },
  llm: {
    fields: [
      {
        key: 'title', label: '节点名称', type: 'text', default: '大模型',
      },
      {
        key: 'model', label: '模型', type: 'text', default: 'gpt-4 / qwen-plus / deepseek-chat',
      },
      {
        key: 'system_prompt', label: '系统提示词', type: 'textarea',
        default: '你是一个工业设备故障诊断专家...',
        hint: '系统级提示词，定义大模型行为',
      },
      {
        key: 'user_prompt', label: '用户提示词', type: 'textarea',
        default: '请分析以下问题：\n{{sys.query}}',
        hint: '用户级提示词，可使用 {{node_id.output}} 引用上游输出',
      },
    ],
  },
  agent: {
    fields: [
      {
        key: 'title', label: '节点名称', type: 'text', default: 'Agent',
      },
      {
        key: 'model', label: '模型', type: 'text', default: 'gpt-4',
      },
      {
        key: 'system_prompt', label: 'Agent 系统提示词', type: 'textarea',
        default: '你是一个 Agent。使用工具进行分析。',
        hint: 'Agent 的系统提示词，定义行为和多轮工具调用策略',
      },
      {
        key: 'user_prompt', label: 'Agent 用户提示词', type: 'textarea',
        default: '请处理：{{sys.query}}',
      },
      {
        key: 'tools', label: '绑定的工具列表', type: 'textarea',
        default: '["工具1","工具2"]',
        hint: 'Agent 可调用的工具，用工具名称列表',
      },
      {
        key: 'max_iterations', label: '最大迭代次数', type: 'text', default: '5',
      },
      {
        key: 'output_schema', label: '输出格式要求', type: 'textarea',
        default: '{}',
        hint: '期望的JSON输出格式',
      },
    ],
  },
  knowledge: {
    fields: [
      {
        key: 'title', label: '节点名称', type: 'text', default: '知识检索',
      },
      {
        key: 'kb_type', label: '知识库类型', type: 'select',
        opts: ['设备运行规程库', '历史故障案例库', '设备说明书库', '定值手册库', '模型模板库', '振动标准库（ISO 10816）', '热力学参数库'],
        default: '设备运行规程库',
      },
      {
        key: 'query', label: '检索语句', type: 'textarea',
        default: '{{sys.query}}',
        hint: '知识库检索关键词',
      },
      {
        key: 'top_k', label: '返回数量', type: 'text', default: '5',
      },
      {
        key: 'threshold', label: '相似度阈值', type: 'text', default: '0.7',
      },
    ],
  },
  'ask-table': {
    fields: [
      {
        key: 'title', label: '节点名称', type: 'text', default: '智能问表',
      },
      {
        key: 'table', label: '关联数据库表', type: 'text', default: 'equipment_alarm_history',
      },
      {
        key: 'db_type', label: '数据库类型', type: 'text', default: 'MySQL / PostgreSQL',
      },
      {
        key: 'question', label: '自然语言问题', type: 'textarea',
        default: '查询数据',
        hint: '自然语言描述，自动转SQL查询',
      },
    ],
  },
  'api-request': {
    fields: [
      {
        key: 'title', label: '节点名称', type: 'text', default: '接口请求',
      },
      {
        key: 'method', label: '请求方法', type: 'select',
        opts: ['GET', 'POST', 'PUT', 'DELETE'], default: 'POST',
      },
      {
        key: 'url', label: 'API 地址', type: 'text', default: 'https://api.example.com/v1/',
      },
      {
        key: 'headers', label: '请求头', type: 'textarea',
        default: '{"Content-Type":"application/json"}',
      },
      {
        key: 'body', label: '请求体', type: 'textarea', default: '{}',
      },
    ],
  },
  condition: {
    fields: [
      {
        key: 'title', label: '节点名称', type: 'text', default: '条件分支',
      },
      {
        key: 'input_var', label: '判断变量', type: 'text', default: '{{node_4.output.severity}}',
      },
      {
        key: 'branches', label: '分支条件定义', type: 'textarea',
        default: '分支1: 条件A\n分支2: 条件B\n分支3: default',
        hint: '每个分支一行，格式：分支名 → 条件表达式',
      },
    ],
  },
  classifier: {
    fields: [
      {
        key: 'title', label: '节点名称', type: 'text', default: '问题分类器',
      },
      {
        key: 'input_source', label: '输入来源', type: 'text', default: '{{sys.query}}',
      },
      {
        key: 'categories', label: '问题分类及描述', type: 'textarea',
        default: '分类1 → 描述\n分类2 → 描述\n其他 → 兜底分类',
        hint: '每行：分类名 → 分类描述，输出为分类名',
      },
      {
        key: 'model', label: '模型', type: 'text', default: 'gpt-4o-mini',
      },
    ],
  },
  code: {
    fields: [
      {
        key: 'title', label: '节点名称', type: 'text', default: '代码执行',
      },
      {
        key: 'inputs', label: '输入变量', type: 'textarea',
        default: 'param1: str\nparam2: int = 0',
        hint: '格式：变量名: 类型 [= 默认值]',
      },
      {
        key: 'outputs', label: '输出变量', type: 'textarea',
        default: 'result: str',
      },
      {
        key: 'code', label: '代码（Python main函数）', type: 'textarea',
        default: 'def main(param1, param2=0):\n    # 你的代码\n    return {"result": "ok"}',
        hint: 'Python语法，main函数',
      },
    ],
  },
  container: {
    fields: [
      {
        key: 'title', label: '容器名称', type: 'text', default: '循环',
      },
      {
        key: 'container_type', label: '容器类型', type: 'select',
        opts: ['循环', '迭代', '对话'], default: '循环',
      },
      {
        key: 'loop_var', label: '循环变量/列表', type: 'text', default: '{{node_5.output}}',
      },
      {
        key: 'loop_desc', label: '循环说明', type: 'textarea',
        default: '对每个元素执行的逻辑',
        hint: '循环：列表每个元素\n迭代：反复优化至收敛',
      },
    ],
  },
  'doc-extractor': {
    fields: [
      {
        key: 'title', label: '节点名称', type: 'text', default: '文档提取器',
      },
      {
        key: 'source', label: '文件来源', type: 'select',
        opts: ['sys.files（用户上传）', '指定文件路径', '上游节点输出'],
        default: 'sys.files（用户上传）',
      },
      {
        key: 'file_path', label: '指定文件路径', type: 'text', default: '',
        hint: '若来源为指定文件路径，填写具体路径',
      },
      {
        key: 'extract_mode', label: '提取模式', type: 'select',
        opts: ['全文提取', '按段落提取', '表格提取'],
        default: '全文提取',
      },
    ],
  },
  'param-extractor': {
    fields: [
      {
        key: 'title', label: '节点名称', type: 'text', default: '参数提取器',
      },
      {
        key: 'model', label: '模型', type: 'text', default: 'gpt-4 / qwen-plus',
      },
      {
        key: 'input_text', label: '输入文本', type: 'text', default: '{{node_previous.output}}',
      },
      {
        key: 'param_schema', label: '目标参数结构', type: 'textarea',
        default: '{\n  "field1": "说明",\n  "field2": "说明"\n}',
        hint: '期望的JSON结构和各字段说明',
      },
      {
        key: 'system_prompt', label: '系统提示词', type: 'textarea',
        default: '你是一个结构化信息提取专家。只输出JSON。',
        hint: '提取器的提示词',
      },
    ],
  },
};

export default NODE_CONFIGS;

/** 节点图标映射 */
export const NODE_ICONS: Record<NodeType, string> = {
  start: '▶',
  end: '■',
  llm: '🤖',
  agent: '🦾',
  knowledge: '📚',
  'ask-table': '📊',
  'api-request': '🌐',
  reply: '✉',
  condition: '↗',
  classifier: '🏷',
  code: '⟨⟩',
  container: '⊞',
  'doc-extractor': '📄',
  'param-extractor': '📋',
};

/** 节点颜色映射 */
export const NODE_COLORS: Record<NodeType, string> = {
  start: '#22c55e',
  end: '#ef4444',
  llm: '#8b5cf6',
  agent: '#6366f1',
  knowledge: '#06b6d4',
  'ask-table': '#0ea5e9',
  'api-request': '#f59e0b',
  reply: '#22c55e',
  condition: '#ef4444',
  classifier: '#ec4899',
  code: '#334155',
  container: '#14b8a6',
  'doc-extractor': '#6b7280',
  'param-extractor': '#a855f7',
};
