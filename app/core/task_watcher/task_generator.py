# -*- coding: utf-8 -*-
"""
TaskWatcher 测试任务生成器
用于生成测试任务文件，方便测试系统功能
"""
import os
import uuid
from pathlib import Path
from typing import Optional, List
from loguru import logger
from .models import TaskConfig, TriggerMode, TaskType, OutputMode, SessionMode
class TaskGenerator:
    """测试任务生成器"""
    
    # 默认输出目录
    DEFAULT_OUTPUT_DIR = os.path.join(Path.home(), ".drifox", "tasks")
    
    def __init__(self, output_dir: Optional[str] = None):
        self._output_dir = output_dir or self.DEFAULT_OUTPUT_DIR
        os.makedirs(self._output_dir, exist_ok=True)
    
    def generate_simple_task(
        self,
        name: str = "简单测试任务",
        content: str = "请简单回复：你好，我是一个测试任务。",
        agent: str = "plan",
        priority: str = "normal"
    ) -> str:
        """生成简单测试任务
        
        Args:
            name: 任务名称
            content: 任务内容
            agent: 使用的 Agent
            priority: 优先级
            
        Returns:
            创建的文件路径
        """
        task_id = str(uuid.uuid4())
        
        task_content = f"""---
id: {task_id}
name: {name}
type: custom
trigger:
  mode: manual
context:
  session_mode: new
  agent: {agent}
output:
  mode: file
  destination: "{self._output_dir}/results/{task_id[:8]}_result.md"
  format: markdown
priority: {priority}
---
{content}
"""
        
        return self._write_task_file(name, task_content)
    
    def generate_research_task(
        self,
        topic: str = "人工智能最新进展",
        name: str = None,
        agent: str = "plan"
    ) -> str:
        """生成研究任务
        
        Args:
            topic: 研究主题
            name: 任务名称（可选，自动生成）
            agent: 使用的 Agent
            
        Returns:
            创建的文件路径
        """
        task_id = str(uuid.uuid4())
        task_name = name or f"研究: {topic[:20]}"
        
        task_content = f"""---
id: {task_id}
name: {task_name}
type: research
trigger:
  mode: manual
context:
  session_mode: new
  agent: {agent}
  reference_files: []
output:
  mode: file
  destination: "{self._output_dir}/results/{task_id[:8]}_research.md"
  format: markdown
priority: normal
---
## 研究任务
请帮我研究以下主题：{topic}
### 要求
1. 总结该主题的核心要点
2. 列出 3-5 个关键发现
3. 提供相关的应用场景
请以结构化的 Markdown 格式输出。
"""
        
        return self._write_task_file(task_name, task_content)
    
    def generate_code_review_task(
        self,
        code_snippet: str = "# 示例代码\ndef hello():\n    print('Hello, World!')\n\nhello()",
        language: str = "python",
        name: str = None,
        agent: str = "code-reviewer"
    ) -> str:
        """生成代码审查任务
        
        Args:
            code_snippet: 代码片段
            language: 编程语言
            name: 任务名称
            agent: 使用的 Agent
            
        Returns:
            创建的文件路径
        """
        task_id =  str(uuid.uuid4())
        task_name = name or f"代码审查: {language}"
        
        task_content = f"""---
id: {task_id}
name: {task_name}
type: code
trigger:
  mode: manual
context:
  session_mode: new
  agent: {agent}
output:
  mode: file
  destination: "{self._output_dir}/results/{task_id[:8]}_review.md"
  format: markdown
priority: high
---
## 代码审查任务
请审查以下 {language} 代码：
```{language}
{code_snippet}
```
### 审查要点
1. 代码质量和风格
2. 潜在的问题和错误
3. 性能优化建议
4. 安全漏洞检查
请以 Markdown 格式输出审查报告。
"""
        
        return self._write_task_file(task_name, task_content)
    
    def generate_daily_summary_task(
        self,
        date: str = None,
        agent: str = "plan"
    ) -> str:
        """生成每日总结任务
        
        Args:
            date: 日期（默认今天）
            agent: 使用的 Agent
            
        Returns:
            创建的文件路径
        """
        from datetime import datetime
        task_id = str(uuid.uuid4())
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        task_name = f"每日总结 {date}"
        
        task_content = f"""---
id: {task_id}
name: {task_name}
type: analyze
trigger:
  mode: scheduled
  cron: "0 21 * * *"
context:
  session_mode: new
  agent: {agent}
output:
  mode: file
  destination: "{self._output_dir}/daily/{date}_summary.md"
  format: markdown
priority: normal
---
## 每日总结任务
请帮我总结今天的重要进展和待办事项。

输出要求：
1. 已完成工作要点
2. 待办事项
3. 需要关注的风险
4. 明日计划建议

请以清晰的 Markdown 列表输出。
"""
        return self._write_task_file(task_name, task_content)
    
    def generate_cron_task(
        self,
        cron_expr: str,
        name: str,
        content: str,
        agent: str = "plan",
        output_path: str = None,
    ) -> str:
        """生成定时任务
        
        Args:
            cron_expr: cron 表达式
            name: 任务名称
            content: 任务内容
            agent: 使用的 Agent
            output_path: 输出路径
            
        Returns:
            创建的文件路径
        """
        task_id = str(uuid.uuid4())
        
        if not output_path:
            output_path = f"{self._output_dir}/results/{task_id[:8]}_result.md"
        
        task_content = f"""---
id: {task_id}
name: {name}
type: custom
trigger:
  mode: scheduled
  cron: "{cron_expr}"
context:
  session_mode: new
  agent: {agent}
output:
  mode: file
  destination: "{output_path}"
  format: markdown
priority: normal
---
{content}
"""
        return self._write_task_file(name, task_content)
    
    def generate_file_watch_task(
        self,
        watch_folder: str,
        name: str = "文件变化处理",
        content: str = "检测到新文件，请处理并总结",
        agent: str = "plan",
        file_pattern: str = "*.md",
    ) -> str:
        """生成文件监听任务
        
        Args:
            watch_folder: 监听文件夹
            name: 任务名称
            content: 处理内容
            agent: 使用的 Agent
            file_pattern: 文件匹配模式
            
        Returns:
            创建的文件路径
        """
        task_id = str(uuid.uuid4())
        
        task_content = f"""---
id: {task_id}
name: {name}
type: custom
trigger:
  mode: file_change
  watch_folder: "{watch_folder}"
  file_pattern: "{file_pattern}"
context:
  session_mode: new
  agent: {agent}
output:
  mode: file
  destination: "{self._output_dir}/results/{task_id[:8]}_processed.md"
  format: markdown
priority: high
---
{content}
"""
        return self._write_task_file(name, task_content)
    
    def generate_bulk_tasks(self, count: int = 3, task_type: str = "simple") -> List[str]:
        """批量生成测试任务
        
        Args:
            count: 数量
            task_type: 任务类型
            
        Returns:
            文件路径列表
        """
        import random
        files = []
        
        # 预设样本
        codes = [
                ("快速排序", "python", "def quicksort(arr):\n    if len(arr) <= 1:\n        return arr\n    pivot = arr[len(arr) // 2]\n    left = [x for x in arr if x < pivot]\n    middle = [x for x in arr if x == pivot]\n    right = [x for x in arr if x > pivot]\n    return quicksort(left) + middle + quicksort(right)"),
                ("数据库连接", "python", "import sqlite3\n\ndef create_table():\n    conn = sqlite3.connect('example.db')\n    cursor = conn.cursor()\n    cursor.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT)''')\n    conn.commit()\n    conn.close()"),
            ]
                codes = [
                ("快速排序", "python", "def quicksort(arr):\n    if len(arr) <= 1:\n        return arr\n    pivot = arr[len(arr) // 2]\n    left = [x for x in arr if x < pivot]\n    middle = [x for x in arr if x == pivot]\n    right = [x for x in arr if x > pivot]\n    return quicksort(left) + middle + quicksort(right)"),
                ("数据库连接", "python", "import sqlite3\n\ndef create_table():\n    conn = sqlite3.connect('example.db')\n    cursor = conn.cursor()\n    cursor.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT)''')\n    conn.commit()\n    conn.close()"),
                ]
        
        for i in range(count):
            if task_type == "code_review":
                code_name, code_lang, code = codes[i % len(codes)]
                filepath = self.generate_code_review_task(
                    code_snippet=code,
                    language=code_lang,
                    name=f"代码审查 {code_name}"
                )
            else:
                filepath = self.generate_simple_task(
                    name=f"测试任务 #{i + 1}",
                    content=f"批量测试任务 #{i + 1}"
                )
            
            files.append(filepath)
        
        logger.info(f"[TaskGenerator] 批量生成了 {count} 个测试任务")
        return files
    
    def _write_task_file(self, name: str, content: str) -> str:
        """写入任务文件
        
        Args:
            name: 任务名称
            content: 任务内容
            
        Returns:
            文件路径
        """
        # 生成安全的文件名
        safe_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in name)[:30]
        filename = f"{safe_name}_{uuid.uuid4().hex[:8]}.task.md"
        filepath = os.path.join(self._output_dir, filename)
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        
        logger.info(f"[TaskGenerator] 生成任务文件: {filepath}")
        return filepath
# 便捷函数
def generate_test_tasks(count: int = 3, task_type: str = "simple") -> List[str]:
    """生成测试任务
    
    Args:
        count: 数量
        task_type: 类型
        
    Returns:
        文件路径列表
    """
    generator = TaskGenerator()
    return generator.generate_bulk_tasks(count, task_type)
def generate_and_add_to_system(system, count: int = 3, task_type: str = "simple") -> List[str]:
    """生成测试任务并添加到系统
    
    Args:
        system: TaskWatcherSystem 实例
        count: 数量
        task_type: 类型
        
    Returns:
        TaskConfig 列表
    """
    files = generate_test_tasks(count, task_type)
    configs = []
    
    for filepath in files:
        config = system.parse_and_enqueue(filepath)
        if config:
            configs.append(config)
    
    return configs