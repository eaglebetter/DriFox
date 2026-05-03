"""
截图脚本 - 修复4K屏幕截图问题
强制使用横向分辨率
"""
import subprocess
import os
import sys
import tempfile


def take_screenshot(output_path="screenshot.png"):
    """
    使用PowerShell截取全屏，强制横向4K分辨率
    """
    if not os.path.isabs(output_path):
        output_path = os.path.join(os.getcwd(), output_path)
    
    # 强制横向4K分辨率截图
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

# 获取物理分辨率
$hdc = [Win32]::GetDC([IntPtr]::Zero)
$physicalWidth = [Win32]::GetDeviceCaps($hdc, 117)  # HORZRES
$physicalHeight = [Win32]::GetDeviceCaps($hdc, 118)  # VERTRES
[Win32]::ReleaseDC([IntPtr]::Zero, $hdc) | Out-Null

# 如果高度>宽度，说明是竖屏模式，交换它们
if ($physicalHeight -gt $physicalWidth) {
    $temp = $physicalWidth
    $physicalWidth = $physicalHeight
    $physicalHeight = $temp
}

Write-Host "截图分辨率: $physicalWidth x $physicalHeight"

# 创建位图
$bmp = New-Object System.Drawing.Bitmap($physicalWidth, $physicalHeight)
$graf = [System.Drawing.Graphics]::FromImage($bmp)

# 高质量截图
$graf.CopyFromScreen(0, 0, 0, 0, (New-Object System.Drawing.Size($physicalWidth, $physicalHeight)))

# 保存
$bmp.Save("%OUTPUT%", [System.Drawing.Imaging.ImageFormat]::Png)

$graf.Dispose()
$bmp.Dispose()

Write-Host "截图成功!"
exit 0
'''.replace('%OUTPUT%', output_path.replace('\\', '\\\\').replace('/', '\\\\'))
    
    temp_file = os.path.join(tempfile.gettempdir(), 'shot.ps1')
    
    with open(temp_file, 'w', encoding='utf-8') as f:
        f.write(ps_script.replace('{{', '{').replace('}}', '}'))
    
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
        
        for line in result.stdout.split('\n'):
            line = line.strip()
            if line:
                print(line)
        
        if result.returncode == 0 and os.path.exists(output_path):
            size = os.path.getsize(output_path)
            print(f"文件大小: {size/1024:.1f} KB ({size/1024/1024:.1f} MB)")
            return True
        else:
            if result.stderr:
                print(f"错误: {result.stderr.strip()}")
            return False
            
    except Exception as e:
        print(f"异常: {e}")
        try:
            os.remove(temp_file)
        except:
            pass
        return False


if __name__ == "__main__":
    output = sys.argv[1] if len(sys.argv) > 1 else "screenshot.png"
    success = take_screenshot(output)
    if not success:
        sys.exit(1)