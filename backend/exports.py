"""
Εξαγωγή βιβλίου εκρηκτικών.
Μορφή: μία γραμμή ανά τιμολόγιο, δυναμικές στήλες ανά υλικό.
"""
import io
import os
import glob
from datetime import datetime
from collections import OrderedDict

def find_font(names):
    search_dirs = [
        '/usr/share/fonts', '/usr/local/share/fonts',
        os.path.expanduser('~/.fonts'), os.path.expanduser('~/.local/share/fonts'),
        os.path.expanduser('~/.cargo'),
    ]
    for name in names:
        for d in search_dirs:
            matches = glob.glob(f'{d}/**/{name}', recursive=True)
            if matches:
                return matches[0]
    return None

FONT_REGULAR = find_font(['JetBrainsMono-Regular.ttf', 'LiberationMono-Regular.ttf', 'FreeMono.ttf'])
FONT_BOLD    = find_font(['JetBrainsMono-Bold.ttf', 'LiberationMono-Bold.ttf', 'FreeMonoBold.ttf'])
FONT_SANS_R  = find_font(['LiberationSans-Regular.ttf', 'FreeSans.ttf'])
FONT_SANS_B  = find_font(['LiberationSans-Bold.ttf', 'FreeSansBold.ttf'])

def register_fonts():
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    try:
        pdfmetrics.getFont('Mono')
    except:
        if FONT_REGULAR:
            pdfmetrics.registerFont(TTFont('Mono',      FONT_REGULAR))
            pdfmetrics.registerFont(TTFont('Mono-Bold', FONT_BOLD or FONT_REGULAR))
        if FONT_SANS_R:
            pdfmetrics.registerFont(TTFont('Sans',      FONT_SANS_R))
            pdfmetrics.registerFont(TTFont('Sans-Bold', FONT_SANS_B or FONT_SANS_R))

def fmt_date(s):
    """YYYY-MM-DD → DD/MM/YYYY"""
    if not s: return ''
    try:
        parts = s.split('-')
        if len(parts) == 3 and len(parts[0]) == 4:
            return f"{parts[2]}/{parts[1]}/{parts[0]}"
    except: pass
    return s

def fmt_num(val):
    if val is None or val == 0: return ''
    return f"{val:,.3f}".replace(',', 'X').replace('.', ',').replace('X', '.')

def build_rows(kiniseis):
    ylika_order = OrderedDict()
    for k in kiniseis:
        yid = k['yliko_id']
        if yid not in ylika_order:
            ylika_order[yid] = (k['yliko_onoma'], k['monada_metrisis'])

    row_keys = OrderedDict()
    row_data = []
    for k in kiniseis:
        key = (k['imerominia'], k.get('arithmos_parstatikos') or '',
               k.get('arithmos_adeias') or '', k.get('promitheftis_onoma') or '')
        if key not in row_keys:
            row_keys[key] = len(row_data)
            row_data.append({
                'imerominia':   k['imerominia'],
                'parstatiko':   k.get('arithmos_parstatikos') or '',
                'adeia':        k.get('arithmos_adeias') or '',
                'promitheftis': k.get('promitheftis_onoma') or '',
                'ylika':        {}
            })
        idx = row_keys[key]
        yid = k['yliko_id']
        pos = k['posotita'] if k['tipos'] == 'ΕΙΣΑΓΩΓΗ' else -k['posotita']
        row_data[idx]['ylika'][yid] = row_data[idx]['ylika'].get(yid, 0) + pos

    return list(ylika_order.items()), row_data

# ─── PDF ─────────────────────────────────────────────────────────────────────

