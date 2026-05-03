---
name: minimax-image-understanding
description: 使用 MiniMax AI 分析图片内容，支持电脑屏幕截图和本地图片解读
---

# MiniMax Image Understanding Skill

本技能提供图片分析功能，可以解读截图、代码图片、设计图等视觉内容。

## 功能特性

1. **一键截图+分析** - 自动完成截图、编码、API调用全流程
2. **4K屏幕支持** - 自动检测并截取完整画面
3. **图片解读** - 使用 MiniMax 多模态 AI 分析图片
4. **多方式配置** - 支持环境变量或配置文件自动获取 API Key

## 一键启动器（最简单）

如果不想每次输入命令，可以使用一键启动器：

```bash
python scripts/launcher.py
```

启动器会自动：
1. 探测 Python 环境（使用 `py -3.12` 或系统 Python）
2. 检查已保存的 API Key（`~/.minimax/api_key`）
3. 未配置时提示用户输入并可选保存
4. 执行截图+分析

### 首次使用

```
飘狐 DriFox - 截图分析
====================================

[1/3] 检测 Python 环境...
  找到: py -3.12

[2/3] 检查 API Key...
  未设置
========================================
需要配置 API Key
========================================
请输入 MiniMax API Key: sk-xxx...
是否保存到配置文件供下次使用? (y/N): y
已保存到: C:\Users\xxx\.minimax\api_key

[3/3] 执行截图分析...
```

### 以后使用

直接运行 `python scripts/launcher.py`，无需再次输入 Key（除非 Key 过期）。

---

## 手动使用方式

### 一键完成截图+分析（推荐）

```bash
set MINIMAX_API_KEY=你的API密钥 && python scripts/capture_and_analyze.py
```

这会在**一轮调用内**完成所有操作：
1. 截取屏幕
2. Base64 编码
3. 调用 MiniMax API
4. 返回分析结果

## 使用方法

### 1. 截图 + 分析（一键）

```bash
set MINIMAX_API_KEY=你的API密钥 && python scripts/capture_and_analyze.py
```

### 2. 仅分析已有截图

```bash
set MINIMAX_API_KEY=你的API密钥 && python scripts/capture_and_analyze.py --no-screenshot
```

### 3. 分析指定图片

```bash
set MINIMAX_API_KEY=你的API密钥 && python scripts/analyze_image.py --file path/to/image.png
```

### 4. 自定义分析提示词

```bash
set MINIMAX_API_KEY=你的API密钥 && python scripts/capture_and_analyze.py --prompt "请分析这个错误截图"
```

## API Key 配置

支持多种方式配置 API Key，按优先级排序：

1. **环境变量**（推荐）
   ```bash
   set MINIMAX_API_KEY=你的API密钥
   ```

2. **配置文件**
   ```
   ~/.minimax/api_key
   ```

## 工作流程

```
┌─────────────────────────────────────────┐
│  capture_and_analyze.py (一键入口)      │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│  截图 → Base64 → MiniMax API → 结果    │
└─────────────────────────────────────────┘
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
│   ├── common/
│   │   ├── __init__.py         # 模块初始化
│   │   └── utils.py            # 通用工具 (Python探测、API Key获取)
│   ├── capture_and_analyze.py  # 一键截图+分析入口
│   ├── take_screenshot.py      # 独立截图脚本
│   ├── analyze_image.py        # 独立分析脚本
│   └── requirements.txt        # Python依赖
```

## 技术细节

### 自动探测

脚本会自动探测：
- **Python 解释器**：从 PATH、常见安装路径、Windows 注册表中自动查找
- **API Key**：从环境变量或配置文件中自动获取

### 依赖说明

本技能使用 Python 标准库，无需额外安装依赖

## 错误处理

| 错误类型 | 说明 | 解决方案 |
|----------|------|----------|
| 未找到 Python | 系统未安装 Python | 安装 Python 3.x |
| 未设置 API Key | 缺少认证信息 | 设置 MINIMAX_API_KEY 环境变量 |
| HTTP 1004 | 认证失败 | 检查 API Key 是否正确 |
| HTTP 2038 | 实名认证 | 在 MiniMax 完成实名认证 |
| 文件不存在 | 图片路径错误 | 检查文件路径是否正确 |
| 截图失败 | PowerShell 问题 | 尝试使用 Alt+PrintScreen 后运行脚本 |
