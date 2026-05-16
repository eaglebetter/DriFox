# -*- coding: utf-8 -*-
"""
Workers 模块 - 包含各种执行器和任务类
"""

from app.core.workers.chat_worker import OpenAIChatWorker
from app.core.workers.subagent_worker import SubAgentExecutor, SubAgentManager
from app.core.workers.topic_summary import TopicSummaryTask
from app.core.workers.shell_task import ShellExecutionTask
from app.core.workers.auto_loop_worker import AutoLoopWorker

__all__ = [
    # Workers
    "OpenAIChatWorker",
    "SubAgentExecutor",
    "SubAgentManager",
    "AutoLoopWorker",
    # Tasks
    "TopicSummaryTask",
    "ShellExecutionTask",
]
