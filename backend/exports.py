"""
Εξαγωγή βιβλίου εκρηκτικών σε νόμιμη μορφή PDF και Excel.
Χρησιμοποιεί Liberation Sans για πλήρη ελληνική υποστήριξη.
"""
import io
import os
from datetime import datetime

# Paths για Liberation Sans fonts
FONT_DIR = '/usr/share/fonts/truetype/liberation'
FONT_REGULAR = os.path.join(FONT_DIR, 'LiberationSans-Regular.ttf')
FONT_BOLD    = os.path.join(FONT_DIR, 'LiberationSans-Bold.ttf')

def register_fonts():
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    try:
        pdfmetrics.getFont('LiberationSans')
    except:
        pdfmetrics.registerFont(TTFont('LiberationSans',     FONT_REGULAR))
        pdfmetrics.registerFont(TTFont('LiberationSans-Bold', FONT_BOLD))

# ─── PDF (ReportLab) ─────────────────────────────────────────────────────────

def export_pdf(kiniseis: list, yliko_label: str, period_label: str) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_CENTER

    register_fonts()
    F  = 'LiberationSans'
    FB = 'LiberationSans-Bold'

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4),
                            leftMargin=1.5*cm, rightMargin=1.5*cm,
                            topMargin=2*cm, bottomMargin=2*cm)

    title_style = ParagraphStyle('title', fontSize=13, fontName=FB,
                                  alignment=TA_CENTER, spaceAfter=4)
    sub_style   = ParagraphStyle('sub',   fontSize=9,  fontName=F,
                                  alignment=TA_CENTER, spaceAfter=10)
    cell_style  = ParagraphStyle('cell',  fontSize=7.5, fontName=F, leading=10)

    story = []
    story.append(Paragraph("ΒΙΒΛΙΟ ΕΚΡΗΚΤΙΚΩΝ ΥΛΩΝ", title_style))
    story.append(Paragraph(
        f"Υλικό: {yliko_label}  |  Περίοδος: {period_label}  |  "
        f"Εκτύπωση: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        sub_style))

    # Υπολογισμός υπολοίπου ανά υλικό
    ypoloipa = {}  # yliko_id → ypoloipo
    rows_data = []
    for k in kiniseis:
        yid = k['yliko_id']
        if yid not in ypoloipa:
            ypoloipa[yid] = 0.0
        eisagogi = k['posotita'] if k['tipos'] == 'ΕΙΣΑΓΩΓΗ' else ''
        exagogi  = k['posotita'] if k['tipos'] == 'ΕΞΑΓΩΓΗ'  else ''
        if k['tipos'] == 'ΕΙΣΑΓΩΓΗ':
            ypoloipa[yid] += k['posotita']
        else:
            ypoloipa[yid] -= k['posotita']

        mon = k['monada_metrisis']
        rows_data.append([
            str(k['auxon_arithmos']),
            k['imerominia'],
            k.get('arithmos_parstatikos') or '',
            Paragraph(k.get('yliko_onoma', ''), cell_style),
            k.get('promitheftis_onoma') or '',
            k.get('arithmos_adeias') or '',
            f"{eisagogi:.3f} {mon}" if eisagogi != '' else '',
            f"{exagogi:.3f} {mon}"  if exagogi  != '' else '',
            f"{ypoloipa[yid]:.3f} {mon}",
            k.get('ypografi') or '',
        ])

    headers = [
        'Α/Α', 'Ημερομηνία', 'Αρ.\nΠαραστ.', 'Είδος\nΕκρηκτικού',
        'Προμηθευτής', 'Αρ.\nΆδειας',
        'Ποσότητα\nΕισαγωγής', 'Ποσότητα\nΕξαγωγής',
        'Υπόλοιπο', 'Υπογραφή'
    ]
    col_widths = [1*cm, 2.2*cm, 2*cm, 5*cm, 3.5*cm, 2.2*cm,
                  2.8*cm, 2.8*cm, 2.8*cm, 2.5*cm]

    table_data = [headers] + rows_data
    t = Table(table_data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND',     (0,0), (-1,0), colors.HexColor('#1a365d')),
        ('TEXTCOLOR',      (0,0), (-1,0), colors.white),
        ('FONTNAME',       (0,0), (-1,0), FB),
        ('FONTSIZE',       (0,0), (-1,0), 7.5),
        ('ALIGN',          (0,0), (-1,0), 'CENTER'),
        ('VALIGN',         (0,0), (-1,-1), 'MIDDLE'),
        ('FONTNAME',       (0,1), (-1,-1), F),
        ('FONTSIZE',       (0,1), (-1,-1), 7.5),
        ('ALIGN',          (0,1), (0,-1), 'CENTER'),
        ('ALIGN',          (1,1), (1,-1), 'CENTER'),
        ('ALIGN',          (6,1), (8,-1), 'RIGHT'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f0f4f8')]),
        ('GRID',           (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e0')),
        ('TOPPADDING',     (0,0), (-1,-1), 4),
        ('BOTTOMPADDING',  (0,0), (-1,-1), 4),
        ('LEFTPADDING',    (0,0), (-1,-1), 3),
        ('RIGHTPADDING',   (0,0), (-1,-1), 3),
    ]))
    story.append(t)
    doc.build(story)
    return buf.getvalue()


# ─── Excel (openpyxl) ────────────────────────────────────────────────────────

def export_excel(kiniseis: list, yliko_label: str, period_label: str) -> bytes:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Βιβλίο Εκρηκτικών"

    ws.merge_cells('A1:J1')
    ws['A1'] = "ΒΙΒΛΙΟ ΕΚΡΗΚΤΙΚΩΝ ΥΛΩΝ"
    ws['A1'].font = Font(bold=True, size=14)
    ws['A1'].alignment = Alignment(horizontal='center')

    ws.merge_cells('A2:J2')
    ws['A2'] = f"Υλικό: {yliko_label}  |  Περίοδος: {period_label}  |  Εκτύπωση: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    ws['A2'].alignment = Alignment(horizontal='center')

    headers    = ['Α/Α', 'Ημερομηνία', 'Αρ. Παραστ.', 'Είδος Εκρηκτικού',
                  'Προμηθευτής', 'Αρ. Άδειας',
                  'Ποσ. Εισαγωγής', 'Ποσ. Εξαγωγής', 'Υπόλοιπο', 'Υπογραφή']
    col_widths = [6, 12, 12, 30, 20, 12, 14, 14, 14, 15]

    header_fill = PatternFill("solid", fgColor="1A365D")
    header_font = Font(bold=True, color="FFFFFF", size=10)
    thin   = Side(style='thin', color="CBD5E0")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    for col, (h, w) in enumerate(zip(headers, col_widths), 1):
        cell = ws.cell(row=4, column=col, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center', wrap_text=True)
        cell.border = border
        ws.column_dimensions[get_column_letter(col)].width = w
    ws.row_dimensions[4].height = 30

    ypoloipa = {}  # yliko_id → ypoloipo
    alt_fill = PatternFill("solid", fgColor="F0F4F8")

    for row_idx, k in enumerate(kiniseis, 5):
        yid = k['yliko_id']
        if yid not in ypoloipa:
            ypoloipa[yid] = 0.0
        fill     = alt_fill if row_idx % 2 == 0 else None
        eisagogi = k['posotita'] if k['tipos'] == 'ΕΙΣΑΓΩΓΗ' else None
        exagogi  = k['posotita'] if k['tipos'] == 'ΕΞΑΓΩΓΗ'  else None
        if eisagogi: ypoloipa[yid] += eisagogi
        else:        ypoloipa[yid] -= exagogi

        row_vals = [
            k['auxon_arithmos'], k['imerominia'],
            k.get('arithmos_parstatikos') or '',
            k.get('yliko_onoma') or '',
            k.get('promitheftis_onoma') or '',
            k.get('arithmos_adeias') or '',
            eisagogi, exagogi, round(ypoloipa[yid], 3),
            k.get('ypografi') or ''
        ]
        for col, val in enumerate(row_vals, 1):
            cell = ws.cell(row=row_idx, column=col, value=val)
            cell.border = border
            if fill: cell.fill = fill
            if col in (7, 8, 9):
                cell.number_format = '#,##0.000'
                cell.alignment = Alignment(horizontal='right')
            elif col in (1, 2):
                cell.alignment = Alignment(horizontal='center')
            if col == 9 and ypoloipa[yid] < 0:
                cell.font = Font(color="C53030", bold=True)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
