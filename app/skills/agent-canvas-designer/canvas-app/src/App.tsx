import React, { useCallback } from 'react';
import { ToastProvider, useToast } from './components/Toast';
import { useCanvasStore } from './stores/useCanvasStore';
import * as api from './services/api';
import NodePalette from './components/NodePalette';
import PropertyPanel from './components/PropertyPanel';
import Canvas from './components/Canvas';
import { NodeType } from './types/canvas';

const AppInner: React.FC = () => {
  const { showToast } = useToast();

  const handleDragStart = useCallback(
    (_type: NodeType, _label: string) => {
      // 拖拽开始时回调（可用于记录日志等）
    },
    []
  );

  return (
    <div className="app">
      <div className="main-layout">
        <NodePalette onDragStart={handleDragStart} />
        <Canvas />
        <PropertyPanel />
      </div>
    </div>
  );
};

const App: React.FC = () => (
  <ToastProvider>
    <AppInner />
  </ToastProvider>
);

export default App;
