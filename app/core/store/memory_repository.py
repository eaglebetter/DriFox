# -*- coding: utf-8 -*-
"""
记忆仓储模块 - 专门负责长期记忆的持久化

从 SessionStore 中提取的记忆 CRUD 逻辑。
"""

import orjson as json
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

from loguru import logger


class MemoryRepository:
    """长期记忆数据仓储，处理记忆的 CRUD 操作"""

    TABLE_NAME = "memories"
    DB_FILENAME = "sessions.db"

    def __init__(self, db_manager):
        """
        Args:
            db_manager: DatabaseManager 实例
        """
        self._db = db_manager

    @property
    def is_initialized(self) -> bool:
        return self._db is not None and self._db.is_connected

    def _execute(self, sql: str, params: tuple = ()) -> Tuple[bool, Any]:
        """执行 SQL（内部使用）"""
        if not self._db:
            return False, "数据库未初始化"
        return self._db.execute_sql(sql, params)

    def _row_to_memory(self, row) -> Dict:
        """将数据库行转换为记忆字典"""
        if not row:
            return {}

        if hasattr(row, 'keys'):
            d = {k: row[k] for k in row.keys()}
        elif isinstance(row, dict):
            d = dict(row)
        else:
            return {}

        return {
            "memory_id": d.get("memory_id", ""),
            "content": d.get("content", ""),
            "enabled": bool(d.get("enabled", 1)),
            "confidence": float(d.get("confidence", 0.8)),
            "category": d.get("category", "task_preference"),
            "source": d.get("source", ""),
            "last_accessed": d.get("last_accessed", ""),
            "created_at": d.get("created_at", ""),
            "updated_at": d.get("updated_at", ""),
        }

    def save(self, memory: Dict) -> bool:
        """
        保存单条长期记忆

        Args:
            memory: 记忆数据，包含 content, category, confidence, source 等

        Returns:
            bool: 保存是否成功
        """
        if not self.is_initialized:
            return False

        # 生成唯一的 memory_id
        existing_id = memory.get("memory_id") or memory.get("id")
        if existing_id:
            memory_id = str(existing_id)
        else:
            # 使用 content hash + timestamp 确保唯一性
            import hashlib
            content_hash = hashlib.md5(str(memory.get("content", "")).encode()).hexdigest()[:8]
            memory_id = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{content_hash}"

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        success, _ = self._execute(f'''
            INSERT OR REPLACE INTO {self.TABLE_NAME}
            (memory_id, content, enabled, confidence, category, source,
             last_accessed, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            memory_id,
            memory.get("content", ""),
            1 if memory.get("enabled", True) else 0,
            memory.get("confidence", 0.8),
            memory.get("category", "key_knowledge"),
            memory.get("source", ""),
            now,
            memory.get("created_at") or now,
            now,
        ))

        return success

    def save_all(self, memories: List[Dict]) -> bool:
        """
        批量保存记忆（全量替换，先清空再插入）

        Args:
            memories: 记忆列表

        Returns:
            bool: 是否成功
        """
        if not self.is_initialized or not self._db:
            return False

        # 使用原生连接，避免 DatabaseManager 自动 commit 破坏事务
        try:
            conn = self._db._conn
            cursor = conn.cursor()

            # 清空现有记忆
            cursor.execute(f"DELETE FROM {self.TABLE_NAME}")

            # 批量插入
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for memory in memories:
                existing_id = memory.get("memory_id") or memory.get("id")
                if existing_id:
                    memory_id = str(existing_id)
                else:
                    import hashlib
                    content_hash = hashlib.md5(str(memory.get("content", "")).encode()).hexdigest()[:8]
                    memory_id = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{content_hash}"

                cursor.execute(f'''
                    INSERT INTO {self.TABLE_NAME}
                    (memory_id, content, enabled, confidence, category, source,
                     last_accessed, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    memory_id,
                    memory.get("content", ""),
                    1 if memory.get("enabled", True) else 0,
                    memory.get("confidence", 0.8),
                    memory.get("category", "key_knowledge"),
                    memory.get("source", ""),
                    now,
                    memory.get("created_at") or now,
                    now,
                ))

            conn.commit()
            logger.info(f"[MemoryRepository] 已保存 {len(memories)} 条记忆")
            return True

        except Exception as e:
            logger.error(f"[MemoryRepository] save_memories 异常: {e}")
            if self._db and self._db._conn:
                self._db._conn.rollback()
            return False

    def load_all(self, limit: int = 200, include_disabled: bool = False) -> List[Dict]:
        """
        加载所有记忆

        Args:
            limit: 最大返回数量
            include_disabled: 是否包含已禁用的记忆

        Returns:
            List[Dict]: 记忆列表
        """
        if not self.is_initialized:
            return []

        try:
            if include_disabled:
                sql = f'SELECT * FROM {self.TABLE_NAME} ORDER BY updated_at DESC LIMIT ?'
                params = (limit,)
            else:
                sql = f'SELECT * FROM {self.TABLE_NAME} WHERE enabled = 1 ORDER BY updated_at DESC LIMIT ?'
                params = (limit,)

            success, rows = self._execute(sql, params)
            if success:
                return [self._row_to_memory(row) for row in rows]
            return []
        except Exception as e:
            logger.error(f"[MemoryRepository] load_memories 异常: {e}")
            return []

    def delete(self, memory_id: str) -> bool:
        """删除指定记忆"""
        if not self.is_initialized:
            return False

        try:
            success, _ = self._execute(
                f'DELETE FROM {self.TABLE_NAME} WHERE memory_id = ?',
                (memory_id,)
            )
            return success
        except Exception as e:
            logger.error(f"[MemoryRepository] delete_memory 异常: {e}")
            return False

    def delete_by_category(self, category: str) -> int:
        """删除指定分类的所有记忆"""
        if not self.is_initialized:
            return 0

        try:
            success, result = self._execute(
                f'DELETE FROM {self.TABLE_NAME} WHERE category = ?',
                (category,)
            )
            if success and result:
                return result[0] if isinstance(result[0], tuple) else result
            return 0
        except Exception as e:
            logger.error(f"[MemoryRepository] delete_memories_by_category 异常: {e}")
            return 0

    def clear_all(self) -> bool:
        """清空所有记忆"""
        if not self.is_initialized:
            return False

        try:
            success, _ = self._execute(f'DELETE FROM {self.TABLE_NAME}')
            return success
        except Exception as e:
            logger.error(f"[MemoryRepository] clear_memories 异常: {e}")
            return False

    def update_enabled(self, memory_id: str, enabled: bool) -> bool:
        """更新记忆的启用状态"""
        if not self.is_initialized:
            return False

        try:
            success, _ = self._execute(
                f'UPDATE {self.TABLE_NAME} SET enabled = ?, updated_at = ? WHERE memory_id = ?',
                (1 if enabled else 0, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), memory_id)
            )
            return success
        except Exception as e:
            logger.error(f"[MemoryRepository] update_memory_enabled 异常: {e}")
            return False

    def update_last_accessed(self, memory_id: str) -> bool:
        """更新记忆的最后访问时间"""
        if not self.is_initialized:
            return False

        try:
            success, _ = self._execute(
                f'UPDATE {self.TABLE_NAME} SET last_accessed = ? WHERE memory_id = ?',
                (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), memory_id)
            )
            return success
        except Exception as e:
            logger.error(f"[MemoryRepository] update_last_accessed 异常: {e}")
            return False

    def search(self, query_terms: List[str], limit: int = 20) -> List[Dict]:
        """
        搜索记忆

        Args:
            query_terms: 搜索关键词列表
            limit: 最大返回数量

        Returns:
            List[Dict]: 匹配的记忆列表
        """
        if not self.is_initialized:
            return []

        try:
            success, rows = self._execute(
                f'SELECT * FROM {self.TABLE_NAME} ORDER BY confidence DESC LIMIT ?',
                (limit * 2,)
            )
            if not success:
                return []

            results = []
            for row in rows:
                memory = self._row_to_memory(row)
                content_key = str(memory.get("content", "")).lower()
                if query_terms and not all(term.lower() in content_key for term in query_terms):
                    continue
                results.append(memory)

            return results[:limit]

        except Exception as e:
            logger.error(f"[MemoryRepository] search_memories 异常: {e}")
            return []