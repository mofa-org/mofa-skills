---
name: mofa-poster
description: "从论文源码自动生成学术会议海报。支持 Overleaf LaTeX 项目、交互式布局编辑、PDF 导出。Triggers: poster, 海报, 生成海报, make poster"
requires_bins: git, npm, python3, sips
requires_env:
always: false
---

# MoFA Poster - 学术海报生成器

从论文源码（Overleaf LaTeX）和项目网站自动生成专业学术海报。输出为交互式 HTML 文件，可拖拽调整布局、导出 PDF。

## Onboarding / 开始使用

### 第一步：安装依赖

```bash
# 安装 Vercel CLI（用于下载网页图片）
npm install -g vercel

# 安装 Playwright（用于截图和自动化）
pip3 install playwright
playwright install chromium
```

### 第二步：准备论文源码

```bash
# 创建海报项目目录
mkdir my-poster && cd my-poster

# 从 Overleaf 克隆论文源码
git clone https://git.overleaf.com/YOUR_PROJECT_ID overleaf

# 可选：添加参考海报用于风格匹配
mkdir references
cp ~/some_reference_poster.pdf references/
```

### 第三步：生成海报

```bash
# 在 Claude Code 中运行
/make-poster

# 或告诉 Claude
"帮我从 overleaf 目录生成一个学术海报，项目网站是 https://..."
```

---

## 使用方法

### 基础流程

1. **准备素材**
   - 论文源码放入 `overleaf/` 目录
   - 参考海报放入 `references/` 目录（可选）

2. **运行生成**
   ```
   告诉 Claude："生成学术海报"
   ```

3. **交互编辑**
   - 拖拽蓝色分隔线调整列宽/行高
   - 点击卡片菱形按钮交换位置
   - A-/A+ 调整字体大小

4. **导出 PDF**
   - 点击 **Preview** 预览打印效果
   - 浏览器打印 → 另存为 PDF

### 示例对话

**你:** "从 overleaf 目录生成一个 CVPR 海报，项目网站是 https://my-project.github.io"

**Claude:**
```
好的！我来为你生成 CVPR 学术海报。

计划：
- 读取 overleaf/main.tex 提取内容
- 抓取项目网站的图片和链接
- 分析 reference/ 中的参考海报风格
- 生成 A0 横向海报

开始生成...
✓ 提取论文内容（标题、作者、摘要）
✓ 下载项目图片
✓ 转换 PDF 图表为 PNG
✓ 生成海报 HTML
✓ 优化布局（最小化空白）
✓ 导出 PDF

🎉 海报生成成功！
打开 poster/index.html 进行编辑
```

---

## 功能特性

### 输入支持

| 输入类型 | 来源 | 必需 |
|---------|------|------|
| 论文源码 | `overleaf/` 目录 | ✅ |
| 项目网站 | URL | ✅ |
| 参考海报 | `references/` 目录 | 可选 |
| 作者网站 | URL | 可选（用于 Logo） |

### 输出文件

```
poster/
├── index.html              # 交互式海报（主文件）
├── poster-config.json      # 布局配置
├── poster.pdf              # 导出 PDF
├── logos/                  # 机构 Logo
├── figures/                # 图表文件
├── qr.png                  # 项目页二维码
└── qr-posterskill.png      # Posterskill 二维码
```

### 交互编辑器功能

- **拖拽列分隔线** - 调整列宽
- **拖拽行分隔线** - 调整卡片高度
- **点击菱形按钮** - 交换卡片位置
- **A-/A+ 按钮** - 全局字体缩放
- **Preview 模式** - 预览打印效果
- **Copy Config** - 导出布局配置

---

## 架构

