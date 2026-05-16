#!/usr/bin/env python3
"""
画布专用服务器 v3.0 — 支持 SSE 实时热更新

功能：
- GET   /*               服务静态文件（Vite 构建产物，从 dist/ 目录）
- GET   /events          SSE 端点：推送 config.json 变化（实时热更新）
- GET   /get-state       返回 config.json 最新画布状态（供大模型读取）
- POST  /save-config     保存配置到 config.json（画布自动保存 / 大模型写回）
- POST  /save-feedback   保存反馈到 feedback.json（兼容旧版）
"""

import http.server
import socketserver
import json
import os
import urllib.parse
import threading
import time
import queue

PORT = 8081
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 静态文件目录（Vite 构建产物）
DIST_DIR = os.path.join(BASE_DIR, 'dist')
if not os.path.isdir(DIST_DIR):
    DIST_DIR = BASE_DIR  # 回退到当前目录

# ============ SSE 广播系统 ============

class SSEBroadcaster:
    """管理所有 SSE 客户端连接，配置变化时广播"""

    def __init__(self):
        self._clients: list[queue.Queue] = []
        self._lock = threading.Lock()
        self._last_mtime = 0
        self._config_path = os.path.join(BASE_DIR, 'config.json')
        self._running = False

    def start_watching(self):
        """启动文件监控线程"""
        self._running = True
        t = threading.Thread(target=self._watch_loop, daemon=True)
        t.start()
        print(f'👁  文件监控已启动: {self._config_path}')

    def register_client(self) -> queue.Queue:
        """注册一个 SSE 客户端，返回其消息队列"""
        q: queue.Queue = queue.Queue()
        with self._lock:
            self._clients.append(q)
        return q

    def unregister_client(self, q: queue.Queue):
        """注销 SSE 客户端"""
        with self._lock:
            if q in self._clients:
                self._clients.remove(q)

    def _watch_loop(self):
        """后台线程：每 500ms 检查 config.json 是否变化"""
        while self._running:
            try:
                mtime = os.path.getmtime(self._config_path) if os.path.exists(self._config_path) else 0
                if mtime != self._last_mtime and self._last_mtime != 0:
                    # 文件已变化，读取并广播
                    with open(self._config_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    self._broadcast(content)
                    print(f'🔄 检测到 config.json 变化，推送到 {len(self._clients)} 个客户端')
                self._last_mtime = mtime
            except Exception as e:
                pass
            time.sleep(0.5)

    def _broadcast(self, data: str):
        """向所有客户端推送数据"""
        with self._lock:
            dead = []
            for q in self._clients:
                try:
                    q.put_nowait(data)
                except queue.Full:
                    dead.append(q)
            for q in dead:
                self._clients.remove(q)


broadcaster = SSEBroadcaster()


# ============ HTTP 处理器 ============

class CanvasHandler(http.server.SimpleHTTPRequestHandler):

    def __init__(self, *args, **kwargs):
        # 静态文件从 DIST_DIR 目录服务
        super().__init__(*args, directory=DIST_DIR, **kwargs)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip('/')

        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)

        if path == '/save-config':
            self._save_config(body)
        elif path == '/save-feedback':
            self._save_feedback(body)
        else:
            self._send_json(404, {'error': 'not found'})

    def _save_config(self, data: bytes):
        """保存 config.json（画布自动保存 + 大模型写回）"""
        try:
            filepath = os.path.join(BASE_DIR, 'config.json')
            # 验证 JSON 合法性
            json.loads(data)
            with open(filepath, 'wb') as f:
                f.write(data)

            self._send_json(200, {
                'success': True,
                'path': filepath,
                'size': len(data),
            })
            print(f'✅ 已保存 config.json ({len(data)} bytes)')
        except json.JSONDecodeError as e:
            self._send_json(400, {'error': f'JSON 格式错误: {str(e)}'})
        except Exception as e:
            self._send_json(500, {'error': str(e)})

    def _save_feedback(self, data: bytes):
        """保存 feedback.json（兼容旧版导出反馈）"""
        try:
            filepath = os.path.join(BASE_DIR, 'feedback.json')
            json.loads(data)
            with open(filepath, 'wb') as f:
                f.write(data)
            self._send_json(200, {
                'success': True,
                'path': filepath,
                'size': len(data),
            })
            print(f'✅ 已保存 feedback.json ({len(data)} bytes)')
        except json.JSONDecodeError as e:
            self._send_json(400, {'error': f'JSON 格式错误: {str(e)}'})
        except Exception as e:
            self._send_json(500, {'error': str(e)})

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip('/')

        # SSE 端点
        if path == '/events':
            self._handle_sse()
            return

        # 获取当前状态
        if path == '/get-state':
            self._send_json_file('config.json')
            return

        # config.json 存在于 BASE_DIR（大模型写入的目录），不在 dist/
        if path == '/config.json':
            self._send_json_file('config.json')
            return

        # 静态文件（重定向 / → index.html）
        if path == '' or self.path == '/':
            self.send_response(302)
            self.send_header('Location', '/index.html')
            self.end_headers()
            return

        return super().do_GET()

    def _handle_sse(self):
        """SSE 长连接：持续推送 config.json 变化"""
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Connection', 'keep-alive')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

        q = broadcaster.register_client()
        try:
            # 发送初始数据
            config_path = os.path.join(BASE_DIR, 'config.json')
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = f.read()
                self.wfile.write(f'data: {data}\n\n'.encode('utf-8'))
                self.wfile.flush()

            # 持续监听变化
            while True:
                try:
                    data = q.get(timeout=30)  # 30s 心跳
                    self.wfile.write(f'data: {data}\n\n'.encode('utf-8'))
                    self.wfile.flush()
                except queue.Empty:
                    # 发送心跳保持连接
                    self.wfile.write(': heartbeat\n\n'.encode('utf-8'))
                    self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            broadcaster.unregister_client(q)

    def _send_json_file(self, filename: str):
        """返回 JSON 文件内容"""
        filepath = os.path.join(BASE_DIR, filename)
        if not os.path.exists(filepath):
            self._send_json(404, {'error': 'file not found'})
            return
        with open(filepath, 'r', encoding='utf-8') as f:
            data = f.read()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Cache-Control', 'no-cache, no-store')
        self.end_headers()
        self.wfile.write(data.encode('utf-8'))

    def _send_json(self, status: int, data: dict):
        """发送 JSON 响应"""
        body = json.dumps(data, ensure_ascii=False)
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(body.encode('utf-8'))

    def log_message(self, format, *args):
        try:
            path_str = str(args[0]) if args else ''
            if '/events' not in path_str:
                print(f'[画布] {self.client_address[0]} - {format % args}')
        except Exception:
            pass


# ============ 启动 ============

if __name__ == '__main__':
    os.chdir(BASE_DIR)

    # 启动文件监控
    broadcaster.start_watching()

    print(f'🚀 画布服务器 v3.0 启动')
    print(f'   地址: http://localhost:{PORT}/')
    print(f'   静态文件: {DIST_DIR}')
    print(f'   SSE 端点: /events（实时推送 config 变化）')
    print(f'   POST /save-config   → config.json')
    print(f'   POST /save-feedback  → feedback.json')
    print(f'   GET  /get-state     返回 config.json')

    with socketserver.TCPServer(('127.0.0.1', PORT), CanvasHandler) as httpd:
        httpd.serve_forever()
