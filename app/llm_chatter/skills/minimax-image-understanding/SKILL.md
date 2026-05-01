---
name: minimax-image-understanding
description: 使用 MiniMax AI 分析图片内容，支持截图和本地图片解读
---

# MiniMax Image Understanding Skill

本技能提供图片分析功能，可以解读截图、代码图片、设计图等视觉内容。

## 功能特性

1. **截图功能** - 自动截取 Windows 全屏（支持4K屏幕自动检测）
2. **图片解读** - 使用 MiniMax 多模态 AI 分析图片
3. **OCR 文字提取** - 从图片中提取文字
4. **代码识别** - 识别截图中的代码内容

## 使用方法

### 1. 截图

```bash
python skills/minimax-image-understanding/scripts/take_screenshot.py
```

截图将保存为 `screenshot.png`，自动检测4K屏幕并截取完整画面。

### 2. 分析截图

```bash
set MINIMAX_API_KEY=你的API密钥 && python skills/minimax-image-understanding/scripts/analyze_image.py
```

### 3. 分析指定图片

```bash
set MINIMAX_API_KEY=你的API密钥 && python skills/minimax-image-understanding/scripts/analyze_image.py --file path/to/image.png
```

### 4. 自定义分析内容

```bash
set MINIMAX_API_KEY=你的API密钥 && python skills/minimax-image-understanding/scripts/analyze_image.py --prompt "请分析这个错误截图"
```

## 工作流程

```
┌─────────────────┐
│  截图 (screenshot.png)  │
└────────┬────────┘
         ▼
┌─────────────────┐
│  转Base64 编码  │
└────────┬────────┘
         ▼
┌─────────────────┐
│  调用MiniMax API  │
└────────┬────────┘
         ▼
┌─────────────────┐
│  返回分析结果  │
└─────────────────┘
```

## API 配置

需要在环境中设置 `MINIMAX_API_KEY` 环境变量：

```bash
set MINIMAX_API_KEY=你的API密钥
```

## 常见场景

| 场景 | 示例提示词 |
|------|-----------|
| 分析报错 | "请分析这个截图中的错误信息" |
| 代码解读 | "请描述截图中显示的代码内容" |
| UI分析 | "分析这个界面的布局和设计" |
| 文字提取 | "提取图片中的所有文字内容" |
| 图表分析 | "描述这个图表显示的数据和趋势" |

## 文件结构

```
minimax-image-understanding/
├── SKILL.md                    # 技能定义文件
├── scripts/
│   ├── take_screenshot.py      # Windows 截图脚本
│   ├── analyze_image.py        # 图片分析脚本
│   └── requirements.txt        # Python依赖 (仅使用标准库)
```

## 依赖说明

本技能使用 Python 标准库，无需额外安装依赖：
- `json` - JSON 处理
- `os` - 系统操作
- `sys` - 系统参数
- `base64` - 图片编码
- `urllib.request` - HTTP 请求
- `argparse` - 命令行参数

## 注意事项

1. **截图保存位置**: `screenshot.png` 在当前工作目录
2. **Base64文件**: `screenshot.b64` 用于临时存储
3. **API Key**: 需要有效的 MiniMax API 密钥才能使用
4. **支持格式**: PNG, JPEG, WebP
5. **不支持**: PDF, GIF, PSD, SVG

## 错误处理

| 错误码 | 说明 | 解决方案 |
|--------|------|----------|
| 1004 | 认证失败 | 检查 API Key 是否正确 |
| 2038 | 实名认证 | 需要在 MiniMax 完成实名认证 |
| 文件不存在 | 图片路径错误 | 检查文件路径是否正确 |
| 截图失败 | PowerShell 问题 | 尝试使用 Alt+PrintScreen 后运行脚本 |