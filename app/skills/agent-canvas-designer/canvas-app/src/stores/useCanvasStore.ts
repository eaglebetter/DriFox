import { create } from 'zustand';
import {
  NodeType,
  CanvasConfig,
  CanvasNodeData,
  CanvasConnectionData,
  SyncStatus,
  EditSource,
} from '../types/canvas';

interface CanvasState {
  // 数据
  nodes: CanvasNodeData[];
  connections: CanvasConnectionData[];
  meta: { title: string; description?: string };

  // 同步状态
  syncStatus: SyncStatus;
  lastEditSource: EditSource;

  // 选区
  selectedNodeId: string | null;

  // 是否已从配置加载（防止覆盖用户编辑）
  isConfigLoaded: boolean;

  // 节点折叠状态
  collapsedNodes: Set<string>;

  // 操作
  setNodes: (nodes: CanvasNodeData[]) => void;
  setConnections: (connections: CanvasConnectionData[]) => void;
  addNode: (type: NodeType, label: string, x: number, y: number) => string;
  updateNode: (id: string, patch: Partial<CanvasNodeData>) => void;
  deleteNode: (id: string) => void;
  addConnection: (conn: CanvasConnectionData) => void;
  deleteConnection: (sourceId: string, targetId: string) => void;
  selectNode: (id: string | null) => void;
  importConfig: (config: CanvasConfig, source: EditSource) => void;
  exportConfig: () => CanvasConfig;
  clearCanvas: () => void;
  setSyncStatus: (status: SyncStatus) => void;
  setLastEditSource: (source: EditSource) => void;
  toggleNodeCollapse: (id: string) => void;
}

let _nodeSeq = 0;

export const useCanvasStore = create<CanvasState>((set, get) => ({
  nodes: [],
  connections: [],
  meta: { title: '未命名流程' },
  syncStatus: 'idle',
  lastEditSource: 'unknown',
  selectedNodeId: null,
  isConfigLoaded: false,
  collapsedNodes: new Set<string>(),

  setNodes: (nodes) => set({ nodes }),
  setConnections: (connections) => set({ connections }),

  addNode: (type, label, x, y) => {
    const id = `node_${++_nodeSeq}`;
    set((s) => ({
      nodes: [...s.nodes, { id, type, label, x, y, config: {} }],
    }));
    return id;
  },

  updateNode: (id, patch) =>
    set((s) => ({
      nodes: s.nodes.map((n) => (n.id === id ? { ...n, ...patch } : n)),
    })),

  deleteNode: (id) =>
    set((s) => ({
      nodes: s.nodes.filter((n) => n.id !== id),
      connections: s.connections.filter(
        (c) => c.sourceId !== id && c.targetId !== id
      ),
      selectedNodeId: s.selectedNodeId === id ? null : s.selectedNodeId,
    })),

  addConnection: (conn) =>
    set((s) => ({
      connections: [...s.connections, conn],
    })),

  deleteConnection: (sourceId, targetId) =>
    set((s) => ({
      connections: s.connections.filter(
        (c) => !(c.sourceId === sourceId && c.targetId === targetId)
      ),
    })),

  selectNode: (id) => set({ selectedNodeId: id }),

  importConfig: (config, source) => {
    // 从配置中提取最大 node 序号，防止 ID 冲突
    const maxSeq = config.nodes.reduce((max, n) => {
      const m = n.id.match(/node_(\d+)/);
      return m ? Math.max(max, parseInt(m[1])) : max;
    }, 0);
    if (maxSeq >= _nodeSeq) _nodeSeq = maxSeq;

    set({
      nodes: config.nodes.map((n) => ({ ...n })),
      connections: config.connections.map((c) => ({ ...c })),
      meta: { ...config.meta },
      syncStatus: 'saved',
      lastEditSource: source,
      isConfigLoaded: true,
    });
  },

  exportConfig: () => {
    const s = get();
    return {
      version: '2.0',
      flow: 'custom',
      meta: { ...s.meta },
      nodes: s.nodes.map((n) => ({ ...n })),
      connections: s.connections.map((c) => ({ ...c })),
    };
  },

  clearCanvas: () =>
    set({
      nodes: [],
      connections: [],
      meta: { title: '未命名流程' },
      selectedNodeId: null,
      isConfigLoaded: false,
      collapsedNodes: new Set(),
    }),

  setSyncStatus: (status) => set({ syncStatus: status }),
  setLastEditSource: (source) => set({ lastEditSource: source }),

  toggleNodeCollapse: (id) =>
    set((s) => {
      const next = new Set(s.collapsedNodes);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return { collapsedNodes: next };
    }),
}));
