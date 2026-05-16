import React, { memo, useState, useCallback } from 'react';
import { Handle, Position, NodeProps, NodeResizer } from '@xyflow/react';
import { NodeType } from '../types/canvas';
import { NODE_ICONS, NODE_COLORS } from '../stores/nodeConfigs';

/** 圆形节点类型（start/end） */
const ROUND_TYPES = new Set<NodeType>(['start', 'end']);

interface CustomNodeData {
  label: string;
  nodeType: NodeType;
  config: Record<string, string>;
  /** 是否折叠（隐藏 body） */
  collapsed: boolean;
  onToggleCollapse: (id: string) => void;
  onSelect: (id: string) => void;
}

const CustomNode = memo(({ id, data, selected }: NodeProps) => {
  const {
    label,
    nodeType,
    config = {},
    collapsed = false,
    onToggleCollapse,
    onSelect,
  } = data as unknown as CustomNodeData;

  const color = NODE_COLORS[nodeType] || '#6b7280';
  const isRound = ROUND_TYPES.has(nodeType);

  const handleDoubleClick = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      onSelect?.(id);
    },
    [id, onSelect]
  );

  const handleToggle = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      onToggleCollapse?.(id);
    },
    [id, onToggleCollapse]
  );

  // 圆形节点（start/end）
  if (isRound) {
    return (
      <div
        className={`custom-node round-node ${selected ? 'selected' : ''}`}
        style={{ '--node-color': color } as React.CSSProperties}
        title={label}
      >
        <Handle
          type="target"
          position={Position.Left}
          className="handle handle-in"
        />
        <div className="round-inner" style={{ background: color }}>
          <span>{NODE_ICONS[nodeType]}</span>
        </div>
        <Handle
          type="source"
          position={Position.Right}
          className="handle handle-out"
        />
      </div>
    );
  }

  // 普通节点：双击打开详情面板
  return (
    <div
      className={`custom-node dif-card ${selected ? 'selected' : ''}`}
      style={
        {
          '--node-color': color,
          '--node-color-light': color + '22',
        } as React.CSSProperties
      }
      onDoubleClick={handleDoubleClick}
    >
      {/* 顶部状态条 */}
      <div className="dif-card-topbar" style={{ background: color }} />

      {/* 头部 */}
      <div className="dif-card-header">
        <div className="dif-card-icon" style={{ background: color }}>
          {NODE_ICONS[nodeType]}
        </div>
        <div className="dif-card-title">
          <span className="dif-card-title-main">{label}</span>
          <span className="dif-card-title-sub">{nodeType}</span>
        </div>
        {/* 折叠按钮（非 container 节点显示） */}
        {nodeType !== 'container' && (
          <button
            className="dif-card-toggle"
            onClick={handleToggle}
            title={collapsed ? '展开' : '折叠'}
          >
            {collapsed ? '▼' : '▲'}
          </button>
        )}
      </div>

      {/* 折叠区域：节点预览内容 */}
      {!collapsed && (
        <div className="dif-card-body">
          <NodeBodyPreview nodeType={nodeType} config={config} />
        </div>
      )}

      {/* 输入端口（左侧中间） */}
      <Handle
        type="target"
        position={Position.Left}
        className="handle handle-in"
        style={{ top: '50%' }}
      />

      {/* 输出端口（右侧中间） */}
      <Handle
        type="source"
        position={Position.Right}
        className="handle handle-out"
        style={{ top: '50%' }}
      />

      {/* container 特殊样式 */}
      {nodeType === 'container' && (
        <div className="dif-card-container-hint">📦 子画布容器 — 拖入节点</div>
      )}
    </div>
  );
});

CustomNode.displayName = 'CustomNode';

/** 节点 body 预览内容（折叠时显示关键信息） */
function NodeBodyPreview({
  nodeType,
  config,
}: {
  nodeType: NodeType;
  config: Record<string, string>;
}) {
  if (nodeType === 'llm' || nodeType === 'agent') {
    const model = config.model;
    const hasPrompt = Boolean(config.system_prompt);
    return (
      <div className="body-preview">
        {model && <span className="preview-tag">{model.split('/').pop()}</span>}
        {hasPrompt && <span className="preview-tag prompt">✓ 提示词</span>}
        {nodeType === 'agent' && config.tools && (
          <span className="preview-tag tools">⚙ 工具</span>
        )}
      </div>
    );
  }
  if (nodeType === 'knowledge') {
    return (
      <div className="body-preview">
        {config.kb_type && (
          <span className="preview-tag">{config.kb_type}</span>
        )}
        {config.top_k && (
          <span className="preview-tag">k={config.top_k}</span>
        )}
      </div>
    );
  }
  if (nodeType === 'code') {
    return (
      <div className="body-preview">
        <span className="preview-tag code-lang">🐍 Python</span>
        {config.code && (
          <span className="preview-tag lines">
            {config.code.split('\n').length} 行
          </span>
        )}
      </div>
    );
  }
  if (nodeType === 'container') {
    return <div className="body-preview" />;
  }
  // 其他节点类型显示配置数量
  const count = Object.keys(config).filter(
    (k) => k !== 'title' && config[k]
  ).length;
  return (
    <div className="body-preview">
      {count > 0 && (
        <span className="preview-tag">{count} 个参数</span>
      )}
    </div>
  );
}

export default CustomNode;