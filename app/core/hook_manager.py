# -*- coding: utf-8 -*-
"""
HookManager - Hooks 机制核心管理类
管理所有已注册的 Hooks，处理事件触发、匹配、异步执行
"""

import re
import subprocess
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Callable
from PyQt5.QtCore import QThreadPool, QRunnable, pyqtSignal, QObject
from loguru import logger


@dataclass
class Hook:
    """单个 Hook 配置"""
    type: str  # 目前只支持 "command"
    command: str
    cwd: Optional[str] = None
    add_output_to_context: bool = True
    skill_root: str = ""  # 所属技能根目录


@dataclass
class HookMatchRule:
    """匹配规则，一个事件可以有多个匹配规则"""
    matcher: Optional[str] = None  # 正则表达式
    hooks: List[Hook] = None
    
    def __post_init__(self):
        if self.hooks is None:
            self.hooks = []


class HookWorkerSignals(QObject):
    """Worker 信号，用于执行完后回调"""
    finished = pyqtSignal(str, bool)  # output, success


class HookWorker(QRunnable):
    """异步执行 Hook 的 Worker"""
    def __init__(self, command: str, cwd: Optional[str], signals: HookWorkerSignals):
        super().__init__()
        self.command = command
        self.cwd = cwd
        self.signals = signals
    
    def run(self):
        """执行命令，收集输出"""
        try:
            result = subprocess.run(
                self.command,
                cwd=self.cwd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300  # 5 分钟超时
            )
            output = result.stdout
            if result.stderr:
                logger.debug(f"[HookWorker] stderr: {result.stderr}")
            self.signals.finished.emit(output, result.returncode == 0)
        except Exception as e:
            logger.error(f"[HookWorker] Execution failed: {e}")
            self.signals.finished.emit(f"Error: {str(e)}", False)


class HookManager:
    """Hook 管理器"""
    
    def __init__(self, thread_pool: Optional[QThreadPool] = None):
        # {event_name: [HookMatchRule, ...]}
        self._hooks: Dict[str, List[HookMatchRule]] = {}
        # 记住每个 Hook 属于哪个技能，方便卸载时清理
        self._skill_to_hooks: Dict[str, List[tuple[str, int]]] = {}  # {skill_name: [(event_name, rule_index), ...]}
        
        # 线程池
        self._thread_pool = thread_pool or QThreadPool.globalInstance()
        
        # 完成回调
        self._on_finished_callback: Optional[Callable[[str, bool], None]] = None
    
    def set_on_finished_callback(self, callback: Callable[[str, bool], None]):
        """设置 Hook 执行完成回调，回调参数: (output, success)"""
        self._on_finished_callback = callback
    
    def register_hooks_from_json(
        self,
        skill_name: str,
        skill_root: str,
        json_data: Dict[str, Any]
    ) -> int:
        """从 JSON 配置注册 Hooks，返回注册的数量"""
        count = 0
        hooks_config = json_data.get("hooks", {})
        if not isinstance(hooks_config, dict):
            logger.warning(f"[HookManager] Invalid hooks config for skill {skill_name}")
            return 0
        
        for event_name, rules in hooks_config.items():
            if not isinstance(rules, list):
                rules = [rules]
            
            for rule in rules:
                match_rule = HookMatchRule(
                    matcher=rule.get("matcher"),
                    hooks=[]
                )
                
                for hook_config in rule.get("hooks", []):
                    hook = Hook(
                        type=hook_config.get("type", "command"),
                        command=hook_config.get("command", ""),
                        cwd=hook_config.get("cwd"),
                        add_output_to_context=hook_config.get("add_output_to_context", True),
                        skill_root=skill_root
                    )
                    if hook.command:
                        match_rule.hooks.append(hook)
                        count += 1
                
                if match_rule.hooks:
                    if event_name not in self._hooks:
                        self._hooks[event_name] = []
                    rule_index = len(self._hooks[event_name])
                    self._hooks[event_name].append(match_rule)
                    
                    if skill_name not in self._skill_to_hooks:
                        self._skill_to_hooks[skill_name] = []
                    self._skill_to_hooks[skill_name].append((event_name, rule_index))
        
        if count > 0:
            logger.info(f"[HookManager] Registered {count} hooks for skill {skill_name}")
        
        return count
    
    def unregister_skill_hooks(self, skill_name: str):
        """注销一个技能的所有 Hooks"""
        if skill_name not in self._skill_to_hooks:
            return
        
        for (event_name, rule_index) in reversed(self._skill_to_hooks[skill_name]):
            if event_name in self._hooks and rule_index < len(self._hooks[event_name]):
                self._hooks[event_name].pop(rule_index)
        
        del self._skill_to_hooks[skill_name]
        logger.debug(f"[HookManager] Unregistered all hooks for skill {skill_name}")
    
    def trigger_event(
        self,
        event_name: str,
        context: Dict[str, Any] = None,
        current_message: str = ""
    ):
        """触发事件，异步执行所有匹配的 Hooks"""
        if event_name not in self._hooks:
            return
        
        context = context or {}
        project_root = context.get("project_root", os.getcwd())
        
        for rule in self._hooks[event_name]:
            # 检查 matcher
            if rule.matcher:
                if not current_message:
                    continue  # 没有消息可匹配，跳过
                if not re.search(rule.matcher, current_message, re.IGNORECASE):
                    continue  # 不匹配，跳过
            
            # 执行这个规则下的所有 Hooks
            for hook in rule.hooks:
                self._execute_hook(hook, context, project_root)
    
    def _execute_hook(self, hook: Hook, context: Dict[str, Any], project_root: str):
        """替换变量并执行 Hook"""
        # 变量替换
        command = hook.command
        command = command.replace("{skill_root}", hook.skill_root)
        command = command.replace("{project_root}", project_root)
        
        # 替换上下文变量
        for key, value in context.items():
            if isinstance(value, str):
                command = command.replace(f"{{{key}}}", value)
        
        # 确定工作目录
        cwd = hook.cwd or project_root
        if cwd:
            cwd = cwd.replace("{skill_root}", hook.skill_root)
            cwd = cwd.replace("{project_root}", project_root)
            for key, value in context.items():
                if isinstance(value, str):
                    cwd = cwd.replace(f"{{{key}}}", value)
        
        # 创建信号和 worker
        signals = HookWorkerSignals()
        worker = HookWorker(command, cwd, signals)
        
        # 连接信号，如果需要添加输出到上下文
        if hook.add_output_to_context and self._on_finished_callback:
            signals.finished.connect(self._on_finished_callback)
        
        self._thread_pool.start(worker)
        logger.debug(f"[HookManager] Started hook: {command[:60]}...")
    
    def get_registered_events(self) -> List[str]:
        """获取所有已注册事件"""
        return list(self._hooks.keys())
