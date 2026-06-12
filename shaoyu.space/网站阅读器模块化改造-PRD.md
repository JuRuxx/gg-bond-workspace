# PRD：shaoyu.space 阅读器模块化改造

## 1. 项目背景

shaoyu.space 上现有三个研究/创作项目，各有一套独立的阅读器：
- **engine/** — 火箭发动机技术路线分析（1个HTML文件，770行）
- **trilogy/** — 减熵三部曲（1个HTML文件，762行）
- **novel/** — 加班管理局小说（1个HTML文件，368行）
- **其它** — tianbing-reader.html 等散落文件

每个阅读器都独立复制了整套 CSS + Markdown 渲染器 + JS 逻辑，导致：
- 代码高度冗余（核心渲染器、导航逻辑完全一样，只 CHAPTERS 数据不同）
- 改一个 bug 要改三四个文件
- 新的项目（比如后续的研究报告）又得重新造轮子

## 2. 目标

将阅读器引擎模块化，实现 **一份引擎，多项目复用**。同时利用这次重构为每个项目增加主题色，让浏览页标题和各栏内容呈现项目特色。

## 3. 范围

**包含：**
3.1. 提取共用 reader 引擎为独立文件（CSS + JS）
3.2. 每个项目提供独立的 `data.js` 配置文件
3.3. 读者通过 `reader.html?project=engine|trilogy|novel` 访问
3.4. 每个项目支持主题色配置（标题颜色、强调色、侧栏高亮色）
3.5. 保持向后兼容：现有的 `/engine-reader.html`、`/trilogy/reader.html`、`/novel/reader.html` 重定向或内联跳转

**不包含：**
- 首页 index.html 不改
- 项目总览页（engine/index.html、trilogy/index.html、novel/index.html）不改
- Markdown 渲染器逻辑不改变（只移动位置，不改功能）
- 不引入打包工具或构建步骤

## 4. 架构设计

### 4.1 文件结构

```
shaoyu.space/
├── common/
│   ├── reader.html       ← 统一的阅读器引擎（入口）
│   ├── reader.css        ← 阅读器通用样式
│   └── reader.js         ← 阅读器逻辑（Markdown渲染+导航+加载）
├── engine/
│   ├── data.js           ← 项目配置（章节数据+主题色）
│   ├── 01-框架.md ...
│   └── index.html        ← 总览页（不变）
├── trilogy/
│   ├── data.js           ← 项目配置（章节数据+主题色）
│   ├── 01-认知减熵/article.md ...
│   └── index.html        ← 总览页（不变）
├── novel/
│   ├── data.js           ← 项目配置（章节数据+主题色）
│   ├── 第01章-第17次面试.html ...
│   └── index.html        ← 总览页（不变）
├── index.html            ← 首页（不变）
└── Caddyfile
```

### 4.2 配置格式（data.js）

```js
// engine/data.js — 示例
const PROJECT = {
  title: '火箭发动机技术路线深度分析',
  emoji: '🔧',
  color: {
    primary: '#00d4aa',         // 主题色（标题、链接、高亮）
    accent: 'rgba(0,212,170,...)', // 强调色背景
    bgLight: 'rgba(0,212,170,0.04)',
    bgMedium: 'rgba(0,212,170,0.06)',
    border: 'rgba(0,212,170,0.12)'
  },
  chapters: [
    { file: 'engine/01-框架.md', title: '框架概述' },
    { file: 'engine/02-燃料路线三巨头.md', title: '燃料路线三巨头' },
    // ...
  ]
};
```

### 4.3 颜色方案

| 项目 | 主题色（primary） | 风格 |
|------|------------------|------|
| engine（发动机） | `#00d4aa` 青绿色 | 科技感、冷色调 |
| trilogy（三部曲） | `#f5a623` 金色 | 温暖、思考感 |
| novel（小说） | `#7c5cbf` 紫色（迷糊老师建议） | 故事感、沉浸感 |

> ⚠️ 注：novel主题色需主人最终确认，当前暂定 `#7c5cbf`（紫色），确认后写入SPEC。

## 5. 用户路径

### 现有路径（保持兼容）

方案：旧文件保留为**重定向壳**，内容仅一段JS做 `window.location.replace`：

```
<!-- engine-reader.html / trilogy/reader.html / novel/reader.html 统一替换为： -->
<script>window.location.replace('/common/reader.html?project=engine');</script>
```

三处旧链接各自指向对应 project 参数。

**不修改Caddyfile**，不涉及服务端301。纯JS前端重定向，保证收藏夹/书签跳转后URL自动更新。

> 注意：`novel/` 下的章节HTML文件（如 `第01章-第17次面试.html`）保留不动，novel原有reader仍指向这些静态HTML——本次模块化的reader引擎只负责用 fetch 加载 .md 文件的内容。

### 新访问路径

```
首页 → 总览页(/trilogy/) → 卡片 → /common/reader.html?project=trilogy&chapter=0|1|2
```

`chapter` 参数对应 data.js 中 chapters 数组的索引（0开始），缺省值 = 0 加载第一章。等待 SPEC 中定义 reader.js 解析逻辑。

## 6. 时间估计

- SPEC 编写：0.5h
- 编码实施：2h（含三套 data.js + 颜色调试）
- 验收测试：1h（每个项目逐一验证）
- **总计：约 3.5h**

## 7. 风险

- 必须确保三套现有数据完全兼容（**验收标准**：旧链接打开后 a)内容一致 b)样式一致 c)翻页/导航一致）
- 重定向不能破坏用户已打开的链接（特别是收藏夹里的）
- 颜色方案需要视觉上和谐，不能太抢眼
