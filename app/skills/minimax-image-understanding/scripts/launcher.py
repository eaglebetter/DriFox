#!/usr/bin/env python3
"""
智能启动器 - 自动解决 Python 环境问题
用户只需运行这个脚本，无需关心 Python 路径配置

使用方法:
    python launcher.py                    # 截图+分析
    python launcher.py --skip-capture     # 仅分析已有截图
"""
import os
import sys
import subprocess
from pathlib import Path


def find_python():
    """智能查找可用的 Python 解释器"""
    # 方法1: 尝试 py launcher (Windows 推荐)
    for version in ['-3.12', '-3.11', '-3.10', '-3.9', '-3']:
        try:
            result = subprocess.run(
                ['py', version, '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                version_num = version.replace('-', '')
                return ['py', version], version_num
        except:
            pass
    
    # 方法2: 直接尝试 python
    for cmd in ['python', 'python3']:
        try:
            result = subprocess.run(
                [cmd, '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return [cmd], None
        except:
            pass
    
    return None, None


def get_saved_api_key():
    """从配置文件读取已保存的 API Key"""
    config_file = Path.home() / ".minimax" / "api_key"
    if config_file.exists():
        content = config_file.read_text().strip()
        # 跳过注释行
        if content and not content.startswith('#'):
            return content
    return None


def save_api_key(api_key):
    """保存 API Key 到配置文件"""
    config_dir = Path.home() / ".minimax"
    config_dir.mkdir(exist_ok=True)
    config_file = config_dir / "api_key"
    config_file.write_text(api_key)
    return config_file


def main():
    # 切换到脚本所在目录
    script_dir = Path(__file__).parent.resolve()
    os.chdir(script_dir)
    
    print("飘狐 DriFox - 截图分析")
    print("=" * 40)
    
    # 0. 尝试从配置文件加载已保存的 API Key
    saved_key = get_saved_api_key()
    
    # 1. 找 Python
    print("\n[1/3] 检测 Python 环境...")
    python_cmd, version_num = find_python()
    
    if python_cmd is None:
        print("错误: 未找到可用的 Python 解释器")
        print("请安装 Python 3.x: https://www.python.org/downloads/")
        input("\n按 Enter 键退出...")
        sys.exit(1)
    
    python_exe = ' '.join(python_cmd)
    print(f"  找到: {python_exe}")
    
    # 2. 获取 API Key
    print("\n[2/3] 检查 API Key...")
    
    # 优先级: 环境变量 > 保存的配置 > 用户输入
    api_key = os.environ.get('MINIMAX_API_KEY')
    
    if not api_key and saved_key:
        api_key = saved_key
        print(f"  从配置文件读取: {api_key[:10]}...")
    elif not api_key:
        print("  未设置")
        print("\n" + "=" * 40)
        print("需要配置 API Key")
        print("=" * 40)
        
        # 检查是否有保存的密钥
        if saved_key:
            print(f"发现已保存的密钥: {saved_key[:10]}...")
            print("直接使用 (Enter) / 重新输入 (输入新密钥)")
            choice = input("选择: ").strip()
            if not choice:
                api_key = saved_key
            else:
                api_key = choice
                save_api_key(api_key)
                print(f"已更新保存: {api_key[:10]}...")
        else:
            user_key = input("请输入 MiniMax API Key: ").strip()
            if not user_key:
                print("取消操作")
                sys.exit(0)
            api_key = user_key
            
            # 询问是否保存
            save = input("是否保存到配置文件供下次使用? (y/N): ").strip().lower()
            if save == 'y':
                config_file = save_api_key(api_key)
                print(f"已保存到: {config_file}")
    
    if api_key:
        print(f"  使用 Key: {api_key[:10]}...")
    
    # 3. 执行
    print("\n[3/3] 执行截图分析...")
    env = os.environ.copy()
    env['MINIMAX_API_KEY'] = api_key
    
    capture_args = [] if '--skip-capture' in sys.argv else []
    
    try:
        cmd = python_cmd + ['-u', 'capture_and_analyze.py'] + capture_args
        result = subprocess.run(cmd, env=env)
        sys.exit(result.returncode)
    except KeyboardInterrupt:
        print("\n操作已取消")
        sys.exit(0)


if __name__ == "__main__":
    main()