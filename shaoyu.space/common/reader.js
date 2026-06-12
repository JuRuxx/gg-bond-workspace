/* ===========================================================
   通用阅读器引擎 · 超人强 出品 💪🔥
   支持项目注入、主题色切换、markdown渲染、键盘导航
   =========================================================== */

// ===== 全局状态 =====
let currentProject = null;
let currentChapter = 0;
let cachedContent = {};
let chapterItems = []; // 动态渲染后更新

const contentEl = document.getElementById('content');
const sidebarEl = document.getElementById('sidebar');
const overlayEl = document.getElementById('overlay');
const menuBtn = document.getElementById('menuBtn');
const mainEl = document.getElementById('main');

// ===== 入口 =====
function initReader(project, startChapter = 0) {
  currentProject = project;
  
  // 从URL参数读取章节索引（覆盖默认值）
  const params = new URLSearchParams(window.location.search);
  const chapterParam = params.get('chapter');
  if (chapterParam !== null) {
    const parsed = parseInt(chapterParam, 10);
    if (!isNaN(parsed) && parsed >= 0 && parsed < project.chapters.length) {
      startChapter = parsed;
    }
  }
  currentChapter = startChapter;

  // 更新标题
  document.title = project.title + ' · 阅读器';
  document.getElementById('topbarTitle').textContent = (project.emoji || '📄') + ' ' + project.title;

  // 注入主题色
  applyTheme(project.color);

  // 渲染侧栏
  renderChapterList(project.chapters);

  // 绑定侧栏事件（需等待 DOM 渲染）
  bindChapterEvents();

  // 绑定顶部菜单按钮
  if (menuBtn) {
    menuBtn.addEventListener('click', toggleSidebar);
    menuBtn.style.display = 'flex'; // 移动端才需显示，但预先绑定
  }
  if (overlayEl) {
    overlayEl.addEventListener('click', closeSidebar);
  }

  // 绑定键盘快捷键
  bindKeyboardEvents();

  // 加载章节
  loadChapter(currentChapter);
}

// ===== 主题色注入 =====
function applyTheme(color) {
  // 清除旧主题样式
  const old = document.getElementById('theme-vars');
  if (old) old.remove();

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

// ===== 侧栏渲染（支持 volumes 分组） =====
function renderChapterList(chapters) {
  const container = document.getElementById('chapterList');
  if (!container) return;

  // 如果项目有 volumes 字段，按卷分组渲染
  if (currentProject.volumes && currentProject.volumes.length > 0) {
    const vlines = [];
    let globalIdx = 0;
    currentProject.volumes.forEach((vol) => {
      vlines.push('<div class="volume-label">' + vol.label + '</div>');
      vol.chapters.forEach((chap) => {
        const num = String(globalIdx + 1).padStart(2, '0');
        vlines.push('<button class="chapter-item' + (globalIdx === currentChapter ? ' active' : '') + '" data-chapter="' + globalIdx + '">' +
          '<span class="chapter-num">' + num + '</span> ' + chap.title +
        '</button>');
        globalIdx++;
      });
    });
    container.innerHTML = vlines.join('');
    chapterItems = container.querySelectorAll('.chapter-item');
    return;
  }

  // 无 volumes 字段，保持原有的扁平列表
  const items = chapters.map((chap, idx) => {
    const num = String(idx + 1).padStart(2, '0');
    return `<button class="chapter-item${idx === currentChapter ? ' active' : ''}" data-chapter="${idx}">
      <span class="chapter-num">${num}</span> ${chap.title}
    </button>`;
  }).join('');

  container.innerHTML = items;
  chapterItems = container.querySelectorAll('.chapter-item');
}

function bindChapterEvents() {
  chapterItems.forEach((item) => {
    item.addEventListener('click', () => {
      const idx = parseInt(item.dataset.chapter);
      if (idx !== currentChapter) {
        goChapter(idx);
      } else {
        closeSidebar();
      }
    });
  });
}

// ===== Markdown → HTML 渲染器 =====
/* 完全保留自 engine-reader.html，不做修改 */
function renderMarkdown(md) {
  if (!md) return '';
  let html = md;

  // 1. 代码块（保护）
  const codeBlocks = [];
  html = html.replace(/```(\w*)\n([\s\S]*?)```/g, (m, lang, code) => {
    const idx = codeBlocks.length;
    codeBlocks.push(`<pre><code class="language-${lang}">${escapeHtml(code.trim())}</code></pre>`);
    return `%%CODEBLOCK_${idx}%%`;
  });

  // 2. 行内代码
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

  // 3. 图片 ![](url)
  html = html.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, '<img src="$2" alt="$1" style="max-width:100%;border-radius:8px;margin:16px 0;">');

  // 4. 链接 [text](url)
  html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>');

  // 5. 水平线
  html = html.replace(/^---+/gm, '<hr>');

  // 6. 引用块
  html = html.replace(/^> (.+)$/gm, '<blockquote><p>$1</p></blockquote>');
  // 合并相邻引用块
  html = html.replace(/<\/blockquote>\s*<blockquote>/g, '\n');
  html = html.replace(/<blockquote>\s*<p>([\s\S]*?)<\/p>\s*<\/blockquote>/g, (m, content) => {
    const lines = content.split(/\n/).filter(l => l.trim());
    return `<blockquote>${lines.map(l => `<p>${l}</p>`).join('')}</blockquote>`;
  });

  // 7. 表格
  html = html.replace(/^(\|.+\|)\n(\|[-:| ]+\|)\n((?:\|.+\|\n?)*)/gm, (match) => {
    const lines = match.trim().split('\n');
    if (lines.length < 3) return match;
    const headerCells = splitTableRow(lines[0]);
    const bodyRows = lines.slice(2).filter(l => l.trim());
    let thead = `<thead><tr>${headerCells.map(c => `<th>${c}</th>`).join('')}</tr></thead>`;
    let tbody = `<tbody>${bodyRows.map(row => {
      const cells = splitTableRow(row);
      return `<tr>${cells.map(c => `<td>${c}</td>`).join('')}</tr>`;
    }).join('')}</tbody>`;
    return `<div class="table-wrap"><table>${thead}${tbody}</table></div>`;
  });

  // 8. 标题 (从大到小，避免嵌套匹配)
  html = html.replace(/^#### (.+)$/gm, '<h4>$1</h4>');
  html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
  html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
  html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');

  // 9. 无序列表 - 处理连续的行
  html = html.replace(/^- (.+)$/gm, '<li>$1</li>');
  html = html.replace(/((?:<li>.*<\/li>\n?)+)/g, '<ul>$1</ul>');

  // 10. 有序列表 - 处理连续的行
  html = html.replace(/^\d+\.\s(.+)$/gm, '<oli>$1</oli>');
  html = html.replace(/((?:<oli>.*<\/oli>\n?)+)/g, (m) => {
    return '<ol>' + m.replace(/<oli>/g, '<li>').replace(/<\/oli>/g, '</li>') + '</ol>';
  });

  // 11. 粗体
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');

  // 12. 段落（没有被任何标签包裹的文本行）
  html = html.replace(/^(?!<[hulopbdi\/\s]|$)(.+)$/gm, '<p>$1</p>');

  // 13. 恢复代码块
  html = html.replace(/%%CODEBLOCK_(\d+)%%/g, (m, idx) => codeBlocks[parseInt(idx)]);

  // 清理多余换行
  html = html.replace(/\n{3,}/g, '\n\n');

  return html;
}

function splitTableRow(row) {
  return row.split('|').filter((c,i,a) => i > 0 && i < a.length - 1).map(c => c.trim());
}

function escapeHtml(str) {
  return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// ===== 加载 & 渲染章节 =====
async function loadChapter(idx) {
  const project = currentProject;
  if (!project) return;
  if (idx < 0 || idx >= project.chapters.length) return;
  currentChapter = idx;

  // 更新侧栏高亮
  chapterItems.forEach((item, i) => {
    item.classList.toggle('active', i === idx);
  });

  const chap = project.chapters[idx];
  // 用相对路径：从当前页面位置推导到根的相对路径
  const depth = (window.location.pathname.match(/\//g) || []).length - 1;
  const filePath = '../'.repeat(depth) + chap.file;

  // 如果有缓存直接用
  if (cachedContent[filePath]) {
    renderContent(cachedContent[filePath], idx);
    return;
  }

  // 显示加载状态
  contentEl.innerHTML = `
    <div class="loading">
      <div class="spinner"></div>
      <div class="loading-text">加载 ${chap.title}……</div>
    </div>
  `;

  try {
    const resp = await fetch(filePath);
    if (!resp.ok) throw new Error('HTTP ' + resp.status + ' ' + resp.statusText);
    const md = await resp.text();
    cachedContent[filePath] = md;
    renderContent(md, idx);
  } catch (err) {
    contentEl.innerHTML = `
      <div class="error-msg">
        <div class="emoji">💥</div>
        <h2>加载失败</h2>
        <p>无法读取 <code>${escapeHtml(filePath)}</code></p>
        <p class="err-detail">${escapeHtml(err.message)}</p>
        <button class="btn-retry" onclick="loadChapter(${idx})">重新加载</button>
      </div>`;
  }
}

function renderContent(md, idx) {
  const project = currentProject;
  if (!project) return;

  const html = renderMarkdown(md);

  // 底部导航
  const prevDisabled = idx === 0 ? 'disabled' : '';
  const nextDisabled = idx === project.chapters.length - 1 ? 'disabled' : '';
  const prevLabel = idx > 0 ? project.chapters[idx - 1].title.slice(3) : '上一章';
  const nextLabel = idx < project.chapters.length - 1 ? project.chapters[idx + 1].title.slice(3) : '下一章';
  const progressHTML = `
    <div class="bottom-nav">
      <button class="btn-chapter" id="prevBtn" ${prevDisabled}>
        ← ${prevLabel}
      </button>
      <div class="chapter-progress">
        <span>${idx + 1}</span> / ${project.chapters.length}
      </div>
      <button class="btn-chapter" id="nextBtn" ${nextDisabled}>
        ${nextLabel} →
      </button>
    </div>
  `;

  contentEl.innerHTML = `<div class="content">${html}</div>${progressHTML}`;

  // 绑定底部按钮
  document.getElementById('prevBtn')?.addEventListener('click', () => goChapter(idx - 1));
  document.getElementById('nextBtn')?.addEventListener('click', () => goChapter(idx + 1));

  // 更新文档标题
  document.title = project.chapters[idx].title + ' · ' + project.title;

  // 滚动到顶部
  if (mainEl) mainEl.scrollTop = 0;
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function goChapter(idx) {
  if (!currentProject) return;
  if (idx < 0 || idx >= currentProject.chapters.length) return;
  loadChapter(idx);
  closeSidebar();
}

// ===== 侧边栏 =====
function toggleSidebar() {
  sidebarEl.classList.toggle('open');
  overlayEl.classList.toggle('show');
}

function closeSidebar() {
  sidebarEl.classList.remove('open');
  overlayEl.classList.remove('show');
}

// ===== 键盘快捷键 =====
function bindKeyboardEvents() {
  document.addEventListener('keydown', (e) => {
    // 避免在输入框中触发
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
    if (e.key === 'ArrowLeft') {
      if (currentChapter > 0) goChapter(currentChapter - 1);
    } else if (e.key === 'ArrowRight') {
      if (currentChapter < currentProject.chapters.length - 1) goChapter(currentChapter + 1);
    }
  });
}
