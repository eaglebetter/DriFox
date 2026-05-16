import React, { useCallback, useEffect, useRef } from 'react';
import { useCanvasStore } from '../stores/useCanvasStore';
import NODE_CONFIGS from '../stores/nodeConfigs';
import { NodeConfigField } from '../types/canvas';

const PropertyPanel: React.FC = () => {
  const selectedNodeId = useCanvasStore((s) => s.selectedNodeId);
  const nodes = useCanvasStore((s) => s.nodes);
  const updateNode = useCanvasStore((s) => s.updateNode);
  const deleteNode = useCanvasStore((s) => s.deleteNode);
  const selectNode = useCanvasStore((s) => s.selectNode);
  const setSyncStatus = useCanvasStore((s) => s.setSyncStatus);

  const node = nodes.find((n) => n.id === selectedNodeId);

  const handleChange = useCallback(
    (key: string, value: string) => {
      if (!selectedNodeId) return;
      updateNode(selectedNodeId, {
        config: { ...(node?.config ?? {}), [key]: value },
      });
      // 如果改的是 title 字段，同步更新 label
      if (key === 'title') {
        updateNode(selectedNodeId, { label: value });
      }
      setSyncStatus('saving');
    },
    [selectedNodeId, node, updateNode, setSyncStatus]
  );

  const handleDelete = useCallback(() => {
    if (!selectedNodeId || !node) return;
    deleteNode(selectedNodeId);
    selectNode(null);
  }, [selectedNodeId, node, deleteNode, selectNode]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Escape') {
        selectNode(null);
      }
      if (e.key === 'Delete' && e.ctrlKey) {
        handleDelete();
      }
    },
    [selectNode, handleDelete]
  );

  if (!node) {
    return (
      <aside className="detail-panel hidden">
        <div className="detail-empty">
          <span style={{ fontSize: 40, opacity: 0.3 }}>📋</span>
          <p>选择一个节点查看配置</p>
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
        <h3>
          <span style={{ marginRight: 8 }}>{node.type}</span>
          {node.label}
        </h3>
        <button className="detail-close" onClick={() => selectNode(null)}>
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

        {node.type === 'llm' || node.type === 'agent' ? (
          <div className="detail-field">
            <label>💡 提示词预览</label>
            <div className="prompt-preview">
              {(saved.system_prompt?.length ?? 0) > 0 && (
                <span className="tag blue">
                  系统提示词 ({saved.system_prompt!.length}字)
                </span>
              )}
              {(saved.user_prompt?.length ?? 0) > 0 && (
                <span className="tag orange">
                  用户提示词 ({saved.user_prompt!.length}字)
                </span>
              )}
              {(saved.tools?.length ?? 0) > 0 && (
                <span className="tag purple">工具已配置</span>
              )}
            </div>
          </div>
        ) : null}

        {node.type === 'code' && (saved.code?.length ?? 0) > 0 && (
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
