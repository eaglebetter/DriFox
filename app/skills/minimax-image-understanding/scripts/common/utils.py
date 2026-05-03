"""
通用工具模块 - 提供 Python 探测和 API Key 获取功能
"""
import os
import sys
import subprocess
import json
import base64
from pathlib import Path


class PythonFinder:
    """自动探测系统中可用的 Python 解释器"""
    
    # 常见 Python 安装路径 (Windows)
    COMMON_PATHS = [
        # User installations
        Path.home() / "AppData" / "Local" / "Programs" / "Python" / "Python312" / "python.exe",
        Path.home() / "AppData" / "Local" / "Programs" / "Python" / "Python311" / "python.exe",
        Path.home() / "AppData" / "Local" / "Programs" / "Python" / "Python310" / "python.exe",
        Path.home() / "AppData" / "Local" / "Programs" / "Python" / "Python39" / "python.exe",
        # System installations
        Path("C:/") / "Python312" / "python.exe",
        Path("C:/") / "Python311" / "python.exe",
        Path("C:/") / "Python310" / "python.exe",
        Path("C:/") / "Program Files" / "Python312" / "python.exe",
        Path("C:/") / "Program Files" / "Python311" / "python.exe",
        Path("C:/") / "Program Files (x86)" / "Python312" / "python.exe",
        Path("C:/") / "Program Files (x86)" / "Python311" / "python.exe",
        # Anaconda
        Path.home() / "anaconda3" / "python.exe",
        Path.home() / "miniconda3" / "python.exe",
        Path("C:/") / "anaconda3" / "python.exe",
        Path("C:/") / "miniconda3" / "python.exe",
    ]
    
    @classmethod
    def find_from_path(cls):
        """从 PATH 环境变量中查找 python"""
        import shutil
        
        # 尝试 python3, python
        for name in ['py', 'python3', 'python']:
            path = shutil.which(name)
            if path:
                return Path(path)
        return None
    
    @classmethod
    def find_from_registry(cls):
        """从 Windows 注册表查找 Python (可选功能)"""
        try:
            import winreg
            results = []
            
            # 尝试读取 Python 3.x 安装路径
            for view in [winreg.KEY_READ]:
                try:
                    key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                                         r"SOFTWARE\Python\PythonCore", 0, view)
                    i = 0
                    while True:
                        try:
                            subkey_name = winreg.EnumKey(key, i)
                            # 查找版本目录下的 InstallPath
                            try:
                                version_key = winreg.OpenKey(key, subkey_name)
                                try:
                                    install_path, _ = winreg.QueryValueEx(version_key, "InstallPath")
                                    if install_path:
                                        exe_path = Path(install_path) / "python.exe"
                                        if exe_path.exists():
                                            results.append(exe_path)
                                except:
                                    pass
                                winreg.CloseKey(version_key)
                            except:
                                pass
                            i += 1
                        except OSError:
                            break
                    winreg.CloseKey(key)
                except:
                    pass
                    
            return results[0] if results else None
        except:
            return None
    
    @classmethod
    def verify_python(cls, path):
        """验证 Python 解释器是否可用"""
        try:
            result = subprocess.run(
                [str(path), '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except:
            return False
    
    @classmethod
    def find(cls):
        """
        自动探测系统中可用的 Python 解释器
        
        探测顺序:
        1. PATH 环境变量中的 python
        2. 常见安装路径
        3. Windows 注册表
        
        Returns:
            Path or None: 找到的 Python 路径，未找到返回 None
        """
        # 1. 先从 PATH 查找 (最可靠，用户配置的)
        path_from_path = cls.find_from_path()
        if path_from_path and cls.verify_python(path_from_path):
            return path_from_path
        
        # 2. 遍历常见安装路径
        for candidate in cls.COMMON_PATHS:
            if candidate.exists() and cls.verify_python(candidate):
                return candidate
        
        # 3. 尝试注册表
        registry_path = cls.find_from_registry()
        if registry_path and cls.verify_python(registry_path):
            return registry_path
        
        return None


class APIKeyFinder:
    """自动获取 MiniMax API Key"""
    
    # 可用的环境变量名
    ENV_VARS = [
        'MINIMAX_API_KEY',
        'MINIMAX_KEY', 
        'OPENAI_API_KEY',  # 某些平台可能复用
    ]
    
    # 可能的配置文件位置
    CONFIG_FILES = [
        Path.home() / ".minimax" / "api_key",
        Path.home() / ".config" / "minimax" / "api_key",
        Path.home() / ".env",
    ]
    
    @classmethod
    def find_from_env(cls):
        """从环境变量获取"""
        for var in cls.ENV_VARS:
            key = os.environ.get(var)
            if key:
                return key
        return None
    
    @classmethod
    def find_from_config(cls):
        """从配置文件获取"""
        for config_file in cls.CONFIG_FILES:
            if config_file.exists():
                try:
                    content = config_file.read_text().strip()
                    if content and not content.startswith('#'):
                        return content
                except:
                    pass
        return None
    
    @classmethod
    def find(cls, raise_if_missing=True):
        """
        自动获取 MiniMax API Key
        
        查找顺序:
        1. 环境变量 (MINIMAX_API_KEY)
        2. 配置文件 (~/.minimax/api_key)
        
        Args:
            raise_if_missing: 未找到时是否抛出异常
        
        Returns:
            str or None: API Key
        """
        key = cls.find_from_env()
        if key:
            return key
        
        key = cls.find_from_config()
        if key:
            return key
        
        if raise_if_missing:
            # 输出结构化错误信息，供 agent 调用 question 工具
            error_info = {
                "error_type": "MISSING_API_KEY",
                "exit_code": 10,
                "message": "未找到 MiniMax API Key",
                "solutions": [
                    "set MINIMAX_API_KEY=your_key",
                    "在 ~/.minimax/api_key 文件中写入密钥"
                ],
                "question_for_user": "请提供您的 MiniMax API Key"
            }
            print("\n" + "=" * 60, file=sys.stderr)
            print("【配置缺失】需要 MiniMax API Key 才能使用图片分析功能", file=sys.stderr)
            print("=" * 60, file=sys.stderr)
            print(f"错误类型: {error_info['error_type']}", file=sys.stderr)
            print(f"退出码: {error_info['exit_code']}", file=sys.stderr)
            print("-" * 60, file=sys.stderr)
            print("解决方法 (二选一):", file=sys.stderr)
            for i, solution in enumerate(error_info['solutions'], 1):
                print(f"  {i}. {solution}", file=sys.stderr)
            print("=" * 60, file=sys.stderr)
            raise ConfigError(error_info)
        return None


class ConfigError(Exception):
    """配置错误异常"""
    
    def __init__(self, info_or_message):
        if isinstance(info_or_message, dict):
            self.error_info = info_or_message
            super().__init__(info_or_message['message'])
        else:
            self.error_info = {"message": info_or_message}
            super().__init__(info_or_message)
    
    def to_question(self):
        """生成向用户提问的内容"""
        if self.error_info.get('question_for_user'):
            return self.error_info['question_for_user']
        return self.error_info.get('message', '配置错误')


def get_python_executable():
    """
    获取当前脚本应该使用的 Python 解释器路径
    
    Returns:
        str: Python 解释器路径
    """
    # 如果当前 Python 可用，直接返回
    if PythonFinder.verify_python(Path(sys.executable)):
        return sys.executable
    
    # 否则尝试自动探测
    found = PythonFinder.find()
    if found:
        return str(found)
    
    raise ConfigError(
        "未找到可用的 Python 解释器\n"
        "请确保已安装 Python 3.x"
    )


def get_api_key():
    """
    获取 MiniMax API Key
    
    Returns:
        str: API Key
    
    Raises:
        ConfigError: 未找到 API Key 时抛出，包含向用户提问的信息
    """
    return APIKeyFinder.find()


if __name__ == "__main__":
    print("Python 探测测试:")
    python_path = PythonFinder.find()
    if python_path:
        print(f"  找到 Python: {python_path}")
    else:
        print("  未找到 Python")
    
    print("\nAPI Key 探测测试:")
    try:
        key = APIKeyFinder.find()
        if key:
            print(f"  找到 API Key: {key[:10]}...")
    except ConfigError as e:
        print(f"  {e}")
