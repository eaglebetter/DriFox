# -*- coding: utf-8 -*-
"""
子智能体日志存储 - 使用 SQLite 持久化存储
"""

import orjson as json
from typing import Dict, List, Optional
from datetime import datetime

from app.utils.db_manager import DatabaseManager
from loguru import logger


class SubAgentLogStore:
    """子智能体日志存储管理器"""

    TABLE_NAME = "sub_agent_logs"

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def init(self, db_path: str):
        """初始化数据库连接"""
        if self._initialized:
            return
        try:
            self._db = DatabaseManager()
            self._db.connect(db_path)
            self._create_table()
            self._initialized = True
            logger.info(f"[SubAgentLogStore] 初始化完成: {db_path}")
        except Exception as e:
            logger.error(f"[SubAgentLogStore] 初始化失败: {e}")
            raise e

    def _create_table(self):
        """创建子智能体日志表"""
        columns = [
            {"name": "task_id", "type": "TEXT", "primary_key": True},
            {"name": "agent_name", "type": "TEXT"},
            {"name": "task_description", "type": "TEXT"},
            {"name": "status", "type": "TEXT"},  # running, finished, error
            {"name": "result", "type": "TEXT"},
            {"name": "error", "type": "TEXT"},
            {"name": "logs", "type": "TEXT"},  # JSON 存储
            {"name": "summary", "type": "TEXT"},  # JSON 存储摘要信息
            {"name": "created_at", "type": "TEXT"},
            {"name": "updated_at", "type": "TEXT"},
        ]
        self._db.create_table(self.TABLE_NAME, columns)

    def save_task(self, task_id: str, agent_name: str, task_description: str,
                  status: str = "running", result: str = None, error: str = None,
                  logs: List[Dict] = None, summary: Dict = None):
        """保存或更新任务"""
        now = datetime.now().isoformat()

        # 检查是否存在
        success, rows = self._db.execute_sql(
            f'SELECT 1 FROM "{self.TABLE_NAME}" WHERE task_id = ?', (task_id,)
        )

        if success and rows and len(rows) > 0:
            # 更新（只更新非 task_id 的字段）
            data = {
                "agent_name": agent_name or "",
                "task_description": task_description or "",
                "status": status,
                "result": result or "",
                "error": error or "",
                "logs": json.dumps(logs or []).decode('utf-8'),
                "summary": json.dumps(summary or {}).decode('utf-8'),
                "updated_at": now,
            }
            self._db.update_data(self.TABLE_NAME, data, "task_id = ?", (task_id,))
        else:
            # 插入
            data = {
                "task_id": task_id,
                "agent_name": agent_name or "",
                "task_description": task_description or "",
                "status": status,
                "result": result or "",
                "error": error or "",
                "logs": json.dumps(logs or []).decode('utf-8'),
                "summary": json.dumps(summary or {}).decode('utf-8'),
                "created_at": now,
                "updated_at": now,
            }
            self._db.insert_data(self.TABLE_NAME, data)

    def update_status(self, task_id: str, status: str, result: str = None,
                      error: str = None, logs: List[Dict] = None, summary: Dict = None):
        """更新任务状态"""
        now = datetime.now().isoformat()
        data = {
            "status": status,
            "updated_at": now,
        }
        if result is not None:
            data["result"] = result
        if error is not None:
            data["error"] = error
        if logs is not None:
            data["logs"] = json.dumps(logs).decode('utf-8')
        if summary is not None:
            data["summary"] = json.dumps(summary).decode('utf-8')

        self._db.update_data(self.TABLE_NAME, data, "task_id = ?", (task_id,))

    def get_task(self, task_id: str) -> Optional[Dict]:
        """获取单个任务"""
        success, rows = self._db.execute_sql(
            f'SELECT * FROM "{self.TABLE_NAME}" WHERE task_id = ?', (task_id,)
        )
        if success and rows and len(rows) > 0:
            row = rows[0]
            return {
                "task_id": row.get("task_id"),
                "agent_name": row.get("agent_name"),
                "task_description": row.get("task_description"),
                "status": row.get("status"),
                "result": row.get("result"),
                "error": row.get("error"),
                "logs": json.loads(row.get("logs", "[]")),
                "summary": json.loads(row.get("summary", "{}")),
                "created_at": row.get("created_at"),
                "updated_at": row.get("updated_at"),
            }
        return None

    def get_tasks(self, task_ids: List[str]) -> List[Dict]:
        """获取多个任务"""
        if not task_ids:
            return []
        placeholders = ",".join(["?"] * len(task_ids))
        sql = f'SELECT * FROM "{self.TABLE_NAME}" WHERE task_id IN ({placeholders})'
        success, rows = self._db.execute_sql(sql, tuple(task_ids))
        if success and rows:
            return [
                {
                    "task_id": row.get("task_id"),
                    "agent_name": row.get("agent_name"),
                    "task_description": row.get("task_description"),
                    "status": row.get("status"),
                    "result": row.get("result"),
                    "error": row.get("error"),
                    "logs": json.loads(row.get("logs", "[]")),
                    "summary": json.loads(row.get("summary", "{}")),
                    "created_at": row.get("created_at"),
                    "updated_at": row.get("updated_at"),
                }
                for row in rows
            ]
        return []

    def get_all_tasks(self, limit: int = 100) -> List[Dict]:
        """获取所有任务"""
        sql = f'SELECT * FROM "{self.TABLE_NAME}" ORDER BY created_at DESC LIMIT ?'
        success, rows = self._db.execute_sql(sql, (limit,))
        if success and rows:
            return [
                {
                    "task_id": row.get("task_id"),
                    "agent_name": row.get("agent_name"),
                    "task_description": row.get("task_description"),
                    "status": row.get("status"),
                    "result": row.get("result"),
                    "error": row.get("error"),
                    "logs": json.loads(row.get("logs", "[]")),
                    "summary": json.loads(row.get("summary", "{}")),
                    "created_at": row.get("created_at"),
                    "updated_at": row.get("updated_at"),
                }
                for row in rows
            ]
        return []

    def delete_task(self, task_id: str):
        """删除任务"""
        self._db.delete_data(self.TABLE_NAME, "task_id = ?", (task_id,))

    def clear_old_tasks(self, days: int = 7):
        """清理旧任务（默认保留7天）"""
        from datetime import timedelta
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        self._db.delete_data(self.TABLE_NAME, "updated_at < ?", (cutoff,))