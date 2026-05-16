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
      if (key === 'title') {
        updateNode(selectedNodeId, { label: value });
      }
    },
    [selectedNodeId, node, updateNode]
  );

  const handleDelete = useCallback(() => {
    if (!selectedNodeId || !node) return;
    deleteNode(selectedNodeId);
    selectNode(null);
  }, [selectedNodeId, node, deleteNode, selectNode]);

  const handleClose = useCallback(() => {
    selectNode(null);
  }, [selectNode]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Escape') handleClose();
      if (e.key === 'Delete' && e.ctrlKey) handleDelete();
    },
    [handleClose, handleDelete]
  );

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

  return (
    <aside className="detail-panel" onKeyDown={handleKeyDown}>
      <div className="detail-header">
        <h3>{node.label}</h3>
        <button className="detail-close" onClick={handleClose}>
          ✕
        </button>
      </div>
      <div className="detail-content">
        {fields.map((f) => {
          const val = saved[f.key] ?? f.default ?? '';
          return (
            <div className="detail-field" key={f.key}>
              <label>{f.label}</label>
              {f.type === 'textarea' ? (
                <textarea
                  rows={6}
                  value={val}
                  onChange={(e) => handleChange(f.key, e.target.value)}
                />
              ) : f.type === 'select' ? (
                <select
                  value={val}
                  onChange={(e) => handleChange(f.key, e.target.value)}
                >
                  {f.opts?.map((o) => (
                    <option key={o} value={o}>
                      {o}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  type="text"
                  value={val}
                  onChange={(e) => handleChange(f.key, e.target.value)}
                />
              )}
              {f.hint && <span className="field-hint">{f.hint}</span>}
            </div>
          );
        })}

        {(node.type === 'llm' || node.type === 'agent') && (
          <div className="detail-field">
            <label>💡 提示词预览</label>
            <div className="prompt-preview">
              {saved.system_prompt && (
                <span className="tag blue">
                  系统提示词 {saved.system_prompt.length}字
                </span>
              )}
              {saved.user_prompt && (
                <span className="tag orange">
                  用户提示词 {saved.user_prompt.length}字
                </span>
              )}
              {saved.tools && <span className="tag purple">工具已配置</span>}
            </div>
          </div>
        )}

        {node.type === 'code' && saved.code && (
          <div className="detail-field">
            <label>代码预览</label>
            <pre className="code-preview">{saved.code}</pre>
          </div>
        )}

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