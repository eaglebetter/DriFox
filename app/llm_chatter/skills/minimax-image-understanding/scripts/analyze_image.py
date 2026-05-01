"""
MiniMax 图片分析脚本
使用 MiniMax 多模态 API 分析图片内容

使用方法:
    python analyze_image.py                    # 分析截图
    python analyze_image.py --file image.png   # 分析指定图片
    python analyze_image.py --prompt "你的问题" # 自定义提示词

环境配置:
    set MINIMAX_API_KEY=your_key  # 或在 ~/.minimax/api_key 配置
"""
import json
import os
import sys
import base64
import ssl
import urllib.request
import urllib.error
import argparse
from pathlib import Path

# 添加 common 目录到路径
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from common.utils import get_api_key, ConfigError


def encode_image_to_base64(image_path):
    """
    将图片文件转换为 Base64 编码
    
    Args:
        image_path: 图片文件路径
    
    Returns:
        str: Base64 编码字符串 (不含 data URL 前缀)
    """
    with open(image_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')


def analyze_image(image_path, prompt=None, api_key=None):
    """
    使用 MiniMax API 分析图片
    
    Args:
        image_path: 图片文件路径
        prompt: 分析提示词
        api_key: MiniMax API 密钥
    
    Returns:
        dict: API 响应结果
    """
    # 默认提示词
    if prompt is None:
        prompt = "请详细描述这张图片的内容，包括所有文字、界面元素、颜色和布局。"
    
    # 获取 API Key
    if api_key is None:
        try:
            api_key = get_api_key()
        except ConfigError as e:
            raise ValueError(str(e))
    
    # API 配置
    api_host = "api.minimax.chat"
    endpoint = "/v1/coding_plan/vlm"
    
    # 读取图片并编码
    print(f"读取图片: {image_path}")
    base64_data = encode_image_to_base64(image_path)
    print(f"图片 Base64 编码完成，长度: {len(base64_data)} 字符")
    
    # 构建请求
    url = f"https://{api_host}{endpoint}"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    payload = {
        "prompt": prompt,
        "image_url": f"data:image/png;base64,{base64_data}"
    }
    
    print("正在调用 MiniMax API...")
    print(f"提示词: {prompt[:50]}..." if len(prompt) > 50 else f"提示词: {prompt}")
    
    # 发送请求
    data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    
    try:
        req = urllib.request.Request(url, data=data, headers=headers, method='POST')
        context = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=120, context=context) as response:
            result = json.loads(response.read().decode('utf-8'))
            
            # 解析响应
            if 'choices' in result and len(result['choices']) > 0:
                content = result['choices'][0]['message']['content']
            elif 'content' in result:
                content = result['content']
            else:
                return {"success": True, "raw": result, "content": json.dumps(result, indent=2, ensure_ascii=False)}
            
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


def main():
    parser = argparse.ArgumentParser(
        description="使用 MiniMax AI 分析图片内容",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python analyze_image.py                          # 分析 screenshot.png
  python analyze_image.py --file myimage.png        # 分析指定图片
  python analyze_image.py --prompt "描述图片内容"   # 使用自定义提示词
  set MINIMAX_API_KEY=sk-xxx && python analyze_image.py
        """
    )
    
    parser.add_argument(
        '--file', '-f',
        default='screenshot.png',
        help='图片文件路径 (默认: screenshot.png)'
    )
    
    parser.add_argument(
        '--prompt', '-p',
        default=None,
        help='分析提示词 (默认: "请详细描述这张图片的内容")'
    )
    
    args = parser.parse_args()
    
    # 检查图片文件是否存在
    if not os.path.exists(args.file):
        # 尝试当前目录
        current_file = os.path.join(os.getcwd(), args.file)
        if os.path.exists(current_file):
            args.file = current_file
        else:
            print(f"错误: 找不到图片文件: {args.file}")
            print(f"当前目录: {os.getcwd()}")
            sys.exit(1)
    
    # 分析图片
    result = analyze_image(args.file, args.prompt)
    print_result(result)
    
    if not result.get("success"):
        sys.exit(1)


if __name__ == "__main__":
    main()