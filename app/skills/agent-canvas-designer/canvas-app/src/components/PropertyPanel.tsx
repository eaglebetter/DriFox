import React, { useCallback } from 'react';
import { useCanvasStore } from '../stores/useCanvasStore';
import NODE_CONFIGS from '../stores/nodeConfigs';
import { NodeConfigField } from '../types/canvas';

const PropertyPanel: React.FC = () => {
  const selectedNodeId = useCanvasStore((s) => s.selectedNodeId);
  const nodes = useCanvasStore((s) => s.nodes);
  const updateNode = useCanvasStore((s) => s.updateNode);
  const deleteNode = useCanvasStore((s) => s.deleteNode);
  const selectNode = useCanvasStore((s) => s.selectNode);

  const node = nodes.find((n) => n.id === selectedNodeId);

  const handleChange = useCallback(
    (key: string, value: string) => {
      if (!selectedNodeId || !node) return;
      updateNode(selectedNodeId, {
        config: { ...(node.config ?? {}), [key]: value },
      });
      if (key === 'title') updateNode(selectedNodeId, { label: value });
    },
    [selectedNodeId, node, updateNode]
  );

  const handleDelete = useCallback(() => {
    if (!selectedNodeId || !node) return;
    deleteNode(selectedNodeId);
    selectNode(null);
  }, [selectedNodeId, node, deleteNode, selectNode]);

  const handleClose = useCallback(() => selectNode(null), [selectNode]);

  const copyToClipboard = useCallback((text: string) => {
    navigator.clipboard.writeText(text).catch(() => {});
  }, []);

  if (!node) {
    return (
      <aside className="detail-panel hidden">
        <div className="detail-empty">
          <span>📋</span>
          <p>双击节点查看配置</p>
        </div>
      </aside>
    );
  }

  const cfg = NODE_CONFIGS[node.type];
  const saved = node.config || {};
  const fields: NodeConfigField[] = cfg?.fields ?? [];

  // 判断是否是长文本字段（提示词/代码）
  const isLongText = (key: string) =>
    ['system_prompt', 'user_prompt', 'prompt', 'code', 'inputs', 'outputs', 'loop_desc'].includes(key);

  return (
    <aside className="detail-panel">
      <div className="detail-header">
        <h3>
          <span className="detail-type-badge">{node.type}</span>
          {node.label}
        </h3>
        <button className="detail-close" onClick={handleClose}>✕</button>
      </div>

      <div className="detail-content">
        {fields.map((f) => {
          const val = saved[f.key] ?? f.default ?? '';

          return (
            <div className="detail-field" key={f.key}>
              <div className="detail-field-label-row">
                <label>{f.label}</label>
                {isLongText(f.key) && val && (
                  <button
                    className="copy-btn"
                    onClick={() => copyToClipboard(val)}
                    title="复制"
                  >
                    📋 复制
                  </button>
                )}
              </div>

              {f.type === 'textarea' ? (
                <textarea
                  rows={isLongText(f.key) ? 8 : 4}
                  value={val}
                  onChange={(e) => handleChange(f.key, e.target.value)}
                  placeholder={f.default || ''}
                />
              ) : f.type === 'select' ? (
                <select
                  value={val}
                  onChange={(e) => handleChange(f.key, e.target.value)}
                >
                  {(f.opts ?? []).map((o) => (
                    <option key={o} value={o}>{o}</option>
                  ))}
                </select>
              ) : (
                <input
                  type="text"
                  value={val}
                  onChange={(e) => handleChange(f.key, e.target.value)}
                  placeholder={f.default || ''}
                />
              )}

              {f.hint && <span className="field-hint">{f.hint}</span>}
            </div>
          );
        })}

        {/* 删除按钮 */}
        <div className="detail-actions">
          <button className="btn btn-danger" onClick={handleDelete}>
            🗑 删除节点
          </button>
        </div>
      </div>
    </aside>
  );
};

export default PropertyPanel;