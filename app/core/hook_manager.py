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
    matcher: Optional[str] = None  # 支持 "tool:xxx" 前缀匹配工具名，或普通正则匹配用户消息
    hooks: List[Hook] = None
    
    def __post_init__(self):
        if self.hooks is None:
            self.hooks = []


class HookWorkerSignals(QObject):
    """Worker 信号，用于执行完后回调"""
    finished = pyqtSignal(str, str, bool)  # event_name, output, success


class HookWorker(QRunnable):
    """异步执行 Hook 的 Worker"""
    def __init__(self, command: str, cwd: Optional[str], signals: HookWorkerSignals, event_name: str = ""):
        super().__init__()
        self.command = command
        self.cwd = cwd
        self.signals = signals
        self.event_name = event_name
    
    def run(self):
        """执行命令，收集输出"""
        try:
            output = ""
            # 直接在 Python 中执行，避免 Windows cmd 的编码问题
            if self.command.startswith("echo "):
                # echo 命令直接输出，不需要 shell
                output = self.command[5:].strip()
                # 去掉首尾的引号（如果有）
                if output.startswith('"') and output.endswith('"'):
                    output = output[1:-1]
                elif output.startswith("'") and output.endswith("'"):
                    output = output[1:-1]
            else:
                # 其他命令用 shell 执行
                result = subprocess.run(
                    self.command,
                    cwd=self.cwd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    timeout=300
                )
                
                # 检查命令是否成功执行
                if result.returncode != 0:
                    output = result.stderr or f"Command failed with exit code {result.returncode}"
                    success = False
                else:
                    output = result.stdout or ""
                    success = True
            
            self.signals.finished.emit(self.event_name, output, success)
        except Exception as e:
            logger.error(f"[HookWorker] Execution failed: {e}")
            self.signals.finished.emit(self.event_name, f"Error: {str(e)}", False)


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
        tool_name = context.get("tool_name", "")
        
        for rule in self._hooks[event_name]:
            if not rule.matcher:
                pass
            elif rule.matcher.startswith("tool:"):
                tool_pattern = rule.matcher[5:]
                if not tool_name or not re.search(tool_pattern, tool_name, re.IGNORECASE):
                    continue
            elif current_message and re.search(rule.matcher, current_message, re.IGNORECASE):
                # 普通 matcher 匹配用户消息
                pass
            else:
                # 用户消息不匹配
                continue
            
            for hook in rule.hooks:
                context_with_event = context.copy()
                context_with_event["_event_name"] = event_name
                self._execute_hook(hook, context_with_event, project_root)
    
    def _parse_command(self, command: str) -> Optional[List[str]]:
        """解析命令字符串，返回 [cmd, arg1, arg2, ...] 或 None（解析失败）"""
        parts = []
        current = ""
        in_quote = False
        quote_char = None
        
        for char in command:
            if char in ('"', "'") and not in_quote:
                in_quote = True
                quote_char = char
            elif char == quote_char and in_quote:
                in_quote = False
                quote_char = None
            elif char == ' ' and not in_quote:
                if current:
                    parts.append(current)
                    current = ""
            else:
                current += char
        
        if current:
            parts.append(current)
        
        if not parts:
            return None
        
        # 去掉首尾引号
        cmd = parts[0]
        if cmd.startswith('"') and cmd.endswith('"'):
            cmd = cmd[1:-1]
        elif cmd.startswith("'") and cmd.endswith("'"):
            cmd = cmd[1:-1]
        
        return [cmd] + parts[1:]

    def _execute_hook(self, hook: Hook, context: Dict[str, Any], project_root: str):
        """替换变量并执行 Hook"""
        event_name = context.get("_event_name", "")
        
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
        
        # 判断是否需要同步执行
        event_name = context.get("_event_name", "")
        need_sync = event_name.startswith("Pre") or event_name == "SessionStart"
        
        if need_sync:
            # 同步执行
            try:
                # 对于 echo 命令，直接用 shell=True 执行（Windows 下 echo 是内置命令）
                if command.strip().startswith("echo "):
                    output = command.strip()[5:].strip()
                    # 去掉首尾的引号
                    if output.startswith('"') and output.endswith('"'):
                        output = output[1:-1]
                    elif output.startswith("'") and output.endswith("'"):
                        output = output[1:-1]
                    if hook.add_output_to_context and self._on_finished_callback:
                        self._on_finished_callback(event_name, output, True)
                    logger.info(f"[HookManager] Hook executed: {event_name}")
                    return
                
                parts = self._parse_command(command)
                if not parts:
                    return

                cmd = parts[0]
                args = parts[1:]

                if not os.path.isabs(cmd):
                    cmd_abs = os.path.normpath(os.path.join(cwd, cmd))
                    cmd = cmd_abs

                if cmd.lower().endswith('.cmd'):
                    result = subprocess.run(
                        ['cmd.exe', '/c', cmd] + args,
                        cwd=cwd,
                        shell=False,
                        capture_output=True,
                        text=True,
                        encoding='utf-8',
                        errors='replace',
                        timeout=300
                    )
                else:
                    # 使用 shell=True 执行其他命令（确保 Windows 内置命令可用）
                    result = subprocess.run(
                        command,
                        cwd=cwd,
                        shell=True,
                        capture_output=True,
                        text=True,
                        encoding='utf-8',
                        errors='replace',
                        timeout=300
                    )

                # 检查命令是否成功执行
                if result.returncode != 0:
                    output = result.stderr or f"Command failed with exit code {result.returncode}"
                    success = False
                else:
                    output = result.stdout or ""
                    success = True
                
                if hook.add_output_to_context and self._on_finished_callback:
                    self._on_finished_callback(event_name, output, success)
                logger.info(f"[HookManager] Hook executed: {event_name}")
                if not success:
                    logger.error(f"[HookManager] Hook failed: {event_name} - {output}")
            except Exception as e:
                logger.error(f"[HookManager] Hook failed: {event_name} - {e}")
                if hook.add_output_to_context and self._on_finished_callback:
                    self._on_finished_callback(event_name, f"Error: {str(e)}", False)
        else:
            signals = HookWorkerSignals()
            worker = HookWorker(command, cwd, signals, event_name)
            if hook.add_output_to_context and self._on_finished_callback:
                signals.finished.connect(self._on_finished_callback)
            self._thread_pool.start(worker)
            logger.info(f"[HookManager] Hook triggered (async): {event_name}")
    
    def get_registered_events(self) -> List[str]:
        """获取所有已注册事件"""
        return list(self._hooks.keys())
