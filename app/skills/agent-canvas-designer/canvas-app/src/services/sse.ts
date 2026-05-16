import { CanvasConfig } from '../types/canvas';

type ConfigChangeCallback = (config: CanvasConfig) => void;

/**
 * SSE 客户端：监听服务器推送的 config.json 变化
 * 实现真正的秒级热更新（替代旧版 3s 轮询）
 */
export function createSSEClient(onChange: ConfigChangeCallback): () => void {
  let eventSource: EventSource | null = null;
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  let stopped = false;

  function connect() {
    if (stopped) return;

    try {
      eventSource = new EventSource('/events');

      eventSource.onmessage = (event) => {
        try {
          const config: CanvasConfig = JSON.parse(event.data);
          onChange(config);
        } catch {
          // 非 JSON 数据忽略
        }
      };

      eventSource.onerror = () => {
        // 连接断开，3秒后重连
        eventSource?.close();
        eventSource = null;
        if (!stopped) {
          reconnectTimer = setTimeout(connect, 3000);
        }
      };
    } catch {
      // 浏览器不支持 SSE，回退到轮询
      if (!stopped) {
        reconnectTimer = setTimeout(connect, 5000);
      }
    }
  }

  connect();

  return () => {
    stopped = true;
    eventSource?.close();
    if (reconnectTimer) clearTimeout(reconnectTimer);
  };
}
