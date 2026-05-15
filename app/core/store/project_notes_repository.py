# -*- coding: utf-8 -*-
"""
项目笔记仓储模块 - 专门负责项目 Markdown 内容的持久化
"""

from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
import hashlib

from loguru import logger


class ProjectNotesRepository:
    """项目笔记数据仓储"""

    TABLE_NAME = "project_notes"
    DB_FILENAME = "sessions.db"

    def __init__(self, db_manager):
        self._db = db_manager

    @property
    def is_initialized(self) -> bool:
        return self._db is not None and self._db.is_connected

    def _execute(self, sql: str, params: tuple = ()) -> Tuple[bool, Any]:
        """执行 SQL（内部使用）"""
        if not self._db:
            return False, "数据库未初始化"
        return self._db.execute_sql(sql, params)

    def _ensure_table(self) -> bool:
        """确保表存在"""
        if not self.is_initialized:
            return False
        try:
            success, _ = self._execute(f'''
                CREATE TABLE IF NOT EXISTS {self.TABLE_NAME} (
                    id TEXT PRIMARY KEY,
                    project TEXT UNIQUE NOT NULL,
                    content TEXT DEFAULT '',
                    updated_at TEXT
                )
            ''')
            return success
        except Exception as e:
            logger.error(f"[ProjectNotesRepository] 创建表失败: {e}")
            return False

    def save(self, project: str, content: str = "") -> bool:
        """
        保存或更新项目笔记
        
        Args:
            project: 项目名称
            content: Markdown 内容
        
        Returns:
            bool: 保存是否成功
        """
        if not self._ensure_table():
            return False
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 检查是否存在
        success, rows = self._execute(
            f'SELECT id FROM {self.TABLE_NAME} WHERE project = ?',
            (project,)
        )
        
        if success and rows and len(rows) > 0:
            # 更新
            success, _ = self._execute(
                f'UPDATE {self.TABLE_NAME} SET content = ?, updated_at = ? WHERE project = ?',
                (content, now, project)
            )
        else:
            # 新增
            note_id = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{hashlib.md5(project.encode()).hexdigest()[:8]}"
            success, _ = self._execute(f'''
                INSERT INTO {self.TABLE_NAME} (id, project, content, updated_at)
                VALUES (?, ?, ?, ?)
            ''', (note_id, project, content, now))
        
        return success

    def get(self, project: str) -> Optional[Dict]:
        """
        获取指定项目的笔记
        
        Args:
            project: 项目名称
        
        Returns:
            Optional[Dict]: 笔记数据，不存在返回 None
        """
        if not self.is_initialized:
            return None
        
        try:
            success, rows = self._execute(
                f'SELECT * FROM {self.TABLE_NAME} WHERE project = ?',
                (project,)
            )
            if success and rows and len(rows) > 0:
                row = rows[0]
                d = {k: row[k] for k in row.keys()} if hasattr(row, 'keys') else dict(row)
                return {
                    "id": d.get("id", ""),
                    "project": d.get("project", ""),
                    "content": d.get("content", ""),
                    "updated_at": d.get("updated_at", ""),
                }
            return None
        except Exception as e:
            logger.error(f"[ProjectNotesRepository] get 异常: {e}")
            return None

    def get_or_create(self, project: str) -> Dict:
        """
        获取或创建项目笔记
        
        Args:
            project: 项目名称
        
        Returns:
            Dict: 笔记数据
        """
        note = self.get(project)
        if note is None:
            # 新建项目时自动填入初始开发规范模板
            initial_content = """# 项目开发规范

本文件为 AI Agent 提供项目操作手册与约束清单，确保 Agent 行为可控、可复现。

---

## 1. 目标与边界

### 允许的操作
- **有关键文档存在时，优先以关键文档作为项目路径进行探索**
- 读取、修改顶层文档：`README.md`、`AGENTS.md`、`CONTRIBUTING.md` 等
- 读取、修改 `docs/`、`prompts/`、`skills/`、`tools/config/`、`tools/external/` 下的文档与代码
- 执行项目规定的 lint、检查、构建命令
- 新增/修改功能、修复问题
- 提交符合规范的 commit

### 禁止的操作
- 修改 `.github/workflows/` 中的 CI 配置（除非任务明确要求）
- 修改 `LICENSE`、`CODE_OF_CONDUCT.md`
- 在代码中硬编码密钥、Token 或敏感凭证
- 未经确认的大范围重构

### 敏感区域（禁止自动修改）
- `.github/workflows/*.yml` - CI/CD 配置
- `.env*` 文件（如存在）

---

## 2. 推荐执行路径

```bash
# 1. 拉取最新代码
git pull --rebase origin develop

# 2. 初始化依赖（如有需要）
# ... 项目特有命令

# 3. 运行 lint 检查
# ... 项目特有命令

# 4. 执行修改任务
# ...

# 5. 再次验证
# ... 项目特有检查命令

# 6. 提交变更
git add -A
git commit -m "feat|fix|docs|chore: scope - summary"
git push origin develop
```

---

## 3. 修改约束

### 架构原则
- 保持根目录扁平，避免巨石文件
- 遵循项目现有架构，不随意改动

### 禁止行为
- 禁止"顺手重构/大范围改动"除非任务明确要求
- 禁止删除现有测试用例（除非任务要求）
- 禁止在代码中硬编码敏感信息

---

## 4. 风格与质量标准

### 格式化工具
- 遵循项目现有代码风格
- 使用项目已有的格式化工具

### 命名约定
- 文档、注释、日志使用中文
- 代码符号统一英文且语义直白
- 文件名小写加中划线或下划线（遵循现有风格）

### 设计品味
- 优先消除分支与重复
- 函数单一职责且短小

---

## 5. 提交规范

遵循简化 Conventional Commits：
```
feat|fix|docs|chore|refactor|test: scope - summary
```

---

## 6. 强制同步规则

**任何功能/命令/配置/目录/工作流变化必须同步更新相关文档**

不确定的内容用 TODO 标注，不允许猜测。
"""
            self.save(project, initial_content)
            return self.get(project) or {
                "id": "",
                "project": project,
                "content": initial_content,
                "updated_at": "",
            }
        return note

    def get_all_projects(self) -> List[str]:
        """
        获取所有有笔记的项目
        
        Returns:
            List[str]: 项目名称列表
        """
        if not self.is_initialized:
            return []
        
        try:
            success, rows = self._execute(
                f'SELECT DISTINCT project FROM {self.TABLE_NAME} ORDER BY updated_at DESC'
            )
            if success and rows:
                return [row[0] if isinstance(row, tuple) else row.get("project", "") for row in rows]
            return []
        except Exception as e:
            logger.error(f"[ProjectNotesRepository] get_all_projects 异常: {e}")
            return []

    def delete(self, project: str) -> bool:
        """
        删除项目笔记
        
        Args:
            project: 项目名称
        
        Returns:
            bool: 删除是否成功
        """
        if not self.is_initialized:
            return False
        
        try:
            success, _ = self._execute(
                f'DELETE FROM {self.TABLE_NAME} WHERE project = ?',
                (project,)
            )
            return success
        except Exception as e:
            logger.error(f"[ProjectNotesRepository] delete 异常: {e}")
            return False