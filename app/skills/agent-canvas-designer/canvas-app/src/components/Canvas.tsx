import React, { useCallback, useEffect, useMemo, useRef } from 'react';
import {
  ReactFlow,
  Background,
  BackgroundVariant,
  useNodesState,
  useEdgesState,
  Connection,
  Node,
  Edge,
  useReactFlow,
  ReactFlowProvider,
  useViewport,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import { useCanvasStore } from '../stores/useCanvasStore';
import { useToast } from './Toast';
import { NodeType, CanvasNodeData } from '../types/canvas';
import { NODE_COLORS } from '../stores/nodeConfigs';
import CustomNode from './CustomNode';
import * as api from '../services/api';
import { createSSEClient } from '../services/sse';

/* ---------- 类型适配 ---------- */
interface FlowNode extends Node {
  data: {
    label: string;
    nodeType: NodeType;
    config: Record<string, string>;
    collapsed: boolean;
    onSelect: (id: string) => void;
    onDelete: (id: string) => void;
    onToggleCollapse: (id: string) => void;
  };
}

/* ---------- 转换函数 ---------- */
function storeNodeToFlowNode(
  n: CanvasNodeData,
  collapsed: boolean,
  handlers: {
    onSelect: (id: string) => void;
    onDelete: (id: string) => void;
    onToggleCollapse: (id: string) => void;
  }
): FlowNode {
  const isRound = n.type === 'start' || n.type === 'end';
  return {
    id: n.id,
    type: 'customNode',
    position: { x: n.x, y: n.y },
    style: isRound ? { width: 72, height: 72, borderRadius: '50%' } : undefined,
    data: {
      label: n.label,
      nodeType: n.type,
      config: n.config,
      collapsed,
      onSelect: handlers.onSelect,
      onDelete: handlers.onDelete,
      onToggleCollapse: handlers.onToggleCollapse,
    },
  };
}

/* ---------- 画布组件 ---------- */
const CanvasInner: React.FC = () => {
  const { showToast } = useToast();
  const { fitView, screenToFlowPosition, getZoom } = useReactFlow();

  const storeNodes = useCanvasStore((s) => s.nodes);
  const storeConnections = useCanvasStore((s) => s.connections);
  const selectedNodeId = useCanvasStore((s) => s.selectedNodeId);
  const isConfigLoaded = useCanvasStore((s) => s.isConfigLoaded);
  const collapsedNodes = useCanvasStore((s) => s.collapsedNodes);

  const addNode = useCanvasStore((s) => s.addNode);
  const updateNode = useCanvasStore((s) => s.updateNode);
  const deleteNode = useCanvasStore((s) => s.deleteNode);
  const addConnection = useCanvasStore((s) => s.addConnection);
  const deleteConnection = useCanvasStore((s) => s.deleteConnection);
  const selectNode = useCanvasStore((s) => s.selectNode);
  const importConfig = useCanvasStore((s) => s.importConfig);
  const exportConfig = useCanvasStore((s) => s.exportConfig);
  const clearCanvas = useCanvasStore((s) => s.clearCanvas);
  const setSyncStatus = useCanvasStore((s) => s.setSyncStatus);
  const setLastEditSource = useCanvasStore((s) => s.setLastEditSource);
  const toggleNodeCollapse = useCanvasStore((s) => s.toggleNodeCollapse);

  const autoSaveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handlers = useMemo(
    () => ({
      onSelect: selectNode,
      onDelete: deleteNode,
      onToggleCollapse: toggleNodeCollapse,
      onUpdate: updateNode,
    }),
    [selectNode, deleteNode, toggleNodeCollapse, updateNode]
  );

  const flowNodes: FlowNode[] = useMemo(
    () => storeNodes.map((n) => storeNodeToFlowNode(n, collapsedNodes.has(n.id), handlers)),
    [storeNodes, collapsedNodes, handlers]
  );

  const flowEdges: Edge[] = useMemo(
    () =>
      storeConnections.map((c, i) => ({
        id: `e${i}-${c.sourceId}-${c.targetId}`,
        source: c.sourceId,
        target: c.targetId,
        style: { stroke: '#94a3b8', strokeWidth: 2 },
        type: 'smoothstep',
      })),
    [storeConnections]
  );

  const [nodes, setNodes, onNodesChange] = useNodesState(flowNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(flowEdges);

  useEffect(() => { setNodes(flowNodes); }, [flowNodes, setNodes]);
  useEffect(() => { setEdges(flowEdges); }, [flowEdges, setEdges]);

  const scheduleAutoSave = useCallback(async () => {
    if (autoSaveTimer.current) clearTimeout(autoSaveTimer.current);
    autoSaveTimer.current = setTimeout(async () => {
      setSyncStatus('saving');
      const config = exportConfig();
      const ok = await api.saveConfig(config);
      setSyncStatus(ok ? 'saved' : 'error');
      if (ok) setLastEditSource('user');
    }, 300);
  }, [exportConfig, setSyncStatus, setLastEditSource]);

  useEffect(() => {
    if (isConfigLoaded) return;
    api.loadConfig().then((cfg) => {
      if (cfg && cfg.nodes?.length > 0) {
        importConfig(cfg, 'unknown');
        showToast('✅ 已加载画布配置', 'success');
      }
    });
  }, [isConfigLoaded, importConfig, showToast]);

  useEffect(() => {
    const cleanup = createSSEClient((cfg) => {
      importConfig(cfg, 'llm');
      setLastEditSource('llm');
      showToast('🤖 LLM 已更新画布', 'info');
    });
    return cleanup;
  }, [importConfig, setLastEditSource, showToast]);

  const onConnect = useCallback(
    (conn: Connection) => {
      if (!conn.source || !conn.target) return;
      const exists = storeConnections.some(
        (c) => c.sourceId === conn.source && c.targetId === conn.target
      );
      if (exists) return;
      addConnection({ sourceId: conn.source, targetId: conn.target });
      scheduleAutoSave();
    },
    [addConnection, storeConnections, scheduleAutoSave]
  );

  const onNodeDragStop = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      updateNode(node.id, {
        x: Math.round(node.position.x),
        y: Math.round(node.position.y),
      });
      scheduleAutoSave();
    },
    [updateNode, scheduleAutoSave]
  );

  const onNodesChangeHandler = useCallback(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (changes: any[]) => {
      changes.forEach((change: { type: string; id: string; position?: { x: number; y: number }; dragging?: boolean }) => {
        if (change.type === 'position' && change.position && !change.dragging) {
          updateNode(change.id, {
            x: Math.round(change.position.x),
            y: Math.round(change.position.y),
          });
        }
      });
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      onNodesChange(changes as any);
    },
    [onNodesChange, updateNode]
  );

  const onNodeClick = useCallback(
    (_event: React.MouseEvent, node: Node) => selectNode(node.id),
    [selectNode]
  );
  const onPaneClick = useCallback(() => selectNode(null), [selectNode]);

  const onEdgesDelete = useCallback(
    (edgesToDelete: Edge[]) => {
      edgesToDelete.forEach((e) => deleteConnection(e.source!, e.target!));
      scheduleAutoSave();
    },
    [deleteConnection, scheduleAutoSave]
  );

  const onNodesDelete = useCallback(
    (nodesToDelete: Node[]) => {
      nodesToDelete.forEach((n) => deleteNode(n.id));
      scheduleAutoSave();
    },
    [deleteNode, scheduleAutoSave]
  );

  // 拖放新节点
  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      const type = e.dataTransfer.getData('application/node-type') as NodeType;
      const label = e.dataTransfer.getData('application/node-label');
      if (!type || !label) return;

      const pos = screenToFlowPosition({ x: e.clientX, y: e.clientY });
      const id = addNode(type, label, Math.round(pos.x), Math.round(pos.y));
      selectNode(id);
      scheduleAutoSave();
    },
    [addNode, selectNode, scheduleAutoSave, screenToFlowPosition]
  );

  const onDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'copy';
  }, []);

  const nodeColor = useCallback(
    (node: Node) => {
      const fn = node as FlowNode;
      return NODE_COLORS[fn.data?.nodeType] || '#6b7280';
    },
    []
  );

  const zoomLabel = document.getElementById('zoomLabel');
  if (zoomLabel) {
    zoomLabel.textContent = Math.round(getZoom() * 100) + '%';
  }

  return (
    <div className="canvas-wrap" onDrop={onDrop} onDragOver={onDragOver}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChangeHandler}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onNodeClick={onNodeClick}
        onNodeDragStop={onNodeDragStop}
        onNodesDelete={onNodesDelete}
        onEdgesDelete={onEdgesDelete}
        onPaneClick={onPaneClick}
        nodeTypes={nodeTypes}
        fitView
        snapToGrid
        snapGrid={[16, 16]}
        minZoom={0.1}
        maxZoom={3}
        defaultEdgeOptions={{ type: 'smoothstep', style: { stroke: '#94a3b8', strokeWidth: 2 } }}
        deleteKeyCode={['Delete', 'Backspace']}
      >
        <Background variant={BackgroundVariant.Dots} gap={24} size={1} color="#d1d5db" />
      </ReactFlow>

      <div className="zoom-panel">
        <button className="zoom-btn" onClick={() => fitView({ padding: 0.1, duration: 200 })}>−</button>
        <span className="zoom-label" id="zoomLabel">{Math.round(getZoom() * 100)}%</span>
        <button className="zoom-btn" onClick={() => fitView({ padding: 0.1, duration: 200 })}>+</button>
        <button className="zoom-btn fit" onClick={() => fitView({ padding: 0.1, duration: 300 })}>⊡</button>
      </div>
    </div>
  );
};

const nodeTypes = { customNode: CustomNode };

const Canvas: React.FC = () => (
  <ReactFlowProvider>
    <CanvasInner />
  </ReactFlowProvider>
);

export default Canvas;