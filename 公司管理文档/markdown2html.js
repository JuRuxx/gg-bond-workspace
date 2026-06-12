#!/usr/bin/env node
/**
 * markdown2html — 把 Markdown 文件转成 A4 风格可打印 HTML
 *
 * 用法：
 *   node markdown2html.js <输入文件.md>
 *   输出同目录同名 .html
 *
 * 样式：深蓝色 #1a5276 系列，A4 尺寸，和产线管理流程摘要 / 报修流程说明一致
 */

const fs = require('fs');
const path = require('path');

// ─── 行级标记处理 ──────────────────────────────────
function inline(md) {
  let s = md;
  // 转义
  s = s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  // 行内代码
  s = s.replace(/`([^`]+)`/g, '<code>$1</code>');
  // 加粗
  s = s.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  // 斜体
  s = s.replace(/\*(.+?)\*/g, '<em>$1</em>');
  return s;
}

// ─── 表格解析 ──────────────────────────────────────
function parseTable(lines, idx) {
  // lines[idx] 是表头行, idx+1 是分隔行
  const header = lines[idx];
  const sep = lines[idx + 1];
  const rows = [header, sep];
  let i = idx + 2;
  while (i < lines.length && lines[i].startsWith('|')) {
    rows.push(lines[i]);
    i++;
  }
  const aligns = sep.split('|').map(cell => {
    const t = cell.trim();
    if (t.startsWith(':') && t.endsWith(':')) return 'center';
    if (t.endsWith(':')) return 'right';
    return 'left';
  });

  const trs = rows.map((row, ri) => {
    if (ri === 1) return null; // 跳过分隔行
    const cells = row.split('|').filter((_, ci) => ci > 0 && ci < row.split('|').length - 1);
    const tag = ri === 0 ? 'th' : 'td';
    return `<tr>${cells.map((c, ci) => {
      const a = aligns[ci] || 'left';
      const style = a !== 'left' ? ` style="text-align:${a}"` : '';
      return `<${tag}${style}>${inline(c.trim())}</${tag}>`;
    }).join('')}</tr>`;
  }).filter(Boolean).join('\n');

  return `<table>\n${trs}\n</table>`;
}

// ─── 代码块解析 ────────────────────────────────────
function parseCodeBlock(lines, idx) {
  const lang = lines[idx].slice(3).trim();
  let code = [];
  let i = idx + 1;
  while (i < lines.length && !lines[i].startsWith('```')) {
    code.push(lines[i]);
    i++;
  }
  return { html: `<pre><code>${code.join('\n')}</code></pre>`, endIdx: i };
}

// ─── 主转换 ────────────────────────────────────────
function md2html(md) {
  const lines = md.split('\n');
  const out = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    // 空行
    if (line.trim() === '') {
      i++;
      continue;
    }

    // 代码块
    if (line.startsWith('```')) {
      const { html, endIdx } = parseCodeBlock(lines, i);
      out.push(html);
      i = endIdx + 1;
      continue;
    }

    // 水平线
    if (/^---+\s*$/.test(line)) {
      out.push('<hr>');
      i++;
      continue;
    }

    // 表格
    if (line.startsWith('|') && i + 1 < lines.length && lines[i + 1].startsWith('|') && lines[i + 1].includes('---')) {
      const table = parseTable(lines, i);
      out.push(table);
      // 跳过表格所有行
      while (i < lines.length && lines[i].startsWith('|')) i++;
      continue;
    }

    // 标题
    const hMatch = line.match(/^(#{1,6})\s+(.+)/);
    if (hMatch) {
      const level = hMatch[1].length;
      const text = inline(hMatch[2]);
      out.push(`<h${level}>${text}</h${level}>`);
      i++;
      continue;
    }

    // 引用
    if (line.startsWith('> ')) {
      out.push(`<blockquote>${inline(line.slice(2))}</blockquote>`);
      i++;
      continue;
    }

    // 有序列表
    if (/^\d+\.\s/.test(line)) {
      const items = [];
      while (i < lines.length && /^\d+\.\s/.test(lines[i])) {
        items.push(`<li>${inline(lines[i].replace(/^\d+\.\s/, ''))}</li>`);
        i++;
      }
      out.push(`<ol>${items.join('\n')}</ol>`);
      continue;
    }

    // 无序列表
    if (/^[-*+]\s/.test(line)) {
      const items = [];
      while (i < lines.length && /^[-*+]\s/.test(lines[i])) {
        items.push(`<li>${inline(lines[i].replace(/^[-*+]\s/, ''))}</li>`);
        i++;
      }
      out.push(`<ul>${items.join('\n')}</ul>`);
      continue;
    }

    // 普通段落
    const paras = [];
    while (i < lines.length && lines[i].trim() !== '' && !lines[i].startsWith('```') && !lines[i].startsWith('|') && !/^---+\s*$/.test(lines[i]) && !/^#{1,6}\s/.test(lines[i]) && !/^> /.test(lines[i]) && !/^\d+\.\s/.test(lines[i]) && !/^[-*+]\s/.test(lines[i])) {
      paras.push(lines[i]);
      i++;
    }
    if (paras.length > 0) {
      out.push(`<p>${paras.map(p => inline(p)).join('<br>')}</p>`);
    }
  }

  return out.join('\n');
}

// ─── A4 打印样式模板（深蓝 #1a5276 系） ──────────
function buildTemplate(body, title) {
  return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<style>
@page { size: A4; margin: 0; }
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif; color: #222; }

.page {
  width: 210mm;
  min-height: 297mm;
  padding: 18mm 16mm;
  position: relative;
}

h1 {
  font-size: 18pt;
  color: #1a5276;
  letter-spacing: 1px;
  border-bottom: 2.5px solid #1a5276;
  padding-bottom: 6mm;
  margin-bottom: 6mm;
}
h2 {
  font-size: 12pt;
  font-weight: bold;
  color: #1a5276;
  padding: 4mm 0 2mm 0;
}
h3 {
  font-size: 10.5pt;
  font-weight: bold;
  color: #1a5276;
  padding: 3mm 0 1.5mm 0;
}
h4 { font-size: 10pt; font-weight: bold; color: #333; padding: 2mm 0 1mm 0; }
h5, h6 { font-size: 9.5pt; font-weight: bold; color: #555; padding: 1.5mm 0 1mm 0; }

table { width: 100%; border-collapse: collapse; font-size: 9pt; margin-bottom: 3mm; }
th { background: #1a5276; color: #fff; text-align: center; padding: 3mm 2mm; font-weight: 600; }
td { border: 1px solid #bbb; padding: 2.2mm 2mm; vertical-align: top; }
tr:nth-child(even) td { background: #f6f9fc; }

p { font-size: 9pt; line-height: 1.7; margin: 2mm 0; }

ul, ol {
  margin: 1.5mm 0 1.5mm 4mm;
  font-size: 9pt;
  line-height: 1.6;
}
li { margin-bottom: 0.5mm; }

pre {
  background: #f4f4f4;
  padding: 12px 16px;
  border-radius: 4px;
  overflow-x: auto;
  font-size: 8.5pt;
  margin: 3mm 0;
  line-height: 1.6;
  font-family: 'Courier New', 'Menlo', monospace;
}
code {
  background: #f0f0f0;
  padding: 1px 4px;
  border-radius: 3px;
  font-size: 8.5pt;
  font-family: 'Courier New', 'Menlo', monospace;
}
pre code { background: none; padding: 0; }

blockquote {
  border-left: 4px solid #999;
  padding: 6px 16px;
  margin: 3mm 0;
  color: #555;
  background: #f9f9f9;
  font-size: 9pt;
  line-height: 1.6;
}

hr { margin: 5mm 0; border: none; border-top: 1.5px solid #ccc; }

@media print {
  body { padding: 0; }
  .page { page-break-after: always; }
  h1, h2, h3 { page-break-after: avoid; }
  table { page-break-inside: auto; }
  tr { page-break-inside: avoid; }
}
</style>
</head>
<body>
<div class="page">
${body}
</div>
</body>
</html>`;
}

// ─── 主流程 ────────────────────────────────────────
const input = process.argv[2];
if (!input) {
  console.error('用法: node markdown2html.js <文件.md>');
  process.exit(1);
}

const mdPath = path.resolve(input);
if (!fs.existsSync(mdPath)) {
  console.error(`文件不存在: ${mdPath}`);
  process.exit(1);
}

const md = fs.readFileSync(mdPath, 'utf-8');
const body = md2html(md);
const filename = path.basename(mdPath, '.md');
const outPath = path.join(path.dirname(mdPath), `${filename}.html`);

const html = buildTemplate(body, filename);

fs.writeFileSync(outPath, html, 'utf-8');
console.log(`✅ 已生成: ${outPath}`);
