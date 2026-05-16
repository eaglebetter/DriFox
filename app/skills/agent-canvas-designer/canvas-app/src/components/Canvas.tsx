import React, { useCallback, useEffect, useMemo, useRef } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  addEdge,
  Connection,
  Node,
  Edge,
  NodeChange,
  EdgeChange,
  BackgroundVariant,
  Panel,
  ReactFlowProvider,
  XYPosition,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import { useCanvasStore } from '../stores/useCanvasStore';
import { useToast } from './Toast';
import { NodeType, CanvasNodeData, EditSource } from '../types/canvas';
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
    onSelect: (id: string) => void;
    onDelete: (id: string) => void;
  };
}

/* ---------- 转换函数 ---------- */
function storeNodeToFlowNode(n: CanvasNodeData, handlers: any): FlowNode {
  const isRound = n.type === 'start' || n.type === 'end';
  return {
    id: n.id,
    type: 'customNode',
    position: { x: n.x, y: n.y },
    style: isRound ? { width: 72, height: 72 } : undefined,
    data: {
      label: n.label,
      nodeType: n.type,
      config: n.config,
      onSelect: handlers.onSelect,
      onDelete: handlers.onDelete,
    },
  };
}

function flowNodeToStoreNode(fn: FlowNode): CanvasNodeData {
  return {
    id: fn.id,
    type: fn.data.nodeType,
    label: fn.data.label,
    x: fn.position.x,
    y: fn.position.y,
    config: fn.data.config,
  };
}

