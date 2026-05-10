from pathlib import Path
from typing import Dict, List

from PyQt5.QtCore import QObject, pyqtSignal
from loguru import logger

from app.tools.diagnostics_tools import (
    DiagnosticsTools,
)
from app.tools.file_tools import FileTools
from app.tools.result import ToolResult
from app.tools.task_tools import TaskTools
from app.tools.terminal_tools import (
    TerminalTools,
)
from app.tools.web_tools import WebTools


class BuiltinTools(QObject):
    """内置工具集，整合所有工具模块"""

    fileModified = pyqtSignal(str)

    def __init__(self, homepage=None, workdir: str = None):
        super().__init__(homepage)
        self.homepage = homepage

        if workdir:
            self.workdir = Path(workdir)
        else:
            try:
                from app.utils.utils import resource_path

                self.workdir = Path(resource_path("/"))
            except Exception:
                self.workdir = Path.cwd()

        self._file_tools = FileTools(self.workdir)
        self._web_tools = WebTools(self.workdir)
        self._terminal_tools = TerminalTools(self.workdir)
        self._task_tools = TaskTools(self.workdir)
        self._diagnostics_tools = DiagnosticsTools(self.workdir)

        self._todo_list = []
        self._loaded_skills = {}
        self._skill_workspaces = {}
        self._sub_agent_manager = None
        self._agent_manager = None  # AgentManager 实例，用于动态生成工具 schema
        self._set_stage_callback = None
        self._memory_manager = None
        self._get_llm_config = None
        self._get_session_messages = None

        logger.info(f"[BuiltinTools] Workdir: {self.workdir}")

    @property
    def file_tools(self):
        return self._file_tools

    @property
    def web_tools(self):
        return self._web_tools

    @property
    def terminal_tools(self):
        return self._terminal_tools

    @property
    def task_tools(self):
        return self._task_tools

    def get_todos(self):
        """获取待办事项列表（返回副本，防止外部直接修改内部状态）"""
        return list(self._task_tools._todo_list)

    @property
    def diagnostics_tools(self):
        return self._diagnostics_tools

    def read_file(self, path: str, offset: int = 1, limit: int = 2000, show_line_numbers: bool = False):
        return self._file_tools.read_file(path, offset, limit, show_line_numbers)

    def write_file(self, path: str, content: str):
        result = self._file_tools.write_file(path, content)
        if result.success:
            resolved_path = self._file_tools._resolve_path(path)
            logger.info(
                f"[BuiltinTools] write_file success, emitting fileModified: {resolved_path}"
            )
            self.fileModified.emit(str(resolved_path))
        return result

    def edit_file(
            self, path: str, oldString: str, newString: str, replaceAll: bool = False
    ):
        result = self._file_tools.edit_file(path, oldString, newString, replaceAll)
        if result.success:
            resolved_path = self._file_tools._resolve_path(path)
            logger.info(
                f"[BuiltinTools] edit_file success, emitting fileModified: {resolved_path}"
            )
            self.fileModified.emit(str(resolved_path))
        return result

    def grep_files(self, pattern: str, path: str = None, include: str = None):
        return self._file_tools.grep_files(pattern, path, include)

    def glob_files(self, pattern: str, path: str = None):
        return self._file_tools.glob_files(pattern, path)

    def list_directory(self, path: str = None):
        return self._file_tools.list_directory(path)

    def apply_patch(self, path: str, patch_content: str):
        result = self._file_tools.apply_patch(path, patch_content)
        if result.success:
            resolved_path = self._file_tools._resolve_path(path)
            logger.info(
                f"[BuiltinTools] apply_patch success, emitting fileModified: {resolved_path}"
            )
            self.fileModified.emit(str(resolved_path))
        return result

    def diff_files(self, file1: str, file2: str = None, use_git: bool = False):
        return self._file_tools.diff_files(file1, file2, use_git)

    def multi_edit(self, path: str, edits: List[Dict]):
        result = self._file_tools.multi_edit(path, edits)
        if result.success:
            resolved_path = self._file_tools._resolve_path(path)
            logger.info(
                f"[BuiltinTools] multi_edit success, emitting fileModified: {resolved_path}"
            )
            self.fileModified.emit(str(resolved_path))
        return result

    def execute_bash(self, command: str, timeout: int = 120, ):
        return self._terminal_tools.execute_bash(command, timeout)

    def fetch_web(self, url: str, format: str = "markdown", max_chars: int = 26000, callback=None,
                  cancelled_ref: list = None):
        return self._web_tools.fetch_web(url, format, max_chars, callback, cancelled_ref)

    def search_web(self, query: str, num_results: int = 10, callback=None, cancelled_ref: list = None):
        return self._web_tools.search_web(query, num_results, callback, cancelled_ref)

    def todo_write(self, todos: List[Dict]):
        result = self._task_tools.todo_write(todos)
        self._todo_list = list(self._task_tools._todo_list)
        return result

    def todo_clear(self):
        self._task_tools.todo_clear()
        self._todo_list = []

    def reset_session_state(self):
        """Reset session-scoped state when switching sessions"""
        self._todo_list = []
        self._task_tools.reset_session_state()

    def cleanup(self):
        """
        彻底清理 BuiltinTools 的所有缓存，防止内存泄漏。
        应该在对话结束后或切换会话时调用。
        """
        # 清理待办事项
        self._todo_list = []
        if hasattr(self._task_tools, 'cleanup'):
            self._task_tools.cleanup()

        # 清理加载的技能
        self._loaded_skills = {}
        self._skill_workspaces = {}

        # 清理子智能体管理器
        self._sub_agent_manager = None

        # 清理文件工具的缓存
        if hasattr(self._file_tools, 'cleanup'):
            self._file_tools.cleanup()

    def todo_read(self):
        return self._task_tools.todo_read()

    def task_execute_batch(self, tasks: List[Dict], share_context: bool = False):
        return self._task_tools.task_execute_batch(tasks, share_context)

    def task_status(self, task_ids: str = None, with_log: bool = False, with_result: bool = True):
        return self._task_tools.task_status(task_ids, with_log, with_result)

    def load_skill(self, name: str):
        return self._task_tools.load_skill(name)

    def list_skills(self):
        return self._task_tools.list_skills()

    def scan_repo(self, path: str = None, max_depth: int = 2):
        return self._task_tools.scan_repo(path, max_depth)

    def stage_files(self, files: List[str]):
        return self._task_tools.stage_files(files)

    def ask_question(
            self, question: str, options: List[str] = None, multiple: bool = False
    ):
        return self._task_tools.ask_question(question, options, multiple)

    def get_diagnostics(self, file_path: str, language: str = None):
        return self._diagnostics_tools.get_diagnostics(file_path, language)

    def summarize_changes(self, text: str = "", limit: int = 1200) -> ToolResult:
        text = (text or "").strip()
        if not text:
            return ToolResult(False, error="No text provided for summarization")

        clean_lines = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if clean_lines and clean_lines[-1] == stripped:
                continue
            clean_lines.append(stripped)

        summary = "\n".join(clean_lines)
        if len(summary) > limit:
            head = summary[: int(limit * 0.75)].rstrip()
            tail = summary[-int(limit * 0.15):].lstrip()
            summary = f"{head}\n\n[... 已省略 {len(summary) - len(head) - len(tail)} 个字符 ...]\n\n{tail}"
        return ToolResult(True, content=summary)

    def set_memory_manager(self, memory_manager):
        self._memory_manager = memory_manager

    def set_llm_config_getter(self, getter):
        self._get_llm_config = getter

    def set_session_messages_getter(self, getter):
        self._get_session_messages = getter

    def set_agent_manager(self, agent_manager):
        """设置 AgentManager 实例，用于动态生成工具 schema"""
        self._agent_manager = agent_manager
        # 同时设置给 task_tools
        if hasattr(self._task_tools, '_agent_manager'):
            self._task_tools._agent_manager = agent_manager

    def memory_list(
            self,
            limit: int = 10,
            include_disabled: bool = False,
    ) -> ToolResult:
        if not self._memory_manager:
            return ToolResult(False, error="Memory manager not available")

        memories = self._memory_manager.get_user_memories()
        if not include_disabled:
            memories = [item for item in memories if item.get("enabled", True)]
        memories = memories[: max(1, int(limit or 10))]
        return ToolResult(
            True,
            content={
                "count": len(memories),
                "memories": memories,
                "formatted": self._memory_manager.format_memories_for_prompt(
                    memories,
                    title="长期记忆列表",
                    include_disabled=include_disabled,
                ),
            },
        )

    def memory_search(
            self,
            query: str = "",
            limit: int = 8,
            include_disabled: bool = False,
    ) -> ToolResult:
        if not self._memory_manager:
            return ToolResult(False, error="Memory manager not available")

        query = str(query or "").strip()
        memories = self._memory_manager.search_memories(
            query,
            include_disabled=include_disabled,
            limit=max(1, int(limit or 8)),
        )
        return ToolResult(
            True,
            content={
                "query": query,
                "count": len(memories),
                "memories": memories,
                "formatted": self._memory_manager.format_memories_for_prompt(
                    memories,
                    title=f"长期记忆搜索结果: {query or '全部'}",
                    include_disabled=include_disabled,
                ),
            },
        )

    def memory_save(
            self,
            content: str,
            confidence: float = 0.8,
            source: str = "assistant",
            conflict_group: str = "",
    ) -> ToolResult:
        if not self._memory_manager:
            return ToolResult(False, error="Memory manager not available")

        content = str(content or "").strip()
        if not content:
            return ToolResult(False, error="Memory content is empty")

        success = self._memory_manager.add_user_memory(
            content,
            source=source or "assistant",
            confidence=float(confidence or 0.8),
            conflict_group=str(conflict_group or ""),
        )
        if not success:
            return ToolResult(False, error="Failed to save memory")

        return ToolResult(
            True,
            content={
                "saved": True,
                "content": content,
                "source": source or "assistant",
                "confidence": float(confidence or 0.8),
                "conflict_group": str(conflict_group or ""),
            },
        )

    def memory_consolidate(
            self,
            max_items: int = 3,
            save: bool = True,
    ) -> ToolResult:
        if not self._memory_manager:
            return ToolResult(False, error="Memory manager not available")
        if not callable(self._get_llm_config):
            return ToolResult(False, error="LLM config getter not available")
        if not callable(self._get_session_messages):
            return ToolResult(False, error="Session messages getter not available")

        llm_config = self._get_llm_config() or {}
        messages = self._get_session_messages() or []
        if not messages:
            return ToolResult(False, error="No session messages available")

        max_items = max(1, int(max_items or 3))
        consolidated = self._memory_manager.consolidate_from_messages(
            messages,
            llm_config,
            max_items=max_items,
        )
        if not consolidated:
            return ToolResult(
                True,
                content={
                    "saved": False,
                    "count": 0,
                    "memories": [],
                    "formatted": "未提炼出适合写入长期记忆的新内容。",
                },
            )

        saved_count = 0
        if save:
            for item in consolidated:
                if self._memory_manager.add_user_memory(
                        item.get("content", ""),
                        source=item.get("source", "session"),
                        confidence=float(item.get("confidence", 0.8) or 0.8),
                        conflict_group=str(item.get("conflict_group", "") or ""),
                        category=str(item.get("category", "task_preference") or "task_preference"),
                ):
                    saved_count += 1

        formatted = self._memory_manager.format_memories_for_prompt(
            consolidated,
            title="本轮提炼出的长期记忆",
            include_disabled=False,
        )
        return ToolResult(
            True,
            content={
                "saved": bool(save),
                "saved_count": saved_count,
                "count": len(consolidated),
                "memories": consolidated,
                "formatted": formatted,
                "provider_linked": bool(
                    llm_config.get("API_URL") or llm_config.get("模型名称")
                ),
            },
        )


