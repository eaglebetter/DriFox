import React from 'react';
import { ToastProvider } from './components/Toast';
import NodePalette from './components/NodePalette';
import PropertyPanel from './components/PropertyPanel';
import Canvas from './components/Canvas';
import { NodeType } from './types/canvas';
import './styles/index.css';

const App: React.FC = () => (
  <ToastProvider>
    <div className="app">
      <NodePalette onDragStart={() => {}} />
      <Canvas />
      <PropertyPanel />
    </div>
  </ToastProvider>
);

export default App;