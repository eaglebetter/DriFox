import React, { useCallback } from 'react';
import { useCanvasStore } from '../stores/useCanvasStore';
import { SyncStatus } from '../types/canvas';

interface ToolbarProps {
  onImportFile: () => void;
  onExportFeedback: () => void;
  onClear: () => void;
}

const STATUS_LABELS: Record<SyncStatus, { text: string; cls: string }> = {
  idle: { text: '✅ 已就绪', cls: 'status-idle' },
  saving: { text: '💾 保存中...', cls: 'status-saving' },
  saved: { text: '✅ 已保存', cls: 'status-saved' },
  error: { text: '❌ 保存失败', cls: 'status-error' },
  loading: { text: '📡 加载中...', cls: 'status-loading' },
};

const Toolbar: React.FC<ToolbarProps> = ({
  onImportFile,
  onExportFeedback,
  onClear,
}) => {
  const meta = useCanvasStore((s) => s.meta);
  const syncStatus = useCanvasStore((s) => s.syncStatus);
  const lastEditSource = useCanvasStore((s) => s.lastEditSource);

  const status = STATUS_LABELS[syncStatus];

  return (
    <header className="toolbar">
      <div className="toolbar-left">
        <div className="toolbar-logo">
          🖥 <span>智能体画布</span>
        </div>
        <span className="toolbar-meta">{meta.title}</span>
      </div>
      <div className="toolbar-center">
        <span className={`sync-indicator ${status.cls}`}>
          {status.text}
        </span>
        {lastEditSource === 'llm' && (
          <span className="sync-source-tag llm">🤖 LLM 已更新</span>
        )}
        {lastEditSource === 'user' && (
          <span className="sync-source-tag user">👤 已修改</span>
        )}
      </div>
      <div className="toolbar-right">
        <button className="btn btn-outline" onClick={onImportFile}>
          📂 加载配置
        </button>
        <button className="btn btn-primary" onClick={onExportFeedback}>
          📤 导出反馈
        </button>
        <button className="btn" onClick={onClear}>
          🗑 清空
        </button>
      </div>
    </header>
  );
};

export default Toolbar;
