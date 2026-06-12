#!/usr/bin/env python3
"""
设备保养看板生成器
input: CSV → output: PNG看板图（适合发微信群）

用法:
    python3 plan_board.py                      # 用默认sample.csv
    python3 plan_board.py my_plan.csv           # 用自己的CSV
    python3 plan_board.py my_plan.csv --title "🔧 6月第一周保养计划"
"""

import csv
import sys
import os
from datetime import datetime

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.font_manager import FontProperties, findfont, FontManager
import numpy as np

# ── 字体 ──────────────────────────────────────────────
# Try common Chinese fonts
CHINESE_FONTS = [
    'PingFang SC', 'PingFang', 'Heiti SC', 'Heiti TC',
    'STHeiti', 'Microsoft YaHei', 'SimHei',
    'WenQuanYi Micro Hei', 'Noto Sans CJK SC', 'Noto Sans SC',
    'Apple LiGothic', 'LiHei Pro',
]


def find_chinese_font():
    """Find an available Chinese font"""
    fm = FontManager()
    available = {f.name for f in fm.ttflist}

    for font in CHINESE_FONTS:
        if font in available:
            try:
                fp = FontProperties(family=font)
                findfont(fp, fallback_to_default=False)
                return font
            except Exception:
                continue

    # Fallback: try to find any font that contains Chinese chars
    for f in fm.ttflist:
        if any(c in f.name for c in ['Hei', 'Song', 'Ming', 'Fang', 'Kai', 'Noto', 'CJK', 'PingFang', 'YaHei']):
            try:
                fp = FontProperties(family=f.name)
                findfont(fp, fallback_to_default=False)
                return f.name
            except Exception:
                continue

    return None


# ── Color schemes ─────────────────────────────────────
# 整体配色灵感：莫兰迪柔和色系 + 低饱和活力色
# 色调柔和但有辨识度，不张扬不刺眼

# 页面背景
BG_PAGE = '#F5F6F8'       # 柔和灰白
BG_HEADER = '#2C3E50'      # 深蓝灰表头（比纯黑柔和）
TEXT_HEADER = '#FFFFFF'    # 表头白字
TEXT_TITLE = '#2C3E50'     # 标题深色
TEXT_SUBTITLE = '#7B8A8B'  # 副标题灰色

# 行背景交替
ROW_EVEN = '#FFFFFF'
ROW_ODD = '#F8F9FB'
ROW_BORDER = '#E8ECF0'

PRIORITY_COLORS = {
    'P0': {'bg': '#FDECEA', 'fg': '#C0392B', 'tag': '#E74C3C'},
    'P1': {'bg': '#FEF5E7', 'fg': '#D68910', 'tag': '#F39C12'},
    'P2': {'bg': '#EBF5FB', 'fg': '#1A5276', 'tag': '#2980B9'},
}

# 进度条配色
PROGRESS_COLORS = {
    'high': '#27AE60',    # >= 90% 深绿色
    'mid':  '#2E86C1',    # >= 30% 蓝色
    'low':  '#95A5A6',    # < 30% 灰色
}
PROGRESS_BG = '#E8ECF0'  # 进度条背景


def parse_csv(filepath):
    """Parse CSV and return list of dicts"""
    rows = []
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            prio = row.get('优先级', '').strip().upper()

            # Parse progress (0-100 integer)
            try:
                progress = int(row.get('进度', '0').strip())
            except ValueError:
                progress = 0
            progress = max(0, min(100, progress))

            rows.append({
                'priority': prio if prio in ('P0', 'P1', 'P2') else 'P2',
                'project': row.get('项目', '').strip(),
                'content': row.get('内容', '').strip(),
                'owner': row.get('负责人', '').strip(),
                'due': row.get('交付日期', '').strip(),
                'progress': progress,
            })
    return rows


