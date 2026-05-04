"""
accounts/pdf_generator.py
Generates a professional Tool Request PDF using ReportLab.
Footers are read dynamically from PdfFooterConfig so admin changes apply immediately.
"""

from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.platypus.flowables import Flowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT


# ── Colour palette ──────────────────────────────────────────────────────────
NAVY     = colors.HexColor('#0B1B3D')
BLUE     = colors.HexColor('#1E488F')
LIGHT_BG = colors.HexColor('#F4F6F9')
BORDER   = colors.HexColor('#CBD5E1')
WHITE    = colors.white
MUTED    = colors.HexColor('#64748B')
SUCCESS  = colors.HexColor('#16A34A')
DANGER   = colors.HexColor('#DC2626')
WARNING  = colors.HexColor('#D97706')


def _status_color(status):
    if status == 'Approved': return SUCCESS
    if status == 'Rejected': return DANGER
    return WARNING
    

def generate_tool_request_pdf(tool_request):
    """
    Returns a BytesIO buffer containing the PDF for the given ToolRequest.
    """
    # Import here to avoid circular imports
    from .models import PdfFooterConfig

    config   = PdfFooterConfig.get_config()
    footer_l = config.footer_left.strip()
    footer_c = config.footer_center.strip()
    footer_r = config.footer_right.strip()

    buffer = BytesIO()
    page_w, page_h = A4

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'Title', parent=styles['Normal'],
        fontSize=20, textColor=WHITE,
        fontName='Helvetica-Bold',
        leading=26,
    )
    subtitle_style = ParagraphStyle(
        'Subtitle', parent=styles['Normal'],
        fontSize=10, textColor=colors.HexColor('#CBD5E1'),
        fontName='Helvetica',
    )
    section_style = ParagraphStyle(
        'Section', parent=styles['Normal'],
        fontSize=11, textColor=NAVY,
        fontName='Helvetica-Bold',
        spaceBefore=10, spaceAfter=4,
    )
    label_style = ParagraphStyle(
        'Label', parent=styles['Normal'],
        fontSize=8, textColor=MUTED,
        fontName='Helvetica',
    )
    value_style = ParagraphStyle(
        'Value', parent=styles['Normal'],
        fontSize=10, textColor=colors.HexColor('#1E293B'),
        fontName='Helvetica',
    )
    value_bold_style = ParagraphStyle(
        'ValueBold', parent=styles['Normal'],
        fontSize=10, textColor=NAVY,
        fontName='Helvetica-Bold',
    )

    # ── Footer drawing function ───────────────────────────────────────────
    def draw_footer(canvas, doc):
        canvas.saveState()
        page_num = doc.page

    # ── TOP RIGHT: Page number ──────────────────────────────────────
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(MUTED)
        canvas.drawRightString(page_w - 15*mm, page_h - 10*mm, f'Page {page_num}')

    # ── BOTTOM: Footer line ─────────────────────────────────────────
        canvas.setStrokeColor(BORDER)
        canvas.setLineWidth(0.5)
        canvas.line(15*mm, 18*mm, page_w - 15*mm, 18*mm)

        canvas.setFont('Helvetica', 7.5)
        canvas.setFillColor(MUTED)

    # Left footer
        if footer_l:
            canvas.drawString(15*mm, 12*mm, footer_l)

    # Centre footer
        if footer_c:
            canvas.drawCentredString(page_w / 2, 12*mm, footer_c)

    # Right footer — NO {page} replacement here anymore
        if footer_r:
            canvas.drawRightString(page_w - 15*mm, 12*mm, footer_r)

        canvas.restoreState()

    # ── Document setup ────────────────────────────────────────────────────
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=15*mm,
        rightMargin=15*mm,
        topMargin=15*mm,
        bottomMargin=28*mm,   # space for footer
        title=f"Tool Request — {tool_request.tool_code}",
        author="Tool Code Library",
    )

    story = []

    # ── Header banner ────────────────────────────────────────────────────
    status_color = _status_color(tool_request.status)

    header_data = [[
        Paragraph('Tool Code Library', title_style),
        Paragraph(f'Status: {tool_request.status}', ParagraphStyle(
            'StatusBadge', parent=styles['Normal'],
            fontSize=11, textColor=WHITE,
            fontName='Helvetica-Bold',
            alignment=TA_RIGHT,
        )),
    ]]
    header_sub_data = [[
        Paragraph('Tool Code Request Report', subtitle_style),
        Paragraph(tool_request.created_at.strftime('%d %B %Y'), ParagraphStyle(
            'DateRight', parent=styles['Normal'],
            fontSize=9, textColor=colors.HexColor('#CBD5E1'),
            fontName='Helvetica',
            alignment=TA_RIGHT,
        )),
    ]]

    content_width = page_w - 30*mm

    header_table = Table(header_data, colWidths=[content_width * 0.65, content_width * 0.35])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), NAVY),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (0,-1), 12),
        ('RIGHTPADDING', (-1,0), (-1,-1), 12),
    ]))

    sub_table = Table(header_sub_data, colWidths=[content_width * 0.65, content_width * 0.35])
    sub_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), BLUE),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (0,-1), 12),
        ('RIGHTPADDING', (-1,0), (-1,-1), 12),
    ]))

    story.append(header_table)
    story.append(sub_table)
    story.append(Spacer(1, 8*mm))

    # ── Tool Code highlight box ───────────────────────────────────────────
    tc_style = ParagraphStyle(
        'TC', parent=styles['Normal'],
        fontSize=16, textColor=NAVY,
        fontName='Helvetica-Bold',
        alignment=TA_CENTER,
    )
    tc_table = Table(
        [[Paragraph(f'Tool Code: {tool_request.tool_code or "[Pending]"}', tc_style)]],
        colWidths=[content_width],
    )
    tc_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), LIGHT_BG),
        ('BOX', (0,0), (-1,-1), 1, BLUE),
        ('TOPPADDING', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ('LEFTPADDING', (0,0), (-1,-1), 12),
        ('RIGHTPADDING', (0,0), (-1,-1), 12),
        ('ROUNDEDCORNERS', [4, 4, 4, 4]),
    ]))
    story.append(tc_table)
    story.append(Spacer(1, 6*mm))

    # ── Helper: two-column info row ───────────────────────────────────────
    def info_row(pairs):
        """pairs = [(label, value), (label, value)] for a 2-column row."""
        col_w = content_width / len(pairs)
        row_data = []
        for label, value in pairs:
            cell = [
                Paragraph(label.upper(), label_style),
                Paragraph(str(value) if value else '—', value_style),
            ]
            row_data.append(cell)
        t = Table([row_data], colWidths=[col_w] * len(pairs))
        t.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 8),
            ('LINEBELOW', (0,-1), (-1,-1), 0.5, BORDER),
        ]))
        return t

    def section_header(title):
        return [
            Paragraph(title, section_style),
            HRFlowable(width='100%', thickness=1.5, color=BLUE, spaceAfter=4),
        ]

    # ── Section 1: Tool Information ───────────────────────────────────────
    story += section_header('Tool Information')
    story.append(info_row([
        ('Description', tool_request.description.field_name if tool_request.description else '—'),
        ('Fixed Value',
         f"{tool_request.fixed_value.fixed_value} — {tool_request.fixed_value.explanation}"
         if tool_request.fixed_value else '—'),
    ]))
    story.append(info_row([
        ('Joint Type', tool_request.joint_type.joint_type_name if tool_request.joint_type else '—'),
        ('Raw Material', tool_request.raw_material.raw_material_name if tool_request.raw_material else '—'),
    ]))

    # ── Section 2: Dynamic Specifications ────────────────────────────────
    attrs = list(tool_request.attributes.all())
    if attrs:
        story += section_header(
            f"{tool_request.description.field_name} Specifications"
            if tool_request.description else 'Specifications'
        )
        # Group into rows of 3
        for i in range(0, len(attrs), 3):
            chunk = attrs[i:i+3]
            pairs = [(a.attr_name, a.value) for a in chunk]
            # Pad to 3 if needed
            while len(pairs) < 3:
                pairs.append(('', ''))
            story.append(info_row(pairs))

    # ── Section 3: Supplier Information ──────────────────────────────────
    story += section_header('Supplier Information')
    story.append(info_row([
        ('Supplier 1', tool_request.supplier1.supplier_name if tool_request.supplier1 else '—'),
        ('Ordering Code 1', tool_request.supplier_code1 or '—'),
    ]))
    story.append(info_row([
        ('Supplier 2', tool_request.supplier2.supplier_name if tool_request.supplier2 else '—'),
        ('Ordering Code 2', tool_request.supplier_code2 or '—'),
    ]))

    # ── Section 4: Remarks ────────────────────────────────────────────────
    if tool_request.remark:
        story += section_header('Remarks')
        remark_box = Table(
            [[Paragraph(tool_request.remark, value_style)]],
            colWidths=[content_width],
        )
        remark_box.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), LIGHT_BG),
            ('BOX', (0,0), (-1,-1), 0.5, BORDER),
            ('TOPPADDING', (0,0), (-1,-1), 8),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
            ('LEFTPADDING', (0,0), (-1,-1), 10),
            ('RIGHTPADDING', (0,0), (-1,-1), 10),
        ]))
        story.append(remark_box)
        story.append(Spacer(1, 4*mm))

    # ── Section 5: Rejection Reason ───────────────────────────────────────
    if tool_request.status == 'Rejected' and tool_request.reject_reason:
        story += section_header('Reason for Rejection')
        reject_box = Table(
            [[Paragraph(tool_request.reject_reason, ParagraphStyle(
                'Reject', parent=styles['Normal'],
                fontSize=10, textColor=colors.HexColor('#7F1D1D'),
                fontName='Helvetica',
            ))]],
            colWidths=[content_width],
        )
        reject_box.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#FEF2F2')),
            ('BOX', (0,0), (-1,-1), 1, DANGER),
            ('TOPPADDING', (0,0), (-1,-1), 8),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
            ('LEFTPADDING', (0,0), (-1,-1), 10),
            ('RIGHTPADDING', (0,0), (-1,-1), 10),
        ]))
        story.append(reject_box)
        story.append(Spacer(1, 4*mm))

    # ── Section 6: Audit Trail ────────────────────────────────────────────
    story += section_header('Audit Trail')
    story.append(info_row([
        ('Requested By', tool_request.created_by.get_full_name() or tool_request.created_by.username),
        ('Requested On', tool_request.created_at.strftime('%d %b %Y, %H:%M')),
    ]))
    if hasattr(tool_request, 'reviewed_by') and tool_request.reviewed_by:
        reviewed_at = ''
        if hasattr(tool_request, 'reviewed_at') and tool_request.reviewed_at:
            reviewed_at = tool_request.reviewed_at.strftime('%d %b %Y, %H:%M')
        story.append(info_row([
            ('Reviewed By',
             tool_request.reviewed_by.get_full_name() or tool_request.reviewed_by.username),
            ('Reviewed On', reviewed_at or '—'),
        ]))

    story.append(Spacer(1, 8*mm))

    # ── Build PDF ─────────────────────────────────────────────────────────
    doc.build(story, onFirstPage=draw_footer, onLaterPages=draw_footer)
    buffer.seek(0)
    return buffer