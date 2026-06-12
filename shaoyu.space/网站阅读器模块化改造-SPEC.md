# SPEC：阅读器模块化改造

> 基于 PRD（网站阅读器模块化改造-PRD.md）编写

---

## 1. 交付物清单

| 文件 | 动作 | 说明 |
|------|------|------|
| `common/reader.html` | **新建** | 统一阅读器入口，加载 CSS + data.js + JS |
| `common/reader.css` | **新建** | 通用阅读器样式（CSS变量驱动主题色） |
| `common/reader.js` | **新建** | 渲染器 + 导航 + 加载逻辑 |
| `engine/data.js` | **新建** | 配置 engine 章节 + 颜色 |
| `trilogy/data.js` | **新建** | 配置 trilogy 章节 + 颜色 |
| `novel/data.js` | **新建** | 配置 novel 章节 + 颜色 |
| `engine-reader.html` | **修改** | 改为重定向壳 |
| `trilogy/reader.html` | **修改** | 改为重定向壳 |
| `novel/reader.html` | **修改** | 改为重定向壳 |
| `index.html` | **不改** | 首页不变 |
| 各项目 `index.html` | **不改** | 总览页不变 |

---

## 2. data.js 格式规范

每个项目根目录下的 `data.js` 暴露一个全局变量 `PROJECT`：

```js
const PROJECT = {
  title: '项目名称',
  emoji: '🔧',                     // 顶部导航显示的图标
  color: {
    primary: '#00d4aa',            // 主题色（标题、链接、高亮、侧栏激活色）
    secondary: '#f5a623',          // 备用色（当前未用，保留）
    accentBg: 'rgba(0,212,170,0.04)',  // 引用块/轻高亮背景
    mediumBg: 'rgba(0,212,170,0.06)',  // 侧栏激活/行hover背景
    border: 'rgba(0,212,170,0.12)',    // 标题下边框/分隔线
  },
  chapters: [
    { file: 'engine/01-框架.md', title: '框架概述' },
    { file: 'engine/02-燃料路线三巨头.md', title: '燃料路线三巨头' },
    // ...
  ]
};
```

### 各项目颜色值

| 项目 | primary | accentBg | mediumBg | border |
|------|---------|----------|----------|--------|
| **engine** | `#00d4aa` | `rgba(0,212,170,0.04)` | `rgba(0,212,170,0.06)` | `rgba(0,212,170,0.12)` |
| **trilogy** | `#f5a623` | `rgba(245,166,35,0.04)` | `rgba(245,166,35,0.06)` | `rgba(245,166,35,0.12)` |
| **novel** | `#7c5cbf` | `rgba(124,92,191,0.04)` | `rgba(124,92,191,0.06)` | `rgba(124,92,191,0.12)` |

### 各项目章节数据

**engine**（来自现有 `engine-reader.html` 的 CHAPTERS + 配置）：
```js
const PROJECT = {
  title: '火箭发动机技术路线深度分析',
  emoji: '🔧',
  color: { primary: '#00d4aa', accentBg: 'rgba(0,212,170,0.04)', mediumBg: 'rgba(0,212,170,0.06)', border: 'rgba(0,212,170,0.12)' },
  chapters: [
    { file: 'engine/01-框架.md', title: '01 框架概述' },
    { file: 'engine/02-燃料路线三巨头.md', title: '02 燃料路线三巨头' },
    { file: 'engine/03-循环方式详解.md', title: '03 循环方式详解' },
    { file: 'engine/04-全球主力发动机.md', title: '04 全球主力发动机' },
    { file: 'engine/05-可回收对发动机的影响.md', title: '05 可回收对发动机的影响' },
    { file: 'engine/06-中国商业航天发动机格局.md', title: '06 中国商业航天发动机格局' },
    { file: 'engine/07-投资视角与结论.md', title: '07 投资视角与结论' }
  ]
};
```

**trilogy**：
```js
const PROJECT = {
  title: '减熵三部曲',
  emoji: '🧠',
  color: { primary: '#f5a623', accentBg: 'rgba(245,166,35,0.04)', mediumBg: 'rgba(245,166,35,0.06)', border: 'rgba(245,166,35,0.12)' },
  chapters: [
    { file: 'trilogy/01-认知减熵/article.md', title: '01 认知减熵——一个AI的自白' },
    { file: 'trilogy/02-管理人性/article.md', title: '02 管理的背后是人性的约束' },
    { file: 'trilogy/03-系统减熵/article.md', title: '03 复杂系统减熵' }
  ]
};
```

**novel**（注意 novel 原有的 reader.html 是加载独立 .html 文件的，本次改造**不改动**这一行为——novel 的 data.js 中的 chapters 使用 .html 路径，reader.js 直接用 fetch 加载html内容展示，或保持原有导航方式？）：
> ⚠️ novel 项目现有章节是 15 个独立 .html 文件（非 .md），各文件已包含完整样式。本次模块化改造的 reader 引擎支持 .md 渲染，**不承诺兼容 .html 文件的差异化解析**。
> **应对方案**：novel 的 reader 使用原有 reader.html（不改成重定向壳），仅 engine 和 trilogy 走模块化。novel 暂不接入。

---

## 3. reader.html 结构

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title id="pageTitle">加载中...</title>
  <link rel="stylesheet" href="/common/reader.css">
</head>
<body>
  <!-- 顶部导航 -->
  <header class="topbar">
    <button class="btn-menu" id="menuBtn">☰</button>
    <span class="topbar-title" id="topbarTitle">加载中...</span>
    <div class="topbar-actions">
      <a href="javascript:history.back()" class="btn-home">← 返回</a>
      <a href="/" class="btn-home">🏠 首页</a>
    </div>
  </header>

  <!-- 侧边栏覆盖 -->
  <div class="sidebar-overlay" id="overlay"></div>

  <!-- 侧边栏 -->
  <nav class="sidebar" id="sidebar">
    <div class="sidebar-section">📑 章节目录</div>
    <div id="chapterList"></div>  <!-- JS动态渲染 -->
  </nav>

  <!-- 主内容 -->
  <main class="main" id="main">
    <div class="content-wrap" id="content">
      <div class="loading">
        <div class="spinner"></div>
        <div class="loading-text">加载中...</div>
      </div>
    </div>
  </main>

  <script>
    // 从 URL 获取 project 参数
    const params = new URLSearchParams(window.location.search);
    const projectName = params.get('project') || 'engine';

    // 加载对应 data.js
    const script = document.createElement('script');
    script.src = `/${projectName}/data.js`;
    document.head.appendChild(script);

    script.onload = function() {
      // PROJECT 全局变量已就绪
      initReader(PROJECT, parseInt(params.get('chapter')) || 0);
    };
  </script>
  <script src="/common/reader.js"></script>
</body>
</html>
```

⚠️ 注意：`initReader()` 是 reader.js 暴露的入口函数。必须确保 data.js 加载完成后再初始化。

---

## 4. reader.css 规范

使用 CSS 自定义属性（变量）驱动主题色。页面根元素 `<html>` 无需额外 data 属性——主题色由 data.js 在初始化时通过 JS 写入 `<style id="theme-vars">`。

### JS 注入方式

```js
function applyTheme(color) {
  const style = document.createElement('style');
  style.id = 'theme-vars';
  style.textContent = `
    :root {
      --primary: ${color.primary};
      --accent-bg: ${color.accentBg};
      --medium-bg: ${color.mediumBg};
      --border: ${color.border};
    }
  `;
  document.head.appendChild(style);
}
```

### CSS 关键引用点

| 元素 | 原硬编码色值 | 改为 CSS 变量 |
|------|------------|-------------|
| 导航标题 `.topbar-title` | `#00d4aa` | `var(--primary)` |
| 侧栏激活 `.chapter-item.active` | `#00d4aa` | `var(--primary)` |
| 侧栏hover `.chapter-item:hover` | `rgba(0,212,170,0.04)` | `var(--accent-bg)` |
| 侧栏激活背景 `.chapter-item.active` | `rgba(0,212,170,0.06)` | `var(--medium-bg)` |
| 侧栏激活边框 `.chapter-item.active` | `border-left-color:#00d4aa` | `border-left-color:var(--primary)` |
| `h1` 下边框 | `rgba(0,212,170,0.12)` | `var(--border)` |
| `h2` 标题颜色 | `#00d4aa` | `var(--primary)` |
| 链接颜色 `.content a` | `#00d4aa` | `var(--primary)` |
| 引用块左边框 `.content blockquote` | `border-left-color:#00d4aa` | `border-left-color:var(--primary)` |
| 引用块背景 | `rgba(0,212,170,0.04)` | `var(--accent-bg)` |
| 代码高亮 `.content code` | `#00d4aa` | `var(--primary)` |
| 列表标记 `ul li::marker` | `#00d4aa` | `var(--primary)` |
| 表格表头 `th` | `#00d4aa` | `var(--primary)` |
| 进度数字 `.chapter-progress span` | `#00d4aa` | `var(--primary)` |
| 底部按钮hover `.btn-chapter:hover` | `#00d4aa` | `var(--primary)` |
| 重试按钮 `.btn-retry` | `#00d4aa` | `var(--primary)` |

其余颜色（背景色 #0a0a0f、文字色 #c8c8d0、侧栏背景 #14141e 等）保持全局不变。

---

## 5. reader.js 规范

### 入口函数

```js
function initReader(project, startChapter = 0) {
  // 1. 更新页面标题 + 导航标题
  document.title = project.title + ' · 阅读器';
  document.getElementById('topbarTitle').textContent = project.emoji + ' ' + project.title;

  // 2. 应用主题色
  applyTheme(project.color);

  // 3. 渲染侧栏章节列表
  renderChapterList(project.chapters);

  // 4. 加载并显示指定章节
  loadChapter(project, startChapter);
}
```

### 函数清单（保留自现有 engine-reader.html）

| 函数 | 改动 |
|------|------|
| `renderMarkdown(md)` → HTML | **不修改**，完整保留 |
| `splitTableRow(row)` | **不修改** |
| `escapeHtml(str)` | **不修改** |
| `applyTheme(color)` | **新增**，注入CSS变量 |
| `renderChapterList(chapters)` | **新增**，动态生成侧栏按钮 |
| `loadChapter(project, idx)` | **适配**，接受 project 参数替代 CHAPTERS 全局变量 |
| `renderContent(md, idx, project)` | **适配**，接受 project 参数 |
| `goChapter(idx, project)` | **适配** |
| `toggleSidebar()` / `closeSidebar()` | **不修改** |

### loadChapter 流程（关键）

```js
async function loadChapter(project, idx) {
  if (idx < 0 || idx >= project.chapters.length) return;
  currentChapter = idx;
  currentProject = project;  // 存为全局，供goChapter等使用

  // 更新侧栏高亮
  document.querySelectorAll('.chapter-item').forEach((item, i) => {
    item.classList.toggle('active', i === idx);
  });

  const chap = project.chapters[idx];

  // 缓存
  if (cachedContent[chap.file]) {
    renderContent(cachedContent[chap.file], idx, project);
    return;
  }

  // 显示加载
  contentEl.innerHTML = `<div class="loading">...`;

  try {
    const resp = await fetch(chap.file);
    if (!resp.ok) throw new Error('HTTP ' + resp.status);
    const md = await resp.text();
    cachedContent[chap.file] = md;
    renderContent(md, idx, project);
  } catch (err) {
    // 显示错误
    contentEl.innerHTML = `...错误信息...`;
  }
}
```

---

## 6. 重定向壳文件格式

以下三个旧文件替换为纯JS重定向壳：

### `engine-reader.html`
```html
<script>window.location.replace('/common/reader.html?project=engine');</script>
```

### `trilogy/reader.html`
```html
<script>window.location.replace('/common/reader.html?project=trilogy');</script>
```

### `novel/reader.html`
**不做改动**，novel 暂不接入模块化引擎，保持原有 reader。

---

## 7. 验收标准

### 7.1 内容一致性
- [ ] `?project=engine` 加载 engine 的 7 章内容，每个章节显示正确的 .md 文件
- [ ] `?project=trilogy` 加载 trilogy 的 3 章内容，每个章节显示正确的 .md 文件
- [ ] `?project=trilogy&chapter=1` 直接跳到第二部（人性约束）
- [ ] `?project=trilogy&chapter=2` 直接跳到第三部（系统减熵）

### 7.2 样式一致性
- [ ] engine 主题色为青绿（`#00d4aa`）
- [ ] trilogy 主题色为金色（`#f5a623`）
- [ ] novel 不接入，保持原有样式不变

### 7.3 导航一致性
- [ ] 侧栏高亮跟随当前章节
- [ ] ← → 键盘切换章节
- [ ] 底部"上一章/下一章"按钮正常
- [ ] mobile 响应式侧栏展开/收起
- [ ] 非首次访问使用缓存

### 7.4 向后兼容
- [ ] 旧链接 `https://shaoyu.space:18888/engine-reader.html` 重定向到 `common/reader.html?project=engine`
- [ ] 旧链接 `https://shaoyu.space:18888/trilogy/reader.html` 重定向到 `common/reader.html?project=trilogy`
- [ ] 重定向后的页面内容与改造前一致（7条vs3条章节）
- [ ] `https://shaoyu.space:18888/novel/reader.html` 保持原样

### 7.5 无回归
- [ ] `https://shaoyu.space:18888/` 首页正常，各卡片链接正常
- [ ] `https://shaoyu.space:18888/engine/` 总览页正常
- [ ] `https://shaoyu.space:18888/trilogy/` 总览页正常（卡片链接已更新为 `common/reader.html?project=trilogy&chapter=N`）
- [ ] 总览页三部卡片分别跳转到对应章节

---

## 8. 数据保留

所有原始文件不变：
- `engine/*.md` — 保留
- `trilogy/*/article.md` — 保留
- `novel/第*.html` — 保留
- 原始 `engine-reader.html` 改造为壳，不改名

若需回溯原始阅读器：查看 git 历史或 `shaoyu.space/archive/` 下的备份。