def export_pdf(kiniseis: list, yliko_label: str, period_label: str) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT

    register_fonts()
    F   = 'Mono'      if FONT_REGULAR else 'Courier'
    FB  = 'Mono-Bold' if FONT_BOLD    else 'Courier-Bold'
    SF  = 'Sans'      if FONT_SANS_R  else 'Helvetica'
    SFB = 'Sans-Bold' if FONT_SANS_B  else 'Helvetica-Bold'

    ylika_order, rows = build_rows(kiniseis)

    buf = io.BytesIO()
    pagesize = landscape(A4)
    doc = SimpleDocTemplate(buf, pagesize=pagesize,
                            leftMargin=1*cm, rightMargin=1*cm,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)

    title_style = ParagraphStyle('t', fontSize=11, fontName=SFB, alignment=TA_CENTER, spaceAfter=3)
    sub_style   = ParagraphStyle('s', fontSize=7,  fontName=SF,  alignment=TA_CENTER, spaceAfter=8)
    hdr_style   = ParagraphStyle('h', fontSize=5.5, fontName=FB, alignment=TA_CENTER, leading=7)
    cell_style  = ParagraphStyle('c', fontSize=6,   fontName=F,  alignment=TA_CENTER, leading=7)
    name_style  = ParagraphStyle('n', fontSize=5.5, fontName=F,  alignment=TA_LEFT,   leading=7)

    story = []
    story.append(Paragraph("ΒΙΒΛΙΟ ΕΚΡΗΚΤΙΚΩΝ ΥΛΩΝ", title_style))
    story.append(Paragraph(
        f"Υλικό: {yliko_label}  |  Περίοδος: {period_label}  |  "
        f"Εκτύπωση: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        sub_style))

    fixed_headers = [
        Paragraph('Α/Α', hdr_style),
        Paragraph('Ημερομηνία', hdr_style),
        Paragraph('Αρ.\nΠαραστ.', hdr_style),
        Paragraph('Αρ.\nΆδειας', hdr_style),
        Paragraph('Προμηθευτής', hdr_style),
    ]
    yliko_headers = [
        Paragraph(f"{onoma}\n({monada})", hdr_style)
        for _, (onoma, monada) in ylika_order
    ]
    headers = fixed_headers + yliko_headers

    page_w   = pagesize[0] - 2*cm
    fixed_w  = [0.8*cm, 1.8*cm, 1.6*cm, 1.6*cm, 2.8*cm]
    remaining = page_w - sum(fixed_w)
    n_ylika  = len(ylika_order)
    yliko_w  = max(1.4*cm, remaining / n_ylika) if n_ylika else 2*cm
    col_widths = fixed_w + [yliko_w] * n_ylika

    table_rows = [headers]
    for i, row in enumerate(rows, 1):
        cells = [
            Paragraph(str(i), cell_style),
            Paragraph(fmt_date(row['imerominia']), cell_style),
            Paragraph(row['parstatiko'], cell_style),
            Paragraph(row['adeia'], cell_style),
            Paragraph(row['promitheftis'], name_style),
        ]
        for yid, _ in ylika_order:
            v = row['ylika'].get(yid)
            cells.append(Paragraph(fmt_num(v) if v else '', cell_style))
        table_rows.append(cells)

    # Ανοιχτό header color
    header_color = colors.HexColor('#4a7fc1')
    t = Table(table_rows, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND',     (0,0), (-1,0), header_color),
        ('TEXTCOLOR',      (0,0), (-1,0), colors.white),
        ('VALIGN',         (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN',          (0,0), (-1,-1), 'CENTER'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#eef2f7')]),
        ('GRID',           (0,0), (-1,-1), 0.3, colors.HexColor('#aabbd0')),
        ('TOPPADDING',     (0,0), (-1,-1), 2),
        ('BOTTOMPADDING',  (0,0), (-1,-1), 2),
        ('LEFTPADDING',    (0,0), (-1,-1), 2),
        ('RIGHTPADDING',   (0,0), (-1,-1), 2),
    ]))
    story.append(t)
    doc.build(story)
    return buf.getvalue()


# ─── Excel ────────────────────────────────────────────────────────────────────

def export_excel(kiniseis: list, yliko_label: str, period_label: str) -> bytes:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    ylika_order, rows = build_rows(kiniseis)
    n_ylika    = len(ylika_order)
    total_cols = 5 + n_ylika

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Βιβλίο Εκρηκτικών"

    last_col = get_column_letter(total_cols)
    ws.merge_cells(f'A1:{last_col}1')
    ws['A1'] = "ΒΙΒΛΙΟ ΕΚΡΗΚΤΙΚΩΝ ΥΛΩΝ"
    ws['A1'].font = Font(bold=True, size=13)
    ws['A1'].alignment = Alignment(horizontal='center')

    ws.merge_cells(f'A2:{last_col}2')
    ws['A2'] = f"Υλικό: {yliko_label}  |  Περίοδος: {period_label}  |  Εκτύπωση: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    ws['A2'].alignment = Alignment(horizontal='center')

    navy_fill = PatternFill("solid", fgColor="4A7FC1")
    navy_font = Font(bold=True, color="FFFFFF", size=9)
    thin      = Side(style='thin', color="AABBD0")
    border    = Border(left=thin, right=thin, top=thin, bottom=thin)
    alt_fill  = PatternFill("solid", fgColor="EEF2F7")

    fixed_headers = ['Α/Α', 'Ημερομηνία', 'Αρ. Παραστ.', 'Αρ. Άδειας', 'Προμηθευτής']
    fixed_widths  = [5, 12, 12, 10, 20]
    yliko_headers = [f"{onoma}\n({monada})" for _, (onoma, monada) in ylika_order]

    for col, (h, w) in enumerate(zip(fixed_headers + yliko_headers,
                                      fixed_widths + [14]*n_ylika), 1):
        cell = ws.cell(row=4, column=col, value=h)
        cell.fill = navy_fill
        cell.font = navy_font
        cell.alignment = Alignment(horizontal='center', wrap_text=True)
        cell.border = border
        ws.column_dimensions[get_column_letter(col)].width = w
    ws.row_dimensions[4].height = 35

    for r_idx, row in enumerate(rows, 5):
        fill = alt_fill if r_idx % 2 == 0 else None
        # Μετατροπή ημερομηνίας
        fixed_vals = [r_idx-4, fmt_date(row['imerominia']), row['parstatiko'],
                      row['adeia'], row['promitheftis']]
        yliko_vals = [row['ylika'].get(yid) for yid, _ in ylika_order]

        for col, val in enumerate(fixed_vals + yliko_vals, 1):
            cell = ws.cell(row=r_idx, column=col, value=val)
            cell.border = border
            if fill: cell.fill = fill
            if col <= 2:
                cell.alignment = Alignment(horizontal='center')
            if col > 5 and val is not None:
                cell.number_format = '#,##0.000'
                cell.alignment = Alignment(horizontal='right')

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
