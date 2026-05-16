import React, { memo, useCallback, useRef, useState } from 'react';
import { Handle, Position, NodeProps } from '@xyflow/react';
import { NodeType } from '../types/canvas';
import { NODE_ICONS, NODE_COLORS } from '../stores/nodeConfigs';

const ROUND_TYPES = new Set<NodeType>(['start', 'end']);
const BOX_TYPES = new Set<NodeType>(['container', 'iteration']);

interface CustomNodeData {
  label: string;
  nodeType: NodeType;
  config: Record<string, string>;
  collapsed: boolean;
  onToggleCollapse: (id: string) => void;
  onSelect: (id: string) => void;
  onUpdate?: (id: string, patch: object) => void;
}

const CustomNode = memo(({ id, data, selected }: NodeProps) => {
  const { label, nodeType, config = {}, collapsed = false, onToggleCollapse, onSelect, onUpdate } =
    data as unknown as CustomNodeData;

  const color = NODE_COLORS[nodeType] || '#6b7280';
  const isRound = ROUND_TYPES.has(nodeType);
  const isBox = BOX_TYPES.has(nodeType);

  const handleClick = useCallback(
    (e: React.MouseEvent) => { e.stopPropagation(); onSelect?.(id); },
    [id, onSelect]
  );
  const handleDoubleClick = useCallback(
    (e: React.MouseEvent) => { e.stopPropagation(); onSelect?.(id); },
    [id, onSelect]
  );
  const handleToggle = useCallback(
    (e: React.MouseEvent) => { e.stopPropagation(); onToggleCollapse?.(id); },
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

  // 容器/迭代节点
  if (isBox) {
    return (
      <BoxNode
        id={id}
        label={label}
        nodeType={nodeType}
        selected={!!selected}
        color={color}
        config={config}
        onClick={handleClick}
        onDoubleClick={handleDoubleClick}
        onUpdate={onUpdate}
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

/* ===== 容器/迭代节点（支持 resize + 多端口） ===== */
interface BoxNodeProps {
  id: string;
  label: string;
  nodeType: NodeType;
  selected: boolean;
  color: string;
  config: Record<string, string>;
  onClick: (e: React.MouseEvent) => void;
  onDoubleClick: (e: React.MouseEvent) => void;
  onUpdate?: (id: string, patch: object) => void;
}

function BoxNode({ id, label, nodeType, selected, color, config, onClick, onDoubleClick, onUpdate }: BoxNodeProps) {
  const [size, setSize] = useState({
    w: parseInt(config.width as string) || 320,
    h: parseInt(config.height as string) || 160,
  });
  const dragging = useRef(false);
  const start = useRef({ x: 0, y: 0, w: 0, h: 0 });

  // 手动 resize
  const handleResizeMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    dragging.current = true;
    start.current = { x: e.clientX, y: e.clientY, w: size.w, h: size.h };

    const onMove = (ev: MouseEvent) => {
      if (!dragging.current) return;
      const newW = Math.max(200, start.current.w + (ev.clientX - start.current.x));
      const newH = Math.max(100, start.current.h + (ev.clientY - start.current.y));
      setSize({ w: newW, h: newH });
    };

    const onUp = (ev: MouseEvent) => {
      if (!dragging.current) return;
      dragging.current = false;
      const finalW = Math.max(200, start.current.w + (ev.clientX - start.current.x));
      const finalH = Math.max(100, start.current.h + (ev.clientY - start.current.y));
      // 持久化到 config
      onUpdate?.(id, { config: { ...config, width: String(finalW), height: String(finalH) } });
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
    };

    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
  }, [size, config, id, onUpdate]);

  const isLoop = nodeType === 'container';
  const icon = isLoop ? '🔄' : '⟳';
  const tag = isLoop ? '循环' : '迭代';

  return (
    <div
      className={`custom-node box-node ${selected ? 'selected' : ''}`}
      style={{ width: size.w, height: size.h } as React.CSSProperties}
      onClick={onClick}
      onDoubleClick={onDoubleClick}
    >
      {/* 标题栏 */}
      <div className="box-header" style={{ borderBottom: `2px dashed ${color}` }}>
        <span className="box-icon" style={{ background: color }}>{icon}</span>
        <span className="box-label">{label}</span>
        <span className="box-tag">{tag}</span>
        <span className="box-size">{size.w}×{size.h}</span>
      </div>

      {/* 内容区 */}
      <div className="box-body">
        <span>📦 子流程</span>
      </div>

      {/* 右下角 resize 拖拽 */}
      <div
        className="box-resize-handle"
        onMouseDown={handleResizeMouseDown}
        title="拖动调整大小"
      >
        ↘
      </div>

      {/* === 端口 === */}
      {/* 输入（左侧中间） */}
      <Handle type="target" position={Position.Left} id="input" className="handle handle-in" style={{ top: '50%' }} />
      {/* 迭代体输入（左侧下方，仅迭代节点） */}
      {nodeType === 'iteration' && (
        <Handle type="target" position={Position.Left} id="iter-input" className="handle handle-in" style={{ top: '75%' }} />
      )}
      {/* 循环体端口（底部中间） */}
      <Handle type="source" position={Position.Bottom} id="loop-body" className="handle handle-out" style={{ left: '50%' }} />
      {/* 输出（右侧中间） */}
      <Handle type="source" position={Position.Right} id="output" className="handle handle-out" style={{ top: '50%' }} />
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
        {config.tools && <span className="preview-tag tools">⚙ {config.tools.split(',').length}个</span>}
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
  const count = Object.keys(config).filter((k) => k !== 'title' && config[k]).length;
  return <div className="body-preview">{count > 0 && <span className="preview-tag">{count} 个参数</span>}</div>;
}

export default CustomNode;