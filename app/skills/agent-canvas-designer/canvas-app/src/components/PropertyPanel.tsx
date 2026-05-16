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

  // 特殊字段（prompt/code）的显示优化
  const isPromptField = (key: string) =>
    ['system_prompt', 'user_prompt', 'prompt'].includes(key);
  const isCodeField = (key: string) => key === 'code';
  const isToolsField = (key: string) => key === 'tools';

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
          const isPrompt = isPromptField(f.key);
          const isCode = isCodeField(f.key);
          const isTools = isToolsField(f.key);

          return (
            <div className="detail-field" key={f.key}>
              <div className="detail-field-label-row">
                <label>{f.label}</label>
                {(isPrompt || isCode || isTools) && val && (
                  <button
                    className="copy-btn"
                    onClick={() => copyToClipboard(val)}
                    title="复制内容"
                  >
                    📋 复制
                  </button>
                )}
              </div>

              {f.type === 'textarea' ? (
                <textarea
                  rows={isCode ? 10 : isPrompt ? 8 : 6}
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

              {/* 特殊预览：提示词/代码/工具 */}
              {isPrompt && val && (
                <div className="field-preview prompt-preview">
                  <div className="preview-label">📝 内容预览</div>
                  <div className="preview-text">{val}</div>
                </div>
              )}
              {isCode && val && (
                <div className="field-preview code-preview-full">
                  <div className="preview-label">🐍 代码预览</div>
                  <pre className="code-block">{val}</pre>
                </div>
              )}
              {isTools && val && (
                <div className="field-preview">
                  <div className="preview-label">⚙ 工具列表</div>
                  <div className="tools-list">
                    {tryParseJson(val).map((tool, i) => (
                      <span key={i} className="tool-tag">{tool}</span>
                    ))}
                  </div>
                </div>
              )}

              {f.hint && <span className="field-hint">{f.hint}</span>}
            </div>
          );
        })}

        {/* 摘要标签 */}
        {(node.type === 'llm' || node.type === 'agent') && (
          <div className="detail-field">
            <label>📌 配置摘要</label>
            <div className="config-summary">
              {saved.model && <span className="summary-tag model">📦 {saved.model}</span>}
              {saved.system_prompt && (
                <span className="summary-tag">📝 系统 {saved.system_prompt.length}字</span>
              )}
              {saved.user_prompt && (
                <span className="summary-tag">💬 用户 {saved.user_prompt.length}字</span>
              )}
              {saved.tools && <span className="summary-tag">⚙ {countTools(saved.tools)}个工具</span>}
              {saved.max_iterations && (
                <span className="summary-tag">🔁 最多{saved.max_iterations}轮</span>
              )}
            </div>
          </div>
        )}

        {node.type === 'code' && saved.code && (
          <div className="detail-field">
            <label>🐍 Python 函数</label>
            <div className="code-info">
              <span>📄 {saved.code.split('\n').length} 行</span>
              <span>⏹ {countOutputs(saved.inputs)} 输入</span>
              <span>⏹ {countOutputs(saved.outputs)} 输出</span>
            </div>
          </div>
        )}

        {node.type === 'knowledge' && saved.kb_type && (
          <div className="detail-field">
            <label>📚 知识库</label>
            <div className="config-summary">
              <span className="summary-tag kb">{saved.kb_type}</span>
              {saved.top_k && <span className="summary-tag">返回 top-{saved.top_k}</span>}
              {saved.threshold && <span className="summary-tag">阈值 {saved.threshold}</span>}
            </div>
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

function tryParseJson(val: string): string[] {
  try {
    const arr = JSON.parse(val);
    if (Array.isArray(arr)) return arr;
  } catch {}
  // 尝试换行分割
  const lines = val.split('\n').filter(Boolean);
  return lines.length > 1 ? lines : [val];
}

function countTools(tools: string): number {
  try { const a = JSON.parse(tools); if (Array.isArray(a)) return a.length; } catch {}
  return tools.split(',').filter(Boolean).length;
}

function countOutputs(outputs: string): number {
  if (!outputs) return 0;
  return outputs.split('\n').filter(Boolean).length;
}

export default PropertyPanel;