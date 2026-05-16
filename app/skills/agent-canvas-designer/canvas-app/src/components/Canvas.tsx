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
  XYPosition,
  Panel,
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
    style: isRound
      ? { width: 72, height: 72, borderRadius: '50%' }
      : undefined,
    data: {
      label: n.label,
      nodeType: n.type,
      config: n.config,
      collapsed: collapsed,
      onSelect: handlers.onSelect,
      onDelete: handlers.onDelete,
      onToggleCollapse: handlers.onToggleCollapse,
    },
  };
}

/* ---------- 画布组件 ---------- */
const CanvasInner: React.FC = () => {
  const { showToast } = useToast();
  const { fitView, getZoom } = useReactFlow();

  const storeNodes = useCanvasStore((s) => s.nodes);
  const storeConnections = useCanvasStore((s) => s.connections);
  const selectedNodeId = useCanvasStore((s) => s.selectedNodeId);
  const isConfigLoaded = useCanvasStore((s) => s.isConfigLoaded);
  const syncStatus = useCanvasStore((s) => s.syncStatus);
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

  // 统一的 handlers，避免每次渲染创建新引用
  const handlers = useMemo(
    () => ({
      onSelect: selectNode,
      onDelete: deleteNode,
      onToggleCollapse: toggleNodeCollapse,
    }),
    [selectNode, deleteNode, toggleNodeCollapse]
  );

  // 将 store 数据转为 ReactFlow 格式
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

  // 当 store 数据变化时同步到 ReactFlow
  useEffect(() => {
    setNodes(flowNodes);
  }, [flowNodes, setNodes]);

  useEffect(() => {
    setEdges(flowEdges);
  }, [flowEdges, setEdges]);

  // 自动保存（300ms 防抖）
  const scheduleAutoSave = useCallback(async () => {
    if (autoSaveTimer.current) clearTimeout(autoSaveTimer.current);
    autoSaveTimer.current = setTimeout(async () => {
      setSyncStatus('saving');
      const config = exportConfig();
      const ok = await api.saveConfig(config);
      if (ok) {
        setSyncStatus('saved');
        setLastEditSource('user');
      } else {
        setSyncStatus('error');
      }
    }, 300);
  }, [exportConfig, setSyncStatus, setLastEditSource]);

  // 自动加载 config.json
  useEffect(() => {
    if (isConfigLoaded) return;
    api.loadConfig().then((cfg) => {
      if (cfg && cfg.nodes?.length > 0) {
        importConfig(cfg, 'unknown');
        showToast('✅ 已加载画布配置', 'success');
        setTimeout(() => fitView({ padding: 0.1, duration: 500 }), 300);
      }
    });
  }, [isConfigLoaded, importConfig, showToast, fitView]);

  // SSE 实时热更新（LLM → 画布）
  useEffect(() => {
    const cleanup = createSSEClient((cfg) => {
      importConfig(cfg, 'llm');
      setLastEditSource('llm');
      showToast('🤖 LLM 已更新画布', 'info');
      setTimeout(() => fitView({ padding: 0.1, duration: 500 }), 300);
    });
    return cleanup;
  }, [importConfig, setLastEditSource, showToast, fitView]);

  // 连线
  const onConnect = useCallback(
    (conn: Connection) => {
      if (!conn.source || !conn.target) return;
      // 防止重复连线
      const exists = storeConnections.some(
        (c) => c.sourceId === conn.source && c.targetId === conn.target
      );
      if (exists) return;
      addConnection({ sourceId: conn.source, targetId: conn.target });
      scheduleAutoSave();
    },
    [addConnection, storeConnections, scheduleAutoSave]
  );

  // 节点拖拽结束 → 保存位置
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

  // 节点位置变化（拖拽中实时同步位置到 store）
  const onNodesChangeHandler = useCallback(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (changes: any[]) => {
      changes.forEach((change) => {
        if (
          change.type === 'position' &&
          change.position &&
          !change.dragging
        ) {
          updateNode(change.id, {
            x: Math.round(change.position.x),
            y: Math.round(change.position.y),
          });
        }
      });
      onNodesChange(changes as Parameters<typeof onNodesChange>[0]);
    },
    [onNodesChange, updateNode]
  );

  // 节点点击 → 选中
  const onNodeClick = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      selectNode(node.id);
    },
    [selectNode]
  );

  // 空白处点击 → 取消选中
  const onPaneClick = useCallback(() => {
    selectNode(null);
  }, [selectNode]);

  // 删边
  const onEdgesDelete = useCallback(
    (edgesToDelete: Edge[]) => {
      edgesToDelete.forEach((e) => {
        deleteConnection(e.source!, e.target!);
      });
      scheduleAutoSave();
    },
    [deleteConnection, scheduleAutoSave]
  );

  // 删节点
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

      const rect = (e.target as HTMLElement)
        .closest('.react-flow')
        ?.getBoundingClientRect();
      if (!rect) return;

      const position: XYPosition = {
        x: e.clientX - rect.left,
        y: e.clientY - rect.top,
      };

      const id = addNode(type, label, Math.round(position.x), Math.round(position.y));
      selectNode(id);
      scheduleAutoSave();
    },
    [addNode, selectNode, scheduleAutoSave]
  );

  const onDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'copy';
  }, []);

  // 右键菜单（点击节点右键）
  const onNodeContextMenu = useCallback(
    (e: React.MouseEvent, node: Node) => {
      e.preventDefault();
      selectNode(node.id);
    },
    [selectNode]
  );

  const nodeColor = useCallback(
    (node: Node) => {
      const fn = node as FlowNode;
      return NODE_COLORS[fn.data?.nodeType] || '#6b7280';
    },
    []
  );

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
        onNodeContextMenu={onNodeContextMenu}
        onPaneClick={onPaneClick}
        nodeTypes={nodeTypes}
        fitView
        snapToGrid
        snapGrid={[16, 16]}
        minZoom={0.1}
        maxZoom={3}
        defaultEdgeOptions={{
          type: 'smoothstep',
          style: { stroke: '#94a3b8', strokeWidth: 2 },
        }}
        deleteKeyCode={['Delete', 'Backspace']}
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={24}
          size={1}
          color="#d1d5db"
        />
      </ReactFlow>

      {/* 缩放控制面板 */}
      <Panel position="bottom-left" className="zoom-panel">
        <button
          className="zoom-btn"
          onClick={() => {
            const z = getZoom();
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            (window as any).__rf?.zoomTo?.(z - 0.15);
          }}
        >
          −
        </button>
        <span className="zoom-label" id="zoomLabel">
          100%
        </span>
        <button
          className="zoom-btn"
          onClick={() => {
            const z = getZoom();
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            (window as any).__rf?.zoomTo?.(z + 0.15);
          }}
        >
          +
        </button>
        <button className="zoom-btn fit" onClick={() => fitView({ padding: 0.1, duration: 300 })}>
          ⊡
        </button>
      </Panel>
    </div>
  );
};

const nodeTypes = {
  customNode: CustomNode,
};

const Canvas: React.FC = () => (
  <ReactFlowProvider>
    <CanvasInner />
  </ReactFlowProvider>
);

export default Canvas;