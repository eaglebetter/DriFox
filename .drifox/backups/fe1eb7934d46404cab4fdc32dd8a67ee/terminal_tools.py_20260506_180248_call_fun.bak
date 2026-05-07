import subprocess
import threading
import time
from pathlib import Path

from app.tools.result import ToolResult


class TerminalTools:
    def __init__(self, workdir: Path):
        self.workdir = workdir

    def execute_bash(self, command: str, timeout: int = 120) -> ToolResult:
        """执行 shell 命令，支持可靠的 timeout
        
        使用 communicate(timeout) 避免管道死锁，同时在超时时杀死进程。
        """
        import platform

        try:
            # Windows: 强制切换到 UTF-8 代码页，确保输出编码一致
            if platform.system() == "Windows":
                # 先设置环境变量，再嵌入 chcp 命令
                command = f"chcp 65001 >nul 2>&1 && {command}"

            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="ignore",
                cwd=str(self.workdir),
            )

            start_time = time.time()

            # 使用子线程执行 communicate，避免阻塞主线程
            result_holder = {"stdout": None, "stderr": None, "error": None}
            
            def communicate_in_thread():
                """在子线程中执行 communicate，同时读取 stdout 和 stderr"""
                try:
                    stdout, stderr = process.communicate()
                    result_holder["stdout"] = stdout
                    result_holder["stderr"] = stderr
                except Exception as e:
                    result_holder["error"] = str(e)

            comm_thread = threading.Thread(target=communicate_in_thread, daemon=True)
            comm_thread.start()

            # 等待线程完成或超时
            comm_thread.join(timeout=timeout)

            if comm_thread.is_alive():
                # 超时：杀死进程
                try:
                    process.kill()
                    # 等待线程结束（进程被杀后 communicate 会立即返回）
                    comm_thread.join(timeout=5)
                except Exception:
                    pass

                elapsed = time.time() - start_time
                return ToolResult(False, error=f"Command timeout after {elapsed:.1f}s (killed)")

            # 检查是否有错误
            if result_holder["error"]:
                return ToolResult(False, error=f"Execution error: {result_holder['error']}")

            # 进程正常完成
            stdout = result_holder["stdout"] or ""
            stderr = result_holder["stderr"] or ""
            
            output = stdout.strip() if stdout else ""
            error_out = stderr.strip() if stderr else ""
            combined = "\n".join(filter(None, [output, error_out]))

            return ToolResult(
                True,
                content=combined if combined else "(command completed with no output)",
            )

        except Exception as e:
            return ToolResult(False, error=f"Execution error: {str(e)}")

    def run_verify(self, command: str = "", timeout: int = 120) -> ToolResult:
        try:
            verify_command = (command or "").strip()
            if not verify_command:
                if (self.workdir / "pytest.ini").exists() or list(
                    self.workdir.glob("test_*.py")
                ):
                    verify_command = "pytest -q"
                elif (self.workdir / "main.py").exists():
                    verify_command = "python -m py_compile main.py"
                else:
                    verify_command = "python -m py_compile ."

            result = self.execute_bash(verify_command, timeout=timeout)
            if result.success:
                return ToolResult(
                    True,
                    content=f"[verify] command: {verify_command}\n{result.content}",
                )
            return ToolResult(
                False, error=f"[verify] command: {verify_command}\n{result.error}"
            )
        except Exception as e:
            return ToolResult(False, error=f"run_verify error: {str(e)}")