```
┌─────────────────────────────────────────────────────────────┐
│                    MOFA-POSTER 海报生成流程                  │
└─────────────────────────────────────────────────────────────┘

User Input
    ↓
┌─────────────────────────────────────────────────────────────┐
│ 1. 内容提取                                                  │
│    ────────                                                  │
│    • 读取 overleaf/*.tex（主文件 + \input{}）                │
│    • 提取：标题、作者、摘要、方法、结果、结论                  │
│    • WebFetch 项目网站抓图和链接                             │
└─────────────────────────┬───────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. 资源准备                                                  │
│    ────────                                                  │
│    • PDF 转 PNG（sips -Z 3000）                              │
│    • Playwright 下载网页图片                                 │
│    • 测量图片宽高比（sips -g pixelWidth/Height）             │
│    • 生成二维码（qrserver API）                              │
└─────────────────────────┬───────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. 布局优化                                                  │
│    ────────                                                  │
│    • 根据宽高比分配图片到合适列                              │
│    • Playwright 自动测量空白区域                             │
│    • 遍历列宽组合寻找最优布局                                │
│    • 最小化 whitespace                                       │
└─────────────────────────┬───────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. 生成海报                                                  │
│    ────────                                                  │
│    • 基于 React CDN 的交互式 HTML                            │
│    • CARD_REGISTRY：定义卡片内容                             │
│    • DEFAULT_LAYOUT：列结构和卡片顺序                        │
│    • 自适应视口缩放（translate + scale）                     │
│    • @media print 优化打印样式                               │
└─────────────────────────┬───────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. 输出                                                      │
│    ────                                                      │
│    • poster/index.html（交互编辑器）                         │
│    • poster/poster.pdf（Playwright 导出）                    │
│    • poster/poster-config.json（布局配置）                   │
└─────────────────────────────────────────────────────────────┘
```

---

## 技术细节

### 关键命令

```bash
# PDF 转高分辨率 PNG
sips -s format png input.pdf --out output.png -Z 3000

# 测量图片尺寸
sips -g pixelWidth -g pixelHeight poster/*.png

# 生成二维码
curl -sL -o qr.png "https://api.qrserver.com/v1/create-qr-code/?size=400x400&data=URL"
```

### Playwright 自动化

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto('file://poster/index.html')

    # 测量空白
    waste = page.evaluate('window.posterAPI.getWaste()')

    # 优化列宽
    page.evaluate('window.posterAPI.setColumnWidth("col1", 300)')

    # 导出 PDF
    page.pdf(path='poster.pdf', width='841mm', height='594mm',
             margin={'top':'0','right':'0','bottom':'0','left':'0'},
             print_background=True)

    browser.close()
```

### 图片宽高比策略

| 宽高比 | 类型 | 最佳列 |
|--------|------|--------|
| > 2:1 | 宽图（架构图） | 最宽列 |
| ~1:1 | 方图（实验结果） | 中等列 |
| < 1:1 | 竖图（示意图） | 最窄列 |

---

## 故障排除

### 常见问题

| 问题 | 解决方案 |
|------|---------|
| `playwright not found` | `pip3 install playwright && playwright install` |
| `sips: image not found` | 确保输入文件存在且为 PDF/图片 |
| 图片下载失败 | 使用 Playwright 而非 curl（处理跳转） |
| 海报空白太多 | 调整列宽或交换卡片位置 |
| 打印时样式丢失 | 勾选"背景图形"选项 |

### 字体太小/太大

- 使用 A-/A+ 按钮实时调整
- 或修改 `DEFAULT_FONT_SCALE`（默认 1.3）

### 图片模糊

- 检查 PDF 转换分辨率（-Z 3000）
- 确保使用 `object-fit: contain` 而非 max-width

---

## 相关 Skills

### mofa-vercel-web
**组合使用：**
```
mofa-poster: 生成海报
mofa-vercel-web: 部署海报到线上
```

### mofa-firecrawl / mofa-defuddle
**组合使用：**
```
mofa-firecrawl: 获取论文网页内容
mofa-poster: 基于内容生成海报
```

---

## 最佳实践

1. **内容精简** - 海报是视觉展示，用要点而非段落
2. **图片优先** - 大图表 + 简短说明，让观众 2 分钟看懂
3. **参考风格** - 放入 `references/` 参考海报让 Claude 匹配风格
4. **迭代优化** - 先用 Claude 生成，再手动微调布局
5. **测试打印** - Preview 模式下打印为 PDF 验证效果

---

## 致谢

本 Skill 基于 [ethanweber/posterskill](https://github.com/ethanweber/posterskill) 适配为 MoFA 格式。