def generate_board(rows, title=None, output_path=None):
    """Generate a beautiful kanban board image from CSV data"""

    # ── Figure setup ──
    font_name = find_chinese_font()
    if font_name:
        plt.rcParams['font.family'] = font_name
    plt.rcParams['axes.unicode_minus'] = False

    n_rows = len(rows)
    # Dynamic height: header(1) + title(1) + data rows + footer(1)
    fig_height = max(4, 2.5 + n_rows * 0.9 + 0.8)
    fig_width = 14

    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, fig_height)
    ax.axis('off')

    # ── Background ──
    fig.patch.set_facecolor(BG_PAGE)
    ax.set_facecolor(BG_PAGE)

    # ── Title ──
    default_title = f"设备保养看板  |  第{datetime.now().isocalendar()[1]}周"
    title_text = title or default_title
    ax.text(0.5, fig_height - 0.2, title_text,
            fontsize=20, fontweight='bold', color=TEXT_TITLE,
            ha='left', va='top', transform=ax.transData)

    # Subtitle with date
    ax.text(0.5, fig_height - 0.7, f"生成日期: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            fontsize=10, color=TEXT_SUBTITLE,
            ha='left', va='top')

    # ── Table ──
    # Column positions (x start, width)
    cols = [
        ('优先级', 0.5, 1.2),
        ('项目', 1.9, 1.8),
        ('内容', 3.9, 4.5),
        ('负责人', 8.6, 1.2),
        ('交付日期', 10.0, 1.5),
        ('进度', 11.7, 2.0),  # wider for progress bar
    ]

    header_y = fig_height - 1.2
    row_height = 0.85
    start_y = header_y - row_height

    # Draw header background
    header_rect = mpatches.FancyBboxPatch(
        (0.3, header_y - 0.25), 13.4, row_height,
        boxstyle="round,pad=0.1", facecolor=BG_HEADER, edgecolor='none'
    )
    ax.add_patch(header_rect)

    for col_name, x_start, width in cols:
        ax.text(x_start + width / 2, header_y + 0.15, col_name,
                fontsize=12, fontweight='bold', color=TEXT_HEADER,
                ha='center', va='center')

    # Draw rows
    current_y = start_y
    for idx, row in enumerate(rows):
        prio = row['priority']
        p_color = PRIORITY_COLORS.get(prio, PRIORITY_COLORS['P2'])

        # Alternate row bg
        bg_color = ROW_EVEN if idx % 2 == 0 else ROW_ODD
        row_rect = mpatches.FancyBboxPatch(
            (0.3, current_y - row_height + 0.1), 13.4, row_height - 0.1,
            boxstyle="round,pad=0.02", facecolor=bg_color, edgecolor=ROW_BORDER,
            linewidth=0.5
        )
        ax.add_patch(row_rect)

        # Priority tag
        tag_y = current_y - row_height / 2 + 0.08
        tag_rect = mpatches.FancyBboxPatch(
            (x_start := cols[0][1], tag_y - 0.25),
            cols[0][2], 0.5,
            boxstyle="round,pad=0.1", facecolor=p_color['tag'],
            edgecolor='none'
        )
        ax.add_patch(tag_rect)
        ax.text(x_start + cols[0][2] / 2, tag_y + 0.02, prio,
                fontsize=11, fontweight='bold', color='white',
                ha='center', va='center')

        # Project
        ax.text(cols[1][1] + 0.1, tag_y + 0.02, row['project'],
                fontsize=11, color='#212529',
                ha='left', va='center')

        # Content
        ax.text(cols[2][1] + 0.1, tag_y + 0.02, row['content'],
                fontsize=10, color='#495057',
                ha='left', va='center')

        # Owner
        ax.text(cols[3][1] + cols[3][2] / 2, tag_y + 0.02, row['owner'],
                fontsize=11, color='#212529',
                ha='center', va='center')

        # Due date
        ax.text(cols[4][1] + cols[4][2] / 2, tag_y + 0.02, row['due'],
                fontsize=10, color='#6C757D',
                ha='center', va='center')

        # Progress bar
        progress = row['progress']
        bar_x = cols[5][1]
        bar_y = tag_y - 0.18
        bar_w = cols[5][2]
        bar_h = 0.36

        # Progress bar background
        prog_bg_rect = mpatches.FancyBboxPatch(
            (bar_x, bar_y), bar_w, bar_h,
            boxstyle="round,pad=0.03", facecolor=PROGRESS_BG,
            edgecolor='none'
        )
        ax.add_patch(prog_bg_rect)

        # Progress bar fill
        if progress > 0:
            if progress >= 90:
                prog_color = PROGRESS_COLORS['high']
            elif progress >= 30:
                prog_color = PROGRESS_COLORS['mid']
            else:
                prog_color = PROGRESS_COLORS['low']

            fill_w = bar_w * (progress / 100)
            prog_fill = mpatches.FancyBboxPatch(
                (bar_x, bar_y), fill_w, bar_h,
                boxstyle="round,pad=0.03", facecolor=prog_color,
                edgecolor='none', alpha=0.85
            )
            ax.add_patch(prog_fill)

        # Progress text on top of bar
        text_color = '#FFFFFF' if progress >= 50 else '#495057'
        ax.text(bar_x + bar_w / 2, tag_y + 0.02, f'{progress}%',
                fontsize=9, fontweight='bold', color=text_color,
                ha='center', va='center')

        current_y -= row_height

    # Footer: legend
    legend_y = current_y - 0.3
    ax.text(0.5, legend_y, '优先级：',
            fontsize=9, color='#6C757D', ha='left', va='center')

    legend_items = [
        ('P0 - 紧急', PRIORITY_COLORS['P0']['tag']),
        ('P1 - 重要', PRIORITY_COLORS['P1']['tag']),
        ('P2 - 常规', PRIORITY_COLORS['P2']['tag']),
    ]
    legend_x = 2.0
    for label, color in legend_items:
        rect = mpatches.FancyBboxPatch(
            (legend_x, legend_y - 0.18), 0.4, 0.36,
            boxstyle="round,pad=0.02", facecolor=color, edgecolor='none'
        )
        ax.add_patch(rect)
        ax.text(legend_x + 0.5, legend_y + 0.02, label,
                fontsize=8, color='#6C757D', ha='left', va='center')
        legend_x += 2.8

    # Set output path
    if output_path is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_path = os.path.join(script_dir, '看板图.png')

    plt.tight_layout()
    plt.savefig(output_path, dpi=200, bbox_inches='tight',
                facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close(fig)

    return output_path


def sort_rows(rows, sort_key='due', reverse=False):
    """Sort rows by given key. Default: ascending by due date."""
    if sort_key == 'due':
        return sorted(rows, key=lambda r: r.get('due', ''), reverse=reverse)
    elif sort_key == 'priority':
        prio_order = {'P0': 0, 'P1': 1, 'P2': 2}
        return sorted(rows, key=lambda r: prio_order.get(r.get('priority', 'P2'), 3), reverse=reverse)
    elif sort_key == 'progress':
        return sorted(rows, key=lambda r: r.get('progress', 0), reverse=reverse)
    return rows


def main():
    # Determine input CSV
    if len(sys.argv) > 1 and not sys.argv[1].startswith('--'):
        csv_path = sys.argv[1]
    else:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        csv_path = os.path.join(script_dir, 'sample.csv')

    # Parse arguments
    title = None
    sort_key = 'due'
    reverse = False
    i = 0
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == '--title' and i + 1 < len(sys.argv):
            title = sys.argv[i + 1]
            i += 1
        elif arg == '--sort' and i + 1 < len(sys.argv):
            sort_key = sys.argv[i + 1]
            i += 1
        elif arg == '--reverse':
            reverse = True
        i += 1

    if not os.path.exists(csv_path):
        print(f"❌ 找不到CSV文件: {csv_path}")
        sys.exit(1)

    print(f"📂 读取: {csv_path}")
    rows = parse_csv(csv_path)
    rows = sort_rows(rows, sort_key=sort_key, reverse=reverse)
    order_label = ' 倒序' if reverse else ' 正序'
    print(f"📊 共 {len(rows)} 条记录（排序: {sort_key}{order_label}）")

    output = generate_board(rows, title=title)
    print(f"✅ 看板图已生成: {output}")

    # Also copy to workspace root for convenience
    import shutil
    workspace_root = os.path.abspath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), '..', '..'))
    dest = os.path.join(workspace_root, '看板图.png')
    shutil.copy2(output, dest)
    print(f"📋 已同步到: {dest}")


if __name__ == '__main__':
    main()
