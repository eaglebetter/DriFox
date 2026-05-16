import React, { memo } from 'react';
import { Handle, Position, NodeProps } from '@xyflow/react';
import { NodeType } from '../types/canvas';
import { NODE_ICONS, NODE_COLORS } from '../stores/nodeConfigs';

interface CustomNodeData {
  label: string;
  nodeType: NodeType;
  onSelect: (id: string) => void;
  onDelete: (id: string) => void;
}

const START_END_TYPES: NodeType[] = ['start', 'end'];

const CustomNode = memo(({ id, data, selected }: NodeProps) => {
  const { label, nodeType } = data as unknown as CustomNodeData;
  const icon = NODE_ICONS[nodeType] || '●';
  const color = NODE_COLORS[nodeType] || '#6b7280';
  const isRound = START_END_TYPES.includes(nodeType);

  const handleDoubleClick = () => {
    (data as any).onSelect?.(id);
  };

  const handleContextMenu = (e: React.MouseEvent) => {
    e.preventDefault();
    (data as any).onSelect?.(id);
  };

  if (isRound) {
    return (
      <div
        className={`custom-node round-node ${selected ? 'selected' : ''}`}
        style={{ '--node-color': color } as React.CSSProperties}
        onDoubleClick={handleDoubleClick}
        onContextMenu={handleContextMenu}
        title={label}
      >
        <Handle type="target" position={Position.Left} />
        <div className="round-node-inner">
          <span>{icon}</span>
        </div>
        <Handle type="source" position={Position.Right} />
      </div>
    );
  }

  return (
    <div
      className={`custom-node ${selected ? 'selected' : ''}`}
      style={
        {
          '--node-color': color,
          minWidth: nodeType === 'container' ? 320 : 180,
        } as React.CSSProperties
      }
      onDoubleClick={handleDoubleClick}
      onContextMenu={handleContextMenu}
      title={label}
    >
      <Handle type="target" position={Position.Left} />
      <div className="node-header">
        <span className="node-icon">{icon}</span>
        <span className="node-label">{label}</span>
      </div>
      {nodeType === 'container' && (
        <div className="node-container-body" />
      )}
      <Handle type="source" position={Position.Right} />
    </div>
  );
});

CustomNode.displayName = 'CustomNode';
export default CustomNode;
