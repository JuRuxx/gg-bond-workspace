#!/usr/bin/env python3
"""Generate A4 double-sided summary PDF for 产线管理流程."""

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, KeepTogether,
    HRFlowable, PageBreak
)
from reportlab.platypus.frames import Frame
from reportlab.platypus.doctemplate import PageTemplate, BaseDocTemplate
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.shapes import Drawing
from reportlab.platypus.flowables import Flowable
import os

# ─── Register Chinese fonts ───
FONT_DIRS = [
    "/System/Library/Fonts",
    "/System/Library/Fonts/Supplemental",
    "/Library/Fonts",
    os.path.expanduser("~/Library/Fonts"),
]

def find_chinese_font():
    for d in FONT_DIRS:
        if not os.path.isdir(d):
            continue
        for f in os.listdir(d):
            fl = f.lower()
            if "ping" in fl and ("sc" in fl or "tc" in fl) and f.endswith(".ttc"):
                return os.path.join(d, f)
            if "heiti" in fl and f.endswith(".ttc"):
                return os.path.join(d, f)
            if "hiragino" in fl and f.endswith(".ttc"):
                return os.path.join(d, f)
    return None

font_path = find_chinese_font()
if font_path:
    pdfmetrics.registerFont(TTFont("CNFont", font_path, subfontIndex=0))
    FONT = "CNFont"
else:
    FONT = "Helvetica"

# ─── Colors ───
BLUE = HexColor("#1a5276")
DARK = HexColor("#222")
GRAY = HexColor("#666")
LIGHT_BG = HexColor("#f6f9fc")
RED_BG = HexColor("#c0392b")
ORANGE_BG = HexColor("#e67e22")
BLUE_BG = HexColor("#2980b9")
GREEN_BG = HexColor("#27ae60")
WARN_BG = HexColor("#fff3cd")
WARN_BORDER = HexColor("#f0ad4e")

PAGE_W, PAGE_H = A4  # 595.27, 841.89
MARGIN_L = 16*mm
MARGIN_R = 16*mm
MARGIN_T = 18*mm
MARGIN_B = 18*mm
CONTENT_W = PAGE_W - MARGIN_L - MARGIN_R

# ─── Custom Flowable: Colored Label (inline-box substitutes) ───
class Badge(Flowable):
    def __init__(self, text, bg_color, text_color=white, font_size=7.5):
        Flowable.__init__(self)
        self.text = text
        self.bg = bg_color
        self.fg = text_color
        self.font_size = font_size
        self.padding = (2, 3)
        self.width = pdfmetrics.stringWidth(text, FONT, font_size) + 6
        self.height = font_size + 4

    def draw(self):
        self.canv.setFillColor(self.bg)
        r = 2
        self.canv.roundRect(0, 0, self.width, self.height, r, fill=1, stroke=0)
        self.canv.setFillColor(self.fg)
        self.canv.setFont(FONT, self.font_size)
        self.canv.drawCentredString(self.width / 2, 2, self.text)

def make_formatted_table(headers, rows, col_widths):
    """Create a styled table with header row and data rows."""
    header_style = ParagraphStyle("th", fontName=FONT, fontSize=7.5, textColor=white,
                                  leading=10, alignment=1)
    cell_style = ParagraphStyle("td", fontName=FONT, fontSize=7.5, textColor=DARK,
                                leading=10, alignment=0)

    data = [[Paragraph(h, header_style) for h in headers]]
    for row in rows:
        cells = []
        for cell in row:
            if isinstance(cell, tuple):
                # (text, badge_style)
                from reportlab.platypus import Paragraph as Para
                cells.append(cell)
            elif isinstance(cell, Badge):
                cells.append(cell)
            else:
                cells.append(Paragraph(str(cell), cell_style))
        data.append(cells)

    t = Table(data, colWidths=col_widths, repeatRows=1)
    style_cmds = [
        ('BACKGROUND', (0, 0), (-1, 0), BLUE),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor("#bbb")),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 2*mm),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2*mm),
        ('LEFTPADDING', (0, 0), (-1, -1), 2*mm),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2*mm),
    ]
    for i in range(2, len(data)):
        if i % 2 == 0:
            style_cmds.append(('BACKGROUND', (0, i), (-1, i), LIGHT_BG))
    t.setStyle(TableStyle(style_cmds))
    return t