def create_builtin_tools(homepage=None, workdir: str = None) -> BuiltinTools:
    """创建内置工具实例"""
    return BuiltinTools(homepage, workdir)


def get_builtin_tools_schema(agent_manager=None) -> List[Dict]:
    """获取内置工具的 schema 定义（用于给 LLM 调用）

    Args:
        agent_manager: AgentManager 实例，用于动态注入可用子智能体列表
    """
    # 动态获取子智能体名称列表
    subagent_names = []
    if agent_manager and hasattr(agent_manager, 'list_subagent_names'):
        try:
            subagent_names = agent_manager.list_subagent_names(include_hidden=True)
        except Exception:
            pass
    # 动态生成 task_batch 工具描述
    if subagent_names:
        subagent_list = ", ".join(subagent_names)
        task_batch_desc = (
            f"批量分发多个子智能体任务（并行执行）。任务完成后系统会自动发送 `[后台任务状态]` 消息通知。"
            f"收到通知后使用 task_status 获取结果。\n\n"
            f"可用子智能体: {subagent_list}"
        )
    else:
        task_batch_desc = (
            "批量分发多个子智能体任务（并行执行）。任务完成后系统会自动发送 `[后台任务状态]` 消息通知。"
            "收到通知后使用 task_status 获取结果。"
        )

    return [
        {
            "type": "function",
            "function": {
                "name": "read",
                "description": "读取文件内容，返回指定范围的代码片段。",
                            # 注意：编辑时请从原始代码复制 oldString，不要包含行号前缀
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "文件相对路径"},
                        "offset": {
                            "type": "integer",
                            "description": "起始行号 (从1开始)",
                            "default": 1,
                        },
                        "limit": {
                            "type": "integer",
                            "description": "读取的行数",
                            "default": 500,
                        },
                        "show_line_numbers": {
                            "type": "boolean",
                            "description": "是否显示行号（不建议在编辑时使用，可能导致 oldString 匹配失败）",
                            "default": False,
                        },
                    },
                    "required": ["path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "write",
                "description": "创建新文件或覆盖现有文件,会自动创建不存在的目录，避免一次性写入超大型文件，超大型文件采用多次工具编辑实现。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "文件相对路径"},
                        "content": {"type": "string", "description": "完整的文件内容"},
                    },
                    "required": ["path", "content"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "edit",
                "description": "通过精确字符串替换编辑文件。为防止误改，oldString 必须在文件中唯一。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "文件路径"},
                        "oldString": {
                            "type": "string",
                            "description": "要被替换的原始精确文本块",
                        },
                        "newString": {
                            "type": "string",
                            "description": "替换后的新文本块",
                        },
                        "replaceAll": {
                            "type": "boolean",
                            "description": "如果存在多个匹配项，是否全部替换",
                            "default": False,
                        },
                    },
                    "required": ["path", "oldString", "newString"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "grep",
                "description": "在指定目录下递归搜索匹配正则表达式的内容。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pattern": {"type": "string", "description": "正则表达式"},
                        "path": {
                            "type": "string",
                            "description": "起始搜索目录 (默认当前目录)",
                            "default": ".",
                        },
                        "include": {
                            "type": "string",
                            "description": "文件过滤模式 (如 '*.py')",
                        },
                    },
                    "required": ["pattern"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list",
                "description": "列出目录下的文件和文件夹。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "目录路径",
                            "default": ".",
                        }
                    },
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "glob",
                "description": "通过通配符模式递归查找文件，支持 **, *, ? 等glob语法。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pattern": {
                            "type": "string",
                            "description": "文件匹配模式 (如 '*.py', '**/*.json', 'src/**/*.ts')"
                        },
                        "path": {
                            "type": "string",
                            "description": "搜索起始路径 (默认当前目录)",
                            "default": ".",
                        },
                    },
                    "required": ["pattern"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "multiedit",
                "description": "在同一个文件中执行多处替换操作。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "文件路径"},
                        "edits": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "oldString": {
                                        "type": "string",
                                        "description": "旧文本",
                                    },
                                    "newString": {
                                        "type": "string",
                                        "description": "新文本",
                                    },
                                },
                                "required": ["oldString", "newString"],
                            },
                        },
                    },
                    "required": ["path", "edits"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "patch",
                "description": "通过 unified diff 格式对文件进行精确修改。支持追加行、删除行、替换行、在指定位置插入行等多处修改。适用于需要同时修改文件多个位置的场景。输入标准的 unified diff 格式（包含 @@ -start +start @@ 行号标记）。**推荐优先使用 patch**，比 write/edit 更安全可靠。\n\n使用规范：\n1. 修改前先用 read 确认文件当前行号和内容\n2. @@ 行号必须是文件中实际的行号（1-based），注意 context/delete 行数之和是旧文件行数\n3. context 行（以空格开头）是匹配锚点，必须与文件完全一致（缩进、空行、空格/制表符）\n4. 只保留必要的 context 行（上下各 1-2 行）减少出错\n\n常见失败原因：\n- @@ 行号不对：检查 hunk 第一行 context 在文件中的实际行号\n- 空行数量不匹配：文件有几个空行，patch 里也要有几个\n- 缩进/空格不一致：空格和制表符不能混用\n\n失败后修复：读取报错中提示的行号附近内容，对比 patch 与文件的差异，修正后重试",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "文件路径"},
                        "patch_content": {
                            "type": "string",
                            "description": "Unified diff 格式补丁内容。格式：\n--- filename\n+++ filename\n@@ -起始行,行数 +起始行,行数 @@\n[空格]上下文行（不变）\n[-]要删除的行\n[+]要添加的新行"
                        },
                    },
                    "required": ["path", "patch_content"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "bash",
                "description": "执行shell命令",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {"type": "string", "description": "命令"},
                        "timeout": {"type": "integer", "description": "超时秒数"},
                    },
                    "required": ["command"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_diagnostics",
                "description": "获取文件的语法检查结果（错误、警告、提示）。支持 Python (pyright/mypy/flake8)、JavaScript/TypeScript (tsc/eslint)、Shell (shellcheck)。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "文件路径"},
                        "language": {
                            "type": "string",
                            "description": "语言类型，可选: python, javascript, typescript, shellscript",
                        },
                    },
                    "required": ["file_path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "webfetch",
                "description": "获取网页内容",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "网页URL"},
                        "format": {
                            "type": "string",
                            "description": "返回格式, 支持:html, text, markdown",
                        },
                    },
                    "required": ["url"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "websearch",
                "description": "网络搜索",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "搜索关键词"},
                        "num_results": {"type": "integer", "description": "结果数量"},
                    },
                    "required": ["query"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "scan_repo",
                "description": "扫描仓库目录并返回结构化摘要，适合编码任务前快速建模上下文",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "扫描路径"},
                        "max_depth": {"type": "integer", "description": "最大扫描深度"},
                    },
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "stage_files",
                "description": "标记当前任务相关文件，帮助后续聚焦编辑和验证",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "files": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "文件路径列表",
                        },
                    },
                    "required": ["files"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "memory_list",
                "description": "列出当前工作区的长期记忆，可选择是否包含已禁用/冲突记忆",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "最多返回多少条记忆",
                        },
                        "include_disabled": {
                            "type": "boolean",
                            "description": "是否包含已禁用的冲突记忆",
                        },
                    },
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "memory_search",
                "description": "检索和当前任务相关的长期记忆，适合在编码或追问前主动查用户偏好、项目约束和长期决策",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "检索关键词"},
                        "limit": {
                            "type": "integer",
                            "description": "最多返回多少条记忆",
                        },
                        "include_disabled": {
                            "type": "boolean",
                            "description": "是否包含已禁用的冲突记忆",
                        },
                    },
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "memory_save",
                "description": "保存一条可能需要跨会话记忆的关键事实进入长期记忆",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "content": {"type": "string", "description": "记忆内容"},
                        "confidence": {
                            "type": "number",
                            "description": "置信度，0 到 1",
                        },
                        "source": {"type": "string", "description": "记忆来源"},
                        "conflict_group": {
                            "type": "string",
                            "description": "冲突组，相同组的新记忆会压制旧记忆",
                        },
                    },
                    "required": ["content"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "todowrite",
                "description": "创建和更新待办事项列表",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "todos": {"type": "array", "description": "待办列表"},
                    },
                    "required": ["todos"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "todoread",
                "description": "读取待办事项列表",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "task_batch",
                "description": task_batch_desc,  # 动态描述，包含可用子智能体列表
                "parameters": {
                    "type": "object",
                    "properties": {
                        "tasks": {
                            "type": "array",
                            "description": f"任务列表，每个任务包含 agent/description/context。agent 可选：{', '.join(subagent_names)}。",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "agent": {
                                        "type": "string",
                                        "description": f"子智能体名称。",
                                        "enum": ', '.join(subagent_names),
                                    },
                                    "description": {"type": "string", "description": "任务描述"},
                                    "context": {"type": "string", "description": "详细上下文信息（可选）"},
                                },
                                "required": ["agent", "description"],
                            },
                        },
                        "share_context": {
                            "type": "boolean",
                            "description": "是否共享主智能体上下文给子智能体（默认 False）。启用后子智能体将获得主智能体的完整上下文信息。",
                            "default": True,
                        },
                    },
                    "required": ["tasks"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "task_status",
                "description": "查询子智能体任务状态。task_ids 不传时只能查一次刚完成的任务；指定 task_id 始终能查到。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_ids": {
                            "type": "array",
                            "description": "任务ID列表（不传则查刚完成的任务，只能查一次）",
                            "items": {"type": "string"},
                        },
                        "with_log": {
                            "type": "boolean",
                            "description": "是否包含执行日志（默认 False）",
                        },
                        "with_result": {
                            "type": "boolean",
                            "description": "是否包含执行结果（默认 True）",
                        },
                    }
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "skill",
                "description": "加载技能。当用户消息中包含 @技能名 时（如 @brainstorming），必须立即调用此工具加载对应技能。技能会提供特定领域的专业知识和工作流程。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string",
                                 "description": "技能名称，如 brainstorming, writing-plans, find-skills, git-commit 等"},
                    },
                    "required": ["name"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_skills",
                "description": "列出所有可用的本地技能，包括内置技能和用户安装的技能。当需要了解有哪些技能可用时可调用此工具。",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "question",
                "description": "向用户提问并获取回答。当需要了解用户偏好、需求或让用户做选择时，**必须**使用此工具，不要自行生成问卷或选项。\n\n## 使用原则\n1. **优先使用选项而非文本输入**: 总是通过 options 参数提供选项列表，让用户直接点击选择。选项可以是功能点、技术方案、确认操作等。\n2. **每个问题独立提问**: 当有多个独立问题时，应分多次调用 question 工具，每次只问一个核心问题。避免在一个 question 调用中塞入多个问题要求用户手动输入文本。\n3. **优先多次选择**: 如果需要用户做多个决定或确认多个点，使用多次 question 调用（每次设置 multiple=true 或提供选项），让用户通过选择完成，而非让他们自行组织文本回复。\n\n## 参数说明\n- question: 问题内容，尽量简洁\n- options: 选项列表（**推荐始终提供**），每个选项应该是完整的、可直接选择的\n- multiple: 是否允许多选",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "question": {"type": "string", "description": "问题内容及描述，尽量简洁，不要包含选项内容"},
                        "options": {"type": "array",
                                    "description": "选项列表。当有多个可选方案或需要用户确认时，**必须提供选项列表**，不要留空让用户文本输入。"},
                        "multiple": {
                            "type": "boolean",
                            "description": "是否允许多选，默认false",
                        },
                    },
                    "required": ["question"],
                },
            },
        },
    ]