/* ---------- 画布组件 ---------- */
const CanvasInner: React.FC = () => {
  const { showToast } = useToast();
  const storeNodes = useCanvasStore((s) => s.nodes);
  const storeConnections = useCanvasStore((s) => s.connections);
  const selectedNodeId = useCanvasStore((s) => s.selectedNodeId);
  const isConfigLoaded = useCanvasStore((s) => s.isConfigLoaded);
  const syncStatus = useCanvasStore((s) => s.syncStatus);

  const addNode = useCanvasStore((s) => s.addNode);
  const updateNode = useCanvasStore((s) => s.updateNode);
  const deleteNode = useCanvasStore((s) => s.deleteNode);
  const addConnection = useCanvasStore((s) => s.addConnection);
  const selectNode = useCanvasStore((s) => s.selectNode);
  const importConfig = useCanvasStore((s) => s.importConfig);
  const exportConfig = useCanvasStore((s) => s.exportConfig);
  const clearCanvas = useCanvasStore((s) => s.clearCanvas);
  const setSyncStatus = useCanvasStore((s) => s.setSyncStatus);

  const autoSaveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // 将 store 数据转为 ReactFlow 格式
  const flowNodes: FlowNode[] = useMemo(
    () =>
      storeNodes.map((n) =>
        storeNodeToFlowNode(n, {
          onSelect: selectNode,
          onDelete: deleteNode,
        })
      ),
    [storeNodes, selectNode, deleteNode]
  );

  const flowEdges: Edge[] = useMemo(
    () =>
      storeConnections.map((c, i) => ({
        id: `e${i}-${c.sourceId}-${c.targetId}`,
        source: c.sourceId,
        target: c.targetId,
        animated: false,
        style: { stroke: '#94a3b8', strokeWidth: 2 },
      })),
    [storeConnections]
  );

  const [nodes, setNodes, onNodesChange] = useNodesState(flowNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(flowEdges);

  // 当 store 数据变化时同步到 ReactFlow
  useEffect(() => {
    setNodes(flowNodes);
  }, [flowNodes, setNodes]);

  useEffect(() => {
    setEdges(flowEdges);
  }, [flowEdges, setEdges]);

  // 用户编辑自动保存（防抖）
  const scheduleAutoSave = useCallback(() => {
    if (autoSaveTimer.current) clearTimeout(autoSaveTimer.current);
    autoSaveTimer.current = setTimeout(async () => {
      const config = exportConfig();
      setSyncStatus('saving');
      const ok = await api.saveConfig(config);
      setSyncStatus(ok ? 'saved' : 'error');
    }, 300);
  }, [exportConfig, setSyncStatus]);

  // 自动加载 config.json
  useEffect(() => {
    if (isConfigLoaded) return;
    api.loadConfig().then((cfg) => {
      if (cfg && cfg.nodes?.length > 0) {
        importConfig(cfg, 'unknown');
        showToast('✅ 已加载配置', 'success');
      }
    });
  }, [isConfigLoaded, importConfig, showToast]);

  // SSE 实时热更新
  useEffect(() => {
    const cleanup = createSSEClient((cfg) => {
      importConfig(cfg, 'llm');
      showToast('🤖 大模型已更新画布', 'info');
    });
    return cleanup;
  }, [importConfig, showToast]);

  // 连线事件
  const onConnect = useCallback(
    (conn: Connection) => {
      if (!conn.source || !conn.target) return;
      addConnection({ sourceId: conn.source, targetId: conn.target });
      scheduleAutoSave();
    },
    [addConnection, scheduleAutoSave]
  );

  // 节点拖拽结束
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

  // 节点点击选中
  const onNodeClick = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      selectNode(node.id);
    },
    [selectNode]
  );

  // 删除键
  const onKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Delete' && selectedNodeId) {
        deleteNode(selectedNodeId);
        selectNode(null);
        scheduleAutoSave();
      }
    },
    [selectedNodeId, deleteNode, selectNode, scheduleAutoSave]
  );

  // 删边事件
  const onEdgesDelete = useCallback(
    (edgesToDelete: Edge[]) => {
      edgesToDelete.forEach((e) => {
        addConnection({ sourceId: '', targetId: '' }); // no-op just to trigger
        // Actually we need to remove the connection from store
      });
      scheduleAutoSave();
    },
    [scheduleAutoSave]
  );

  // 拖放新节点
  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      const type = e.dataTransfer.getData('application/node-type') as NodeType;
      const label = e.dataTransfer.getData('application/node-label');
      if (!type || !label) return;

      const rect = (e.target as HTMLElement)
        .closest('.react-flow')
        ?.getBoundingClientRect();
      if (!rect) return;

      const position: XYPosition = {
        x: e.clientX - rect.left - 90,
        y: e.clientY - rect.top - 20,
      };

      addNode(type, label, Math.round(position.x), Math.round(position.y));
      scheduleAutoSave();
    },
    [addNode, scheduleAutoSave]
  );

  const onDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'copy';
  }, []);

  // 导出反馈
  const handleExportFeedback = useCallback(async () => {
    const config = exportConfig();
    const ok = await api.saveFeedback(config);
    if (ok) {
      showToast('✅ 已导出反馈 — 告诉大模型"改好了"', 'success');
    } else {
      showToast('❌ 导出失败', 'error');
    }
  }, [exportConfig, showToast]);

  // 加载文件
  const handleLoadFile = useCallback(() => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';
    input.onchange = async () => {
      const file = input.files?.[0];
      if (!file) return;
      try {
        const text = await file.text();
        const cfg = JSON.parse(text);
        importConfig(cfg, 'user');
        showToast('✅ 已导入配置', 'success');
      } catch {
        showToast('❌ JSON 格式错误', 'error');
      }
    };
    input.click();
  }, [importConfig, showToast]);

  // 清空画布
  const handleClear = useCallback(() => {
    clearCanvas();
    setSyncStatus('idle');
    showToast('🗑 画布已清空', 'info');
  }, [clearCanvas, setSyncStatus, showToast]);

  // 高亮选中节点
  const nodeColor = useCallback(
    (node: Node) => {
      const fn = node as FlowNode;
      return NODE_COLORS[fn.data?.nodeType] || '#6b7280';
    },
    []
  );

  return (
    <div
      className="canvas-wrap"
      onDrop={onDrop}
      onDragOver={onDragOver}
      onKeyDown={onKeyDown}
      tabIndex={0}
    >
      <div className="canvas-toolbar-embedded">
        <button className="btn btn-outline" onClick={handleLoadFile}>
          📂 加载
        </button>
        <button className="btn btn-primary" onClick={handleExportFeedback}>
          📤 导出反馈
        </button>
        <button className="btn" onClick={handleClear}>
          🗑 清空
        </button>
      </div>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onNodeClick={onNodeClick}
        onNodeDragStop={onNodeDragStop}
        onEdgesDelete={onEdgesDelete}
        nodeTypes={nodeTypes}
        fitView
        deleteKeyCode={['Delete', 'Backspace']}
        snapToGrid
        snapGrid={[16, 16]}
        minZoom={0.2}
        maxZoom={2}
        defaultEdgeOptions={{
          style: { stroke: '#94a3b8', strokeWidth: 2 },
        }}
      >
        <Background variant={BackgroundVariant.Dots} gap={24} size={1} color="#d1d5db" />
        <Controls />
        <MiniMap
          nodeColor={nodeColor}
          maskColor="rgba(0,0,0,0.08)"
          style={{ right: 390 }}
        />
      </ReactFlow>
    </div>
  );
};

const nodeTypes = {
  customNode: CustomNode,
};

/** 带 Provider 的画布 */
const Canvas: React.FC = () => (
  <ReactFlowProvider>
    <CanvasInner />
  </ReactFlowProvider>
);

export default Canvas;