def build_front_page():
    """Page 1: 产线服务流程."""
    from reportlab.platypus import Paragraph as P
    styles = getSampleStyleSheet()

    elements = []

    # ── Header ──
    def header_table():
        title = P("<b>技术部产线管理流程摘要</b>", ParagraphStyle(
            "title", fontName=FONT, fontSize=14, textColor=BLUE, leading=18))
        sub = P(
            "奥普新（陆河）科技有限公司<br/>"
            "<font size=7>试行期：一个月 · 月底复盘协商调整</font>",
            ParagraphStyle("sub", fontName=FONT, fontSize=8, textColor=GRAY, alignment=2, leading=11))

        data = [[title, sub]]
        t = Table(data, colWidths=[CONTENT_W * 0.6, CONTENT_W * 0.4])
        t.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 4*mm),
        ]))
        return t

    elements.append(header_table())
    elements.append(HRFlowable(width="100%", thickness=2, color=BLUE, spaceAfter=4*mm))

    # ── Section title ──
    sec_style = ParagraphStyle("sec", fontName=FONT, fontSize=10, textColor=BLUE,
                                leading=14, spaceBefore=3*mm, spaceAfter=2*mm)
    elements.append(P("▎产线服务流程（故障分级响应）", sec_style))

    # ── Fault grade table ──
    p0 = Badge("P0 紧急", RED_BG)
    p1 = Badge("P1 重要", ORANGE_BG)
    p2 = Badge("P2 一般", BLUE_BG)
    p3 = Badge("P3 计划性", GREEN_BG)

    c = ParagraphStyle("c", fontName=FONT, fontSize=7.5, leading=10)
    cb = ParagraphStyle("cb", fontName=FONT, fontSize=7.5, leading=10)

    rows = [
        [p0, P("产线停线<br/>无法生产", c),
         P("设备完全不动、主传动故障、关键工位失效", c),
         P("<b>15分钟到场</b><br/>先修后补单", cb)],
        [p1, P("设备异常<br/>效率下降", c),
         P("节拍变慢、某工位不稳定、需调参", c),
         P("<b>2小时内</b>响应<br/>按排程处理", cb)],
        [p2, P("小故障<br/>日常调试", c),
         P("传感器误报、螺丝松动、程序微调", c),
         P("<b>当天或次日</b>", cb)],
        [p3, P("保养、优化<br/>换型调试", c),
         P("周保养、程序升级、新产品换型", c),
         P("按<b>周计划</b>排期", cb)],
    ]
    cw = [CONTENT_W*0.18, CONTENT_W*0.17, CONTENT_W*0.38, CONTENT_W*0.27]
    elements.append(make_formatted_table(["等级", "定义", "典型例子", "技术部响应"], rows, cw))
    elements.append(Spacer(1, 3*mm))

    # ── Two-column: 报修 + 响应 ──
    box_style = ParagraphStyle("box", fontName=FONT, fontSize=7.5, leading=11,
                                leftIndent=2*mm, rightIndent=2*mm)
    box_title = ParagraphStyle("box_title", fontName=FONT, fontSize=8.5, textColor=BLUE,
                                leading=12, spaceAfter=1.5*mm)

    repair_content = [
        [P("<b>📞 怎么报修</b>", box_title)],
        [P(
            "• <b>P0（停线）</b>：先电话通知技术部值班人，后补填单<br/>"
            "• <b>P1/P2/P3</b>：先填腾讯文档在线表格（时间/设备/问题/预估等级/报修人），"
            "技术部按排程处理<br/>"
            "• 同一设备同一问题 3 天内报 ≥2 次 → <b>自动升级</b>一级处理",
            box_style)],
    ]
    resp_content = [
        [P("<b>⏰ 技术部响应时间</b>", box_title)],
        [P(
            "• <b>工作日 8:00-17:30</b>：值班工程师优先响应<br/>"
            "• <b>午休 12:00-13:30</b>：仅响应 P0，其余排队<br/>"
            "• <b>下班后/节假日</b>：仅 P0，电话联系技术部主管调度",
            box_style)],
    ]

    t_repair = Table(repair_content, colWidths=[CONTENT_W/2 - 1.5*mm])
    t_repair.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.5, HexColor("#ccc")),
        ('TOPPADDING', (0, 0), (-1, -1), 2*mm),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2*mm),
        ('LEFTPADDING', (0, 0), (-1, -1), 2*mm),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2*mm),
        ('BACKGROUND', (0, 0), (-1, 0), HexColor("#f0f4f8")),
        ('SPAN', (0, 0), (0, 0)),
    ]))

    t_resp = Table(resp_content, colWidths=[CONTENT_W/2 - 1.5*mm])
    t_resp.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.5, HexColor("#ccc")),
        ('TOPPADDING', (0, 0), (-1, -1), 2*mm),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2*mm),
        ('LEFTPADDING', (0, 0), (-1, -1), 2*mm),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2*mm),
        ('BACKGROUND', (0, 0), (-1, 0), HexColor("#f0f4f8")),
        ('SPAN', (0, 0), (0, 0)),
    ]))

    two_col = Table([[t_repair, t_resp]], colWidths=[CONTENT_W/2, CONTENT_W/2])
    two_col.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 1*mm),
        ('RIGHTPADDING', (0, 0), (-1, -1), 1*mm),
    ]))
    elements.append(two_col)
    elements.append(Spacer(1, 3*mm))

    # ── Two-column: 异常升级 + 分级争议 ──
    upgrade_content = [
        [P("<b>⬆ 异常升级</b>", box_title)],
        [P("值班工程师 <b>→</b> 设备负责人 <b>→</b> 技术部主管 <b>→</b> 供应商", box_style)],
    ]
    dispute_content = [
        [P("<b>⚖ 分级争议</b>", box_title)],
        [P("双方主管协商裁定，<b>不在产线上争执</b>。", box_style)],
    ]

    t_up = Table(upgrade_content, colWidths=[CONTENT_W/2 - 1.5*mm])
    t_up.setStyle(TableStyle([('BOX', (0,0), (-1,-1), 0.5, HexColor("#ccc")),
                               ('TOPPADDING', (0,0), (-1,-1), 2*mm),
                               ('BOTTOMPADDING', (0,0), (-1,-1), 2*mm),
                               ('LEFTPADDING', (0,0), (-1,-1), 2*mm),
                               ('RIGHTPADDING', (0,0), (-1,-1), 2*mm),
                               ('BACKGROUND', (0,0), (-1,0), HexColor("#f0f4f8")),
                               ('SPAN', (0,0), (0,0))]))
    t_dis = Table(dispute_content, colWidths=[CONTENT_W/2 - 1.5*mm])
    t_dis.setStyle(TableStyle([('BOX', (0,0), (-1,-1), 0.5, HexColor("#ccc")),
                                ('TOPPADDING', (0,0), (-1,-1), 2*mm),
                                ('BOTTOMPADDING', (0,0), (-1,-1), 2*mm),
                                ('LEFTPADDING', (0,0), (-1,-1), 2*mm),
                                ('RIGHTPADDING', (0,0), (-1,-1), 2*mm),
                                ('BACKGROUND', (0,0), (-1,0), HexColor("#f0f4f8")),
                                ('SPAN', (0,0), (0,0))]))

    two_col2 = Table([[t_up, t_dis]], colWidths=[CONTENT_W/2, CONTENT_W/2])
    two_col2.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'),
                                   ('LEFTPADDING', (0,0), (-1,-1), 1*mm),
                                   ('RIGHTPADDING', (0,0), (-1,-1), 1*mm)]))
    elements.append(two_col2)
    elements.append(Spacer(1, 5*mm))

    # ── Section 2: 意见流程 ──
    elements.append(P("▎产线意见流程（改进建议管理）", sec_style))

    ba = Badge("A 必须改", RED_BG)
    bb = Badge("B 建议改", ORANGE_BG)
    bc = Badge("C 提醒", HexColor("#7f8c8d"), font_size=7.5)

    rows2 = [
        [ba, P("安全隐患<br/>可能造成损坏", c),
         P("跳过安全门禁、违规操作、强行运行", c),
         P("书面+正式会议<br/>抄送双方主管", c),
         P("<b>24h</b>确认", cb)],
        [bb, P("影响设备寿命<br/>效率或保养", c),
         P("保养不到位、操作习惯不良", c),
         P("书面<br/>值班工程师→产线组长", c),
         P("<b>48h</b>确认", cb)],
        [bc, P("小问题<br/>提醒即可", c),
         P("工具未归位、地面油污、记录潦草", c),
         P("口头提醒<br/>记录备查", c),
         P("无需回应", cb)],
    ]
    cw2 = [CONTENT_W*0.15, CONTENT_W*0.15, CONTENT_W*0.30, CONTENT_W*0.26, CONTENT_W*0.14]
    elements.append(make_formatted_table(["等级", "定义", "典型例子", "提出方式", "期望回应"], rows2, cw2))

    # Highlight box
    warn_style = ParagraphStyle("warn", fontName=FONT, fontSize=7.5, leading=11,
                                 leftIndent=3*mm, textColor=HexColor("#8a6d3b"))
    highlight_table = Table(
        [[P("🔔 同一 C 级问题口头提醒 ≥2 次未改 → 自动升级为 B 级", warn_style)]],
        colWidths=[CONTENT_W])
    highlight_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), WARN_BG),
        ('LEFTPADDING', (0, 0), (-1, 0), 3*mm),
        ('TOPPADDING', (0, 0), (-1, 0), 2.5*mm),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 2.5*mm),
        ('LEFTPADDING', (0, 0), (-1, -1), 3*mm),
        ('LINELEFT', (0, 0), (-1, 0), 2.5, WARN_BORDER),
    ]))
    elements.append(highlight_table)
    elements.append(Spacer(1, 3*mm))

    # ── Two-col: 提出流程 + 登记表 ──
    flow_content = [
        [P("<b>📋 提出流程</b>", box_title)],
        [P(
            "<b>①</b> 发现问题 → <b>②</b> 判断等级<br/>"
            "<b>③</b> 内部确认（A/B级统一口径）<br/>"
            "<b>④</b> 选择方式提出<br/>"
            "<b>⑤</b> 跟踪闭环 · <b>2周无反馈升级</b>",
            box_style)],
        [P("<font size=7>✓ 同一问题不要多人重复提<br/>✓ 指向问题，不指责任何人</font>",
           ParagraphStyle("note", fontName=FONT, fontSize=7, textColor=HexColor("#666"),
                          leading=9, spaceBefore=1*mm))],
    ]
    reg_content = [
        [P("<b>📊 登记表（腾讯文档）</b>", box_title)],
        [P(
            "提出日期 | 提出人 | 问题描述 | 等级<br/>"
            "指出对象 | 反馈方式 | 生产部回应 | 整改状态 | 关闭日期",
            ParagraphStyle("reg", fontName=FONT, fontSize=6.5, textColor=HexColor("#444"),
                           leading=9))],
        [P("<font size=7>A/B级必须登记，C级可选登记</font>",
           ParagraphStyle("note2", fontName=FONT, fontSize=7, textColor=HexColor("#666"),
                          leading=9, spaceBefore=1*mm))],
    ]

    t_flow = Table(flow_content, colWidths=[CONTENT_W/2 - 1.5*mm])
    t_flow.setStyle(TableStyle([('BOX', (0,0), (-1,-1), 0.5, HexColor("#ccc")),
                                 ('TOPPADDING', (0,0), (-1,-1), 2*mm),
                                 ('BOTTOMPADDING', (0,0), (-1,-1), 2*mm),
                                 ('LEFTPADDING', (0,0), (-1,-1), 2*mm),
                                 ('RIGHTPADDING', (0,0), (-1,-1), 2*mm),
                                 ('BACKGROUND', (0,0), (-1,0), HexColor("#f0f4f8")),
                                 ('SPAN', (0,0), (0,0))]))

    t_reg = Table(reg_content, colWidths=[CONTENT_W/2 - 1.5*mm])
    t_reg.setStyle(TableStyle([('BOX', (0,0), (-1,-1), 0.5, HexColor("#ccc")),
                                ('TOPPADDING', (0,0), (-1,-1), 2*mm),
                                ('BOTTOMPADDING', (0,0), (-1,-1), 2*mm),
                                ('LEFTPADDING', (0,0), (-1,-1), 2*mm),
                                ('RIGHTPADDING', (0,0), (-1,-1), 2*mm),
                                ('BACKGROUND', (0,0), (-1,0), HexColor("#f0f4f8")),
                                ('SPAN', (0,0), (0,0))]))

    two_col3 = Table([[t_flow, t_reg]], colWidths=[CONTENT_W/2, CONTENT_W/2])
    two_col3.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'),
                                   ('LEFTPADDING', (0,0), (-1,-1), 1*mm),
                                   ('RIGHTPADDING', (0,0), (-1,-1), 1*mm)]))
    elements.append(two_col3)
    elements.append(Spacer(1, 3*mm))

    # ── 定期复盘 ──
    review_style = ParagraphStyle("rev", fontName=FONT, fontSize=7, textColor=DARK, leading=10)
    rev_content = [
        [P("<b>📅 定期复盘</b>", box_title)],
        [Table(
            [[P("<b>每月</b>：技术部内部汇总，讨论采纳/拒绝/反复问题", review_style),
              P("<b>每季度</b>：形成《设备操作规范改进建议》提交生产部", review_style),
              P("<b>年度</b>：结合设备故障分析盘点效果", review_style)]],
            colWidths=[CONTENT_W/3 - 3*mm, CONTENT_W/3 - 3*mm, CONTENT_W/3 - 3*mm]),
         ],
    ]
    t_rev = Table(rev_content, colWidths=[CONTENT_W])
    t_rev.setStyle(TableStyle([('BOX', (0,0), (-1,-1), 0.5, HexColor("#ccc")),
                                ('TOPPADDING', (0,0), (-1,-1), 2*mm),
                                ('BOTTOMPADDING', (0,0), (-1,-1), 2*mm),
                                ('LEFTPADDING', (0,0), (-1,-1), 2*mm),
                                ('RIGHTPADDING', (0,0), (-1,-1), 2*mm),
                                ('BACKGROUND', (0,0), (-1,0), HexColor("#f0f4f8")),
                                ('SPAN', (0,0), (0,0))]))
    elements.append(t_rev)
    elements.append(Spacer(1, 6*mm))

    # ── Signature ──
    sig_style = ParagraphStyle("sig", fontName=FONT, fontSize=8, textColor=DARK, leading=12)
    sig = Table([
        [P("技术部主管：______________________", sig_style),
         P("生产部主管：______________________", sig_style)]
    ], colWidths=[CONTENT_W*0.45, CONTENT_W*0.45])
    sig.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'BOTTOM'),
        ('ALIGN', (0,0), (0,0), 'LEFT'),
        ('ALIGN', (1,0), (1,0), 'RIGHT'),
        ('LINEABOVE', (0,0), (-1,0), 1, HexColor("#999")),
        ('TOPPADDING', (0,0), (-1,-1), 4*mm),
    ]))
    elements.append(sig)

    # Date
    date_style = ParagraphStyle("date", fontName=FONT, fontSize=7, textColor=GRAY, alignment=2)
    elements.append(P("日期：____年____月____日", date_style))

    # Footer
    footer_style = ParagraphStyle("ft", fontName=FONT, fontSize=6, textColor=HexColor("#bbb"),
                                   alignment=2, spaceBefore=1*mm)
    elements.append(P("产线管理流程摘要 v1.0", footer_style))

    return elements


def build_pdf():
    output = "/Users/a1/.openclaw/workspace/公司管理文档/产线管理流程摘要（A4）.pdf"

    doc = SimpleDocTemplate(
        output, pagesize=A4,
        leftMargin=MARGIN_L, rightMargin=MARGIN_R,
        topMargin=MARGIN_T, bottomMargin=MARGIN_B,
        title="技术部产线管理流程摘要",
        author="技术部",
    )

    elements = build_front_page()
    doc.build(elements)
    print(f"PDF generated: {output}")
    print(f"Size: {os.path.getsize(output)} bytes")

if __name__ == "__main__":
    build_pdf()
