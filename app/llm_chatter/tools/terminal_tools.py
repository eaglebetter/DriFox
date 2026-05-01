import subprocess
import threading
import time
from pathlib import Path

from app.llm_chatter.tools.result import ToolResult


class TerminalTools:
    def __init__(self, workdir: Path):
        self.workdir = workdir

    def execute_bash(self, command: str, timeout: int = 120) -> ToolResult:
        """执行 shell 命令，支持可靠的 timeout
        
        注意：使用 Popen + wait() 替代 run()，因为 run() 的 timeout
        在 shell=True 时对后台进程无效。
        """
        try:
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

            def wait_for_process():
                """在线程中等待进程完成"""
                nonlocal process_finished
                try:
                    process.wait()
                    process_finished = True
                except Exception:
                    pass

            process_finished = False
            wait_thread = threading.Thread(target=wait_for_process, daemon=True)
            wait_thread.start()

            # 等待进程完成或超时
            wait_thread.join(timeout=timeout)

            if not process_finished:
                # 超时：杀死进程树
                try:
                    process.kill()
                    # 等待进程真正退出
                    process.wait(timeout=5)
                except Exception:
                    pass

                elapsed = time.time() - start_time
                return ToolResult(False, error=f"Command timeout after {elapsed:.1f}s (killed)")

            # 进程正常完成
            stdout, stderr = process.communicate()
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