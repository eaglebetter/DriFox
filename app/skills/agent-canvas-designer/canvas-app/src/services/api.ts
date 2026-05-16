import { CanvasConfig } from '../types/canvas';

const BASE = '';

/** 从服务器加载 config.json */
export async function loadConfig(): Promise<CanvasConfig | null> {
  try {
    const resp = await fetch(`${BASE}/config.json?t=${Date.now()}`);
    if (!resp.ok) return null;
    return resp.json();
  } catch {
    return null;
  }
}

/** 保存配置到服务器（大模型写入触发） */
export async function saveConfig(data: CanvasConfig): Promise<boolean> {
  try {
    const resp = await fetch(`${BASE}/save-config`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return resp.ok;
  } catch {
    return false;
  }
}

/** 导出反馈到 feedback.json */
export async function saveFeedback(data: CanvasConfig): Promise<boolean> {
  try {
    const resp = await fetch(`${BASE}/save-feedback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return resp.ok;
  } catch {
    return false;
  }
}

/** 获取画布当前状态（大模型读取） */
export async function getState(): Promise<CanvasConfig | null> {
  try {
    const resp = await fetch(`${BASE}/get-state`);
    if (!resp.ok) return null;
    return resp.json();
  } catch {
    return null;
  }
}
