/** 节点类型枚举 */
export type NodeType =
  | 'start'
  | 'end'
  | 'llm'
  | 'agent'
  | 'knowledge'
  | 'ask-table'
  | 'api-request'
  | 'reply'
  | 'condition'
  | 'classifier'
  | 'code'
  | 'container'
  | 'doc-extractor'
  | 'param-extractor';

/** 画布配置（导入导出格式） */
export interface CanvasConfig {
  version: string;
  flow: string;
  meta: {
    title: string;
    description?: string;
  };
  nodes: CanvasNodeData[];
  connections: CanvasConnectionData[];
}

/** 节点数据（配置格式） */
export interface CanvasNodeData {
  id: string;
  type: NodeType;
  label: string;
  x: number;
  y: number;
  config: Record<string, string>;
}

/** 连线数据（配置格式） */
export interface CanvasConnectionData {
  sourceId: string;
  targetId: string;
}

/** 节点配置字段定义 */
export interface NodeConfigField {
  key: string;
  label: string;
  type: 'text' | 'textarea' | 'select';
  /** select 的选项 */
  opts?: string[];
  /** 默认值 */
  default?: string;
  /** 提示文字 */
  hint?: string;
}

/** 节点配置元信息（用于渲染属性面板） */
export interface NodeConfigMeta {
  fields: NodeConfigField[];
}

/** 同步状态 */
export type SyncStatus = 'idle' | 'saving' | 'saved' | 'error' | 'loading';

/** 编辑来源：user=人编辑, llm=大模型编辑 */
export type EditSource = 'user' | 'llm' | 'unknown';
