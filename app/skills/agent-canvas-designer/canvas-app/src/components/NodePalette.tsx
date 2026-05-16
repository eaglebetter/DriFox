import React, { useState, useCallback } from 'react';
import { NodeType } from '../types/canvas';
import { NODE_ICONS, NODE_COLORS } from '../stores/nodeConfigs';

interface NodePaletteProps {
  onDragStart: (type: NodeType, label: string) => void;
}

interface PaletteGroup {
  title: string;
  items: { type: NodeType; label: string }[];
}

const PALETTE_GROUPS: PaletteGroup[] = [
  {
    title: '基础',
    items: [
      { type: 'start', label: '开始' },
      { type: 'reply', label: '回复' },
      { type: 'end', label: '结束' },
    ],
  },
  {
    title: 'AI 组件',
    items: [
      { type: 'llm', label: '大模型组件' },
      { type: 'agent', label: 'Agent 组件' },
      { type: 'classifier', label: '问题分类器' },
      { type: 'param-extractor', label: '参数提取器' },
    ],
  },
  {
    title: '知识 & 数据',
    items: [
      { type: 'knowledge', label: '知识检索' },
      { type: 'ask-table', label: '智能问表' },
      { type: 'doc-extractor', label: '文档提取器' },
      { type: 'api-request', label: '接口请求' },
    ],
  },
  {
    title: '控制流',
    items: [
      { type: 'condition', label: '条件分支' },
      { type: 'container', label: '循环/迭代' },
      { type: 'code', label: '代码执行' },
    ],
  },
];

const NodePalette: React.FC<NodePaletteProps> = ({ onDragStart }) => {
  const [search, setSearch] = useState('');

  const handleDragStart = useCallback(
    (e: React.DragEvent, type: NodeType, label: string) => {
      e.dataTransfer.setData('application/node-type', type);
      e.dataTransfer.setData('application/node-label', label);
      e.dataTransfer.effectAllowed = 'copy';
      onDragStart(type, label);
    },
    [onDragStart]
  );

  const filterItem = (label: string) =>
    !search || label.toLowerCase().includes(search.toLowerCase());

  return (
    <aside className="sidebar">
      <div className="sidebar-search">
        <input
          type="text"
          placeholder="🔍 搜索组件..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>
      {PALETTE_GROUPS.map((group) => {
        const visible = group.items.filter((it) => filterItem(it.label));
        if (visible.length === 0) return null;
        return (
          <div className="sidebar-section" key={group.title}>
            <div className="sidebar-section-title">{group.title}</div>
            {visible.map((item) => (
              <div
                key={item.type + item.label}
                className="sidebar-item"
                draggable
                onDragStart={(e) => handleDragStart(e, item.type, item.label)}
              >
                <span
                  className="sidebar-item-icon"
                  style={{ background: NODE_COLORS[item.type] }}
                >
                  {NODE_ICONS[item.type]}
                </span>
                <span className="sidebar-item-text">{item.label}</span>
              </div>
            ))}
          </div>
        );
      })}
    </aside>
  );
};

export default NodePalette;
