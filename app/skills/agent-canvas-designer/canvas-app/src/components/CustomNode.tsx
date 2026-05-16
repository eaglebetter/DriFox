import React, { memo, useCallback } from 'react';
import { Handle, Position, NodeProps } from '@xyflow/react';
import { NodeType } from '../types/canvas';
import { NODE_ICONS, NODE_COLORS } from '../stores/nodeConfigs';

const ROUND_TYPES = new Set<NodeType>(['start', 'end']);
const CONTAINER_TYPES = new Set<NodeType>(['container', 'iteration']);

interface CustomNodeData {
  label: string;
  nodeType: NodeType;
  config: Record<string, string>;
  collapsed: boolean;
  onToggleCollapse: (id: string) => void;
  onSelect: (id: string) => void;
}

const CustomNode = memo(({ id, data, selected }: NodeProps) => {
  const { label, nodeType, config = {}, collapsed = false, onToggleCollapse, onSelect } =
    data as unknown as CustomNodeData;

  const color = NODE_COLORS[nodeType] || '#6b7280';
  const isRound = ROUND_TYPES.has(nodeType);
  const isContainer = CONTAINER_TYPES.has(nodeType);

  // 整节点可点击
  const handleClick = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      onSelect?.(id);
    },
    [id, onSelect]
  );

  // 双击打开详情
  const handleDoubleClick = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      onSelect?.(id);
    },
    [id, onSelect]
  );

  // 折叠
  const handleToggle = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      onToggleCollapse?.(id);
    },
    [id, onToggleCollapse]
  );

  // 圆形节点
  if (isRound) {
    return (
      <div
        className={`custom-node round-node ${selected ? 'selected' : ''}`}
        style={{ '--node-color': color } as React.CSSProperties}
        onClick={handleClick}
        title={label}
      >
        <Handle type="target" position={Position.Left} className="handle handle-in" />
        <div className="round-inner" style={{ background: color }}>
          {NODE_ICONS[nodeType]}
        </div>
        <Handle type="source" position={Position.Right} className="handle handle-out" />
      </div>
    );
  }

  // 容器节点
  if (isContainer) {
    return (
      <LoopContainerNode
        id={id}
        label={label}
        selected={selected}
        color={color}
        onClick={handleClick}
        onDoubleClick={handleDoubleClick}
      />
    );
  }

  // 普通节点卡片
  return (
    <div
      className={`custom-node dif-card ${selected ? 'selected' : ''} ${collapsed ? 'collapsed' : ''}`}
      style={{ '--node-color': color } as React.CSSProperties}
      onClick={handleClick}
      onDoubleClick={handleDoubleClick}
    >
      <div className="dif-card-topbar" style={{ background: color }} />
      <div className="dif-card-header">
        <div className="dif-card-icon" style={{ background: color }}>
          {NODE_ICONS[nodeType]}
        </div>
        <div className="dif-card-title">
          <span className="dif-card-title-main">{label}</span>
          <span className="dif-card-title-sub">{nodeType}</span>
        </div>
        <button className="dif-card-toggle" onClick={handleToggle} title={collapsed ? '展开' : '折叠'}>
          {collapsed ? '▼' : '▲'}
        </button>
      </div>

      {!collapsed && (
        <div className="dif-card-body">
          <NodeBodyPreview nodeType={nodeType} config={config} />
        </div>
      )}

      <Handle type="target" position={Position.Left} className="handle handle-in" />
      <Handle type="source" position={Position.Right} className="handle handle-out" />
    </div>
  );
});

CustomNode.displayName = 'CustomNode';

/* ===== 循环/迭代容器节点 ===== */
interface LoopNodeProps {
  id: string;
  label: string;
  selected: boolean;
  color: string;
  onClick: (e: React.MouseEvent) => void;
  onDoubleClick: (e: React.MouseEvent) => void;
}

function LoopContainerNode({ id, label, selected, color, onClick, onDoubleClick }: LoopNodeProps) {
  // 容器固定尺寸，不做 runtime resize（避免与 ReactFlow 拖拽冲突）
  // 用户可通过右侧面板配置 width/height

  const isLoop = label.includes('循环');
  const icon = isLoop ? '🔄' : '⟳';
  const tag = isLoop ? '循环' : '迭代';

  return (
    <div
      className={`custom-node container-node ${selected ? 'selected' : ''}`}
      onClick={onClick}
      onDoubleClick={onDoubleClick}
    >
      {/* 顶部标题栏 */}
      <div className="container-header">
        <span className="container-icon" style={{ background: color }}>{icon}</span>
        <span className="container-label">{label}</span>
        <span className="container-type-tag">{tag}</span>
      </div>

      {/* 内容区 */}
      <div className="container-body">
        <span>📦 子流程 — 拖入节点</span>
      </div>

      <Handle type="target" position={Position.Left} className="handle handle-in" style={{ top: 40 }} />
      <Handle type="source" position={Position.Right} className="handle handle-out" style={{ top: 40 }} />
    </div>
  );
}

/* ===== 节点预览 ===== */
function NodeBodyPreview({ nodeType, config }: { nodeType: NodeType; config: Record<string, string> }) {
  if (nodeType === 'llm' || nodeType === 'agent') {
    return (
      <div className="body-preview">
        {config.model && <span className="preview-tag">{config.model.split('/').pop()}</span>}
        {config.system_prompt && <span className="preview-tag prompt">✓ 提示词</span>}
        {config.user_prompt && <span className="preview-tag prompt">✓ 用户词</span>}
        {config.tools && <span className="preview-tag tools">⚙ {config.tools.split(',').length}个工具</span>}
      </div>
    );
  }
  if (nodeType === 'knowledge') {
    return (
      <div className="body-preview">
        {config.kb_type && <span className="preview-tag">{config.kb_type}</span>}
        {config.top_k && <span className="preview-tag">k={config.top_k}</span>}
      </div>
    );
  }
  if (nodeType === 'code') {
    const lines = (config.code || '').split('\n').length;
    return (
      <div className="body-preview">
        <span className="preview-tag code-lang">🐍 Python</span>
        {lines > 1 && <span className="preview-tag lines">{lines} 行</span>}
      </div>
    );
  }
  if (nodeType === 'container') return <div className="body-preview" />;
  const count = Object.keys(config).filter((k) => k !== 'title' && config[k]).length;
  return (
    <div className="body-preview">
      {count > 0 && <span className="preview-tag">{count} 个参数</span>}
    </div>
  );
}

export default CustomNode;