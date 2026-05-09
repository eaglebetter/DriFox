"""
一键截图+分析脚本
自动完成: 截图 → 分析 → 输出结果

使用方法:
    python capture_and_analyze.py                          # 截图并分析
    python capture_and_analyze.py --no-screenshot         # 仅分析已有截图
    python capture_and_analyze.py --prompt "自定义问题"   # 自定义分析提示词
"""
import os
import sys
import orjson as json
import base64
import ssl
import urllib.request
import urllib.error
import argparse
import tempfile
import subprocess
from pathlib import Path

# 添加 common 目录到路径
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from common.utils import get_python_executable, get_api_key, PythonFinder


# ============== 截图功能 ==============

def take_screenshot(output_path="screenshot.png"):
    """
    使用 PowerShell 截取全屏，支持 4K 屏幕
    """
    if not os.path.isabs(output_path):
        output_path = os.path.join(os.getcwd(), output_path)
    
    ps_script = '''
Add-Type -AssemblyName System.Windows.Forms
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Win32 {
    [DllImport("user32.dll")] public static extern IntPtr GetDC(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern int ReleaseDC(IntPtr hWnd, IntPtr hDC);
    [DllImport("gdi32.dll")] public static extern int GetDeviceCaps(IntPtr hDC, int index);
}
"@

$hdc = [Win32]::GetDC([IntPtr]::Zero)
$physicalWidth = [Win32]::GetDeviceCaps($hdc, 117)
$physicalHeight = [Win32]::GetDeviceCaps($hdc, 118)
[Win32]::ReleaseDC([IntPtr]::Zero, $hdc) | Out-Null

if ($physicalHeight -gt $physicalWidth) {
    $temp = $physicalWidth
    $physicalWidth = $physicalHeight
    $physicalHeight = $temp
}

$bmp = New-Object System.Drawing.Bitmap($physicalWidth, $physicalHeight)
$graf = [System.Drawing.Graphics]::FromImage($bmp)
$graf.CopyFromScreen(0, 0, 0, 0, (New-Object System.Drawing.Size($physicalWidth, $physicalHeight)))
$bmp.Save('%OUTPUT%', [System.Drawing.Imaging.ImageFormat]::Png)
$graf.Dispose()
$bmp.Dispose()
exit 0
'''.replace('%OUTPUT%', output_path.replace('\\', '\\\\').replace('/', '\\\\'))
    
    temp_file = os.path.join(tempfile.gettempdir(), 'shot.ps1')
    
    with open(temp_file, 'w', encoding='utf-8') as f:
        # 修复 PowerShell 脚本中的大括号转义问题
        content = ps_script.replace('{{', '{').replace('}}', '}')
        f.write(content)
    
    print("正在截取屏幕...")
    
    try:
        result = subprocess.run(
            ['powershell', '-ExecutionPolicy', 'Bypass', '-File', temp_file],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=30
        )
        
        os.remove(temp_file)
        
        if result.returncode == 0 and os.path.exists(output_path):
            size = os.path.getsize(output_path)
            print(f"截图成功! 分辨率检测完成，文件大小: {size/1024/1024:.1f} MB")
            return True
        else:
            print(f"截图失败: {result.stderr.strip() if result.stderr else '未知错误'}")
            return False
            
    except subprocess.TimeoutExpired:
        print("截图超时")
        return False
    except Exception as e:
        print(f"截图异常: {e}")
        try:
            os.remove(temp_file)
        except:
            pass
        return False


# ============== 分析功能 ==============

def encode_image_to_base64(image_path):
    """将图片文件转换为 Base64 编码"""
    with open(image_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')


def analyze_image(image_path, prompt=None, api_key=None):
    """
    使用 MiniMax API 分析图片
    """
    if prompt is None:
        prompt = "请详细描述这张图片的内容，包括所有文字、界面元素、颜色和布局。"
    
    if api_key is None:
        api_key = get_api_key()
    
    if not api_key:
        raise ValueError("未设置 MINIMAX_API_KEY 环境变量")
    
    print(f"读取图片: {image_path}")
    base64_data = encode_image_to_base64(image_path)
    
    api_host = "api.minimax.chat"
    endpoint = "/v1/coding_plan/vlm"
    
    url = f"https://{api_host}{endpoint}"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    payload = {
        "prompt": prompt,
        "image_url": f"data:image/png;base64,{base64_data}"
    }
    
    print("正在调用 MiniMax API 分析...")
    
    data = json.dumps(payload)
    
    try:
        req = urllib.request.Request(url, data=data, headers=headers, method='POST')
        context = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=120, context=context) as response:
            result = json.loads(response.read().decode('utf-8'))
            
            if 'choices' in result and len(result['choices']) > 0:
                content = result['choices'][0]['message']['content']
            elif 'content' in result:
                content = result['content']
            else:
                content = json.dumps(result, option=json.OPT_INDENT_2).decode('utf-8')
            
            return {"success": True, "content": content}
            
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        return {"success": False, "error": f"HTTP {e.code}", "details": error_body}
    except Exception as e:
        return {"success": False, "error": str(e)}


def print_result(result):
    """打印分析结果"""
    if result.get("success"):
        print("\n" + "=" * 60)
        print("图片分析结果:")
        print("=" * 60)
        print(result.get("content", ""))
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("分析失败:")
        print("=" * 60)
        print(f"错误: {result.get('error')}")
        if 'details' in result:
            print(f"详情: {result.get('details')}")
        print("=" * 60)


# ============== 主入口 ==============

def main():
    parser = argparse.ArgumentParser(
        description="一键截图+分析屏幕内容",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python capture_and_analyze.py                    # 截图并分析
  python capture_and_analyze.py --no-screenshot    # 分析已有截图
  python capture_and_analyze.py -p "请分析UI布局" # 自定义分析问题

环境配置:
  set MINIMAX_API_KEY=your_key  # 或在 ~/.minimax/api_key 配置
        """
    )
    
    parser.add_argument(
        '--no-screenshot', '-n',
        action='store_true',
        help='跳过截图，仅分析已有的 screenshot.png'
    )
    
    parser.add_argument(
        '--prompt', '-p',
        default=None,
        help='自定义分析提示词'
    )
    
    parser.add_argument(
        '--file', '-f',
        default='screenshot.png',
        help='截图保存路径 (默认: screenshot.png)'
    )
    
    args = parser.parse_args()
    
    # 1. 截图 (除非指定跳过)
    if not args.no_screenshot:
        print(f"[1/2] 截图阶段")
        if not take_screenshot(args.file):
            sys.exit(1)
    else:
        if not os.path.exists(args.file):
            print(f"错误: 找不到图片文件: {args.file}")
            sys.exit(1)
        print(f"使用已有截图: {args.file}")
    
    # 2. 分析
    print(f"\n[2/2] 分析阶段")
    result = analyze_image(args.file, args.prompt)
    print_result(result)
    
    if not result.get("success"):
        sys.exit(1)


if __name__ == "__main__":
    main()
