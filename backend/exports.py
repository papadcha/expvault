"""
Εξαγωγή βιβλίου εκρηκτικών.
Μορφή: μία γραμμή ανά τιμολόγιο, δυναμικές στήλες ανά υλικό.
"""
import io
import os
from datetime import datetime
from collections import defaultdict, OrderedDict

def find_font(names):
    """Ψάχνει για TTF font σε κοινά paths."""
    import glob
    search_dirs = [
        '/usr/share/fonts',
        '/usr/local/share/fonts',
        os.path.expanduser('~/.fonts'),
        os.path.expanduser('~/.local/share/fonts'),
    ]
    for name in names:
        for d in search_dirs:
            matches = glob.glob(f'{d}/**/{name}', recursive=True)
            if matches:
                return matches[0]
    return None

FONT_REGULAR = find_font(['LiberationSans-Regular.ttf', 'FreeSans.ttf', 'DejaVuSans.ttf'])
FONT_BOLD    = find_font(['LiberationSans-Bold.ttf', 'FreeSansBold.ttf', 'DejaVuSans-Bold.ttf'])

def register_fonts():
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    try:
        pdfmetrics.getFont('GreekFont')
    except:
        if FONT_REGULAR:
            pdfmetrics.registerFont(TTFont('GreekFont',      FONT_REGULAR))
            pdfmetrics.registerFont(TTFont('GreekFont-Bold', FONT_BOLD or FONT_REGULAR))
        # Fallback σε Helvetica αν δεν βρεθεί font


def build_rows(kiniseis):
    """
    Επιστρέφει:
      - ylika_order: λίστα (yliko_id, onoma, monada) με σειρά εμφάνισης
      - rows: λίστα dicts με τα δεδομένα κάθε γραμμής (ανά παραστατικό+ημερομηνία)
    """
    # Συλλογή μοναδικών υλικών με σειρά πρώτης εμφάνισης
    ylika_order = OrderedDict()  # yliko_id → (onoma, monada)
    for k in kiniseis:
        yid = k['yliko_id']
        if yid not in ylika_order:
            ylika_order[yid] = (k['yliko_onoma'], k['monada_metrisis'])

    # Ομαδοποίηση ανά (imerominia, arithmos_parstatikos, adeia, promitheftis)
    # Κλειδί: tuple για σωστή σειρά
    row_keys = OrderedDict()  # key → index
    row_data = []             # λίστα από dicts

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
                'ylika':        {}   # yliko_id → posotita
            })
        idx = row_keys[key]
        yid = k['yliko_id']
        pos = k['posotita'] if k['tipos'] == 'ΕΙΣΑΓΩΓΗ' else -k['posotita']
        row_data[idx]['ylika'][yid] = row_data[idx]['ylika'].get(yid, 0) + pos

    return list(ylika_order.items()), row_data


def fmt(val):
    if val is None or val == 0:
        return ''
    return f"{val:,.3f}".replace(',', 'X').replace('.', ',').replace('X', '.')


# ─── PDF ─────────────────────────────────────────────────────────────────────

def export_pdf(kiniseis: list, yliko_label: str, period_label: str) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import cm, mm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_CENTER

    register_fonts()
    F  = 'GreekFont'      if FONT_REGULAR else 'Helvetica'
    FB = 'GreekFont-Bold' if FONT_BOLD    else 'Helvetica-Bold'

    ylika_order, rows = build_rows(kiniseis)

    buf = io.BytesIO()
    # Αν υπάρχουν πολλά υλικά χρησιμοποίησε μεγαλύτερο χαρτί
    pagesize = landscape(A4)
    doc = SimpleDocTemplate(buf, pagesize=pagesize,
                            leftMargin=1*cm, rightMargin=1*cm,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)

    title_style = ParagraphStyle('t', fontSize=11, fontName=FB, alignment=TA_CENTER, spaceAfter=3)
    sub_style   = ParagraphStyle('s', fontSize=7,  fontName=F,  alignment=TA_CENTER, spaceAfter=8)
    hdr_style   = ParagraphStyle('h', fontSize=6,  fontName=FB, alignment=TA_CENTER, leading=7)
    cell_style  = ParagraphStyle('c', fontSize=6.5,fontName=F,  alignment=TA_CENTER, leading=8)

    story = []
    story.append(Paragraph("ΒΙΒΛΙΟ ΕΚΡΗΚΤΙΚΩΝ ΥΛΩΝ", title_style))
    story.append(Paragraph(
        f"Υλικό: {yliko_label}  |  Περίοδος: {period_label}  |  "
        f"Εκτύπωση: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        sub_style))

    # Στήλες: Α/Α | Ημ/νία | Παραστ. | [υλικό1] [υλικό2] ...
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

    # Πλάτη στηλών
    page_w = pagesize[0] - 2*cm  # διαθέσιμο πλάτος
    fixed_w = [1*cm, 2*cm, 1.8*cm, 1.8*cm, 3*cm]
    remaining = page_w - sum(fixed_w)
    n_ylika = len(ylika_order)
    yliko_w = max(1.5*cm, remaining / n_ylika) if n_ylika else 2*cm
    col_widths = fixed_w + [yliko_w] * n_ylika

    # Γραμμές δεδομένων
    table_rows = [headers]
    for i, row in enumerate(rows, 1):
        cells = [
            str(i),
            row['imerominia'],
            row['parstatiko'],
            row['adeia'],
            Paragraph(row['promitheftis'], cell_style),
        ]
        for yid, (onoma, monada) in ylika_order:
            v = row['ylika'].get(yid)
            cells.append(fmt(v) if v else '')
        table_rows.append(cells)

    t = Table(table_rows, colWidths=col_widths, repeatRows=1)
    navy = colors.HexColor('#1a365d')
    t.setStyle(TableStyle([
        ('BACKGROUND',     (0,0), (-1,0), navy),
        ('TEXTCOLOR',      (0,0), (-1,0), colors.white),
        ('FONTNAME',       (0,0), (-1,0), FB),
        ('FONTSIZE',       (0,0), (-1,0), 6),
        ('VALIGN',         (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN',          (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME',       (0,1), (-1,-1), F),
        ('FONTSIZE',       (0,1), (-1,-1), 6.5),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f0f4f8')]),
        ('GRID',           (0,0), (-1,-1), 0.4, colors.HexColor('#cbd5e0')),
        ('TOPPADDING',     (0,0), (-1,-1), 3),
        ('BOTTOMPADDING',  (0,0), (-1,-1), 3),
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
    n_ylika = len(ylika_order)
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

    navy_fill   = PatternFill("solid", fgColor="1A365D")
    navy_font   = Font(bold=True, color="FFFFFF", size=9)
    thin        = Side(style='thin', color="CBD5E0")
    border      = Border(left=thin, right=thin, top=thin, bottom=thin)
    alt_fill    = PatternFill("solid", fgColor="F0F4F8")

    # Headers
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

    # Δεδομένα
    for r_idx, row in enumerate(rows, 5):
        fill = alt_fill if r_idx % 2 == 0 else None
        fixed_vals = [r_idx-4, row['imerominia'], row['parstatiko'],
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
