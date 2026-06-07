"""
Εξαγωγή βιβλίου εκρηκτικών.
Διάταξη: αριστερά αγορές/επιστροφές, δεξιά καταναλώσεις.
Μία γραμμή ανά παραστατικό αγοράς + υπογραμμή επιστροφής.
"""
import io, os, glob
from datetime import datetime
from collections import OrderedDict

def find_font(names):
    search_dirs = [
        '/usr/share/fonts', '/usr/share/fonts/TTF',
        '/usr/local/share/fonts',
        os.path.expanduser('~/.fonts'),
        os.path.expanduser('~/.local/share/fonts'),
        os.path.expanduser('~/.cargo'),
    ]
    for name in names:
        for d in search_dirs:
            matches = glob.glob(f'{d}/**/{name}', recursive=True)
            if matches: return matches[0]
            direct = os.path.join(d, name)
            if os.path.exists(direct): return direct
    return None

FONT_REGULAR = find_font(['Iosevka-Regular.ttc','JetBrainsMono-Regular.ttf','LiberationMono-Regular.ttf','FreeMono.ttf'])
FONT_BOLD    = find_font(['Iosevka-Bold.ttc','JetBrainsMono-Bold.ttf','LiberationMono-Bold.ttf','FreeMonoBold.ttf'])
FONT_SANS_R  = find_font(['LiberationSans-Regular.ttf','FreeSans.ttf'])
FONT_SANS_B  = find_font(['LiberationSans-Bold.ttf','FreeSansBold.ttf'])

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
    if not s: return ''
    try:
        p = s.split('-')
        if len(p)==3 and len(p[0])==4: return f"{p[2]}/{p[1]}/{p[0]}"
    except: pass
    return s

def fmt_num(val):
    if val is None or val == 0: return ''
    return f"{val:,.3f}".replace(',','X').replace('.',',').replace('X','.')

def get_ylika_order(kiniseis):
    """Επιστρέφει υλικά με σειρά πρώτης εμφάνισης."""
    order = OrderedDict()
    for k in kiniseis:
        yid = k['yliko_id']
        if yid not in order:
            order[yid] = (k['yliko_onoma'], k['monada_metrisis'])
    return list(order.items())

def build_book_rows(kiniseis):
    """
    Επιστρέφει λίστα από εγγραφές βιβλίου:
    [
      {
        'auxon': int,
        'type': 'agora' | 'epistrofi' | 'katanalosi',
        'imerominia': str,
        'parstatiko': str,
        'adeia': str,
        'promitheftis': str,
        'ylika': {yid: posotita},   # αγορά/επιστροφή
        'katanalosi': {yid: posotita},  # μόνο για katanalosi
        'paratirishis': str,
        'aa': int or None,
      }
    ]
    Λογική:
    - ΕΙΣΑΓΩΓΗ → γραμμή 'agora' με Α/Α
    - ΕΞΑΓΩΓΗ με παραστατικό → γραμμή 'epistrofi' (υπογραμμή, χωρίς Α/Α)
    - ΕΞΑΓΩΓΗ χωρίς παραστατικό → γραμμή 'katanalosi' στη δεξιά πλευρά
    """
    # Ομαδοποίηση ανά παραστατικό για αγορές
    agores   = OrderedDict()  # key → row
    epistrofes = []
    katanaliseis = []
    aa = 1

    for k in kiniseis:
        yid = k['yliko_id']
        tipos = k['tipos']
        parst = k.get('arithmos_parstatikos') or ''
        imer  = k['imerominia']
        adeia = k.get('arithmos_adeias') or ''
        prom  = k.get('promitheftis_onoma') or ''
        par   = k.get('paratirishis') or ''

        if tipos == 'ΕΙΣΑΓΩΓΗ':
            key = (imer, parst, adeia, prom)
            if key not in agores:
                agores[key] = {
                    'type': 'agora', 'aa': aa,
                    'imerominia': imer, 'parstatiko': parst,
                    'adeia': adeia, 'promitheftis': prom,
                    'ylika': {}, 'paratirishis': par
                }
                aa += 1
            agores[key]['ylika'][yid] = agores[key]['ylika'].get(yid, 0) + k['posotita']

        elif tipos == 'ΕΞΑΓΩΓΗ' and parst:
            # Επιστροφή — υπογραμμή
            key = (imer, parst, adeia, prom)
            found = None
            for e in epistrofes:
                if e['parstatiko'] == parst and e['imerominia'] == imer:
                    found = e; break
            if not found:
                found = {
                    'type': 'epistrofi', 'aa': None,
                    'imerominia': imer, 'parstatiko': parst,
                    'adeia': adeia, 'promitheftis': prom,
                    'ylika': {}, 'paratirishis': 'ΕΠΙΣΤΡΟΦΗ'
                }
                epistrofes.append(found)
            found['ylika'][yid] = found['ylika'].get(yid, 0) + k['posotita']

        else:
            # Κατανάλωση
            key = (imer, parst)
            found = None
            for c in katanaliseis:
                if c['imerominia'] == imer and c['parstatiko'] == parst:
                    found = c; break
            if not found:
                found = {
                    'type': 'katanalosi', 'aa': None,
                    'imerominia': imer, 'parstatiko': parst,
                    'adeia': '', 'promitheftis': '',
                    'ylika': {}, 'paratirishis': par
                }
                katanaliseis.append(found)
            found['ylika'][yid] = found['ylika'].get(yid, 0) + k['posotita']

    # Χτίσε τελική λίστα: αγορά → επιστροφή (αν υπάρχει) → ...
    # Κατανάλωση αντιστοιχεί σε κάθε αγορά βάσει ημερομηνίας
    rows = []
    epi_used = set()
    kat_used = set()

    for key, agora in agores.items():
        rows.append(agora)
        # Βρες επιστροφή με ίδια ημερομηνία
        for i, e in enumerate(epistrofes):
            if i not in epi_used and e['imerominia'] == agora['imerominia']:
                rows.append(e)
                epi_used.add(i)
                break

    # Κατανάλωση ξεχωριστά στη δεξιά — δεν εμφανίζεται ως γραμμή αριστερά
    # αλλά αντιστοιχεί σε γραμμή αγοράς της ίδιας ημερομηνίας
    kat_by_date = {}
    for k in katanaliseis:
        d = k['imerominia']
        if d not in kat_by_date:
            kat_by_date[d] = {}
        for yid, pos in k['ylika'].items():
            kat_by_date[d][yid] = kat_by_date[d].get(yid, 0) + pos

    return rows, kat_by_date


# ─── PDF ─────────────────────────────────────────────────────────────────────

def export_pdf(kiniseis: list, yliko_label: str, period_label: str) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT

    register_fonts()
    F   = 'Mono'      if FONT_REGULAR else 'Courier'
    FB  = 'Mono-Bold' if FONT_BOLD    else 'Courier-Bold'
    SF  = 'Sans'      if FONT_SANS_R  else 'Helvetica'
    SFB = 'Sans-Bold' if FONT_SANS_B  else 'Helvetica-Bold'

    ylika_order = get_ylika_order(kiniseis)
    rows, kat_by_date = build_book_rows(kiniseis)
    n = len(ylika_order)

    buf = io.BytesIO()
    pagesize = landscape(A4)
    doc = SimpleDocTemplate(buf, pagesize=pagesize,
                            leftMargin=0.7*cm, rightMargin=0.7*cm,
                            topMargin=1.2*cm, bottomMargin=1.2*cm)

    TS  = ParagraphStyle('t',  fontSize=10, fontName=SFB, alignment=TA_CENTER, spaceAfter=2)
    SS  = ParagraphStyle('s',  fontSize=6.5,fontName=SF,  alignment=TA_CENTER, spaceAfter=6)
    HS  = ParagraphStyle('h',  fontSize=5,  fontName=FB,  alignment=TA_CENTER, leading=6)
    CS  = ParagraphStyle('c',  fontSize=5.5,fontName=F,   alignment=TA_CENTER, leading=6)
    NS  = ParagraphStyle('n',  fontSize=5,  fontName=F,   alignment=TA_LEFT,   leading=6)
    RS  = ParagraphStyle('r',  fontSize=5,  fontName=F,   alignment=TA_CENTER, leading=6, textColor=colors.HexColor('#c53030'))

    story = []
    story.append(Paragraph("ΒΙΒΛΙΟ ΑΓΟΡΑΣ ΚΑΙ ΚΑΤΑΝΑΛΩΣΗΣ ΕΚΡΗΚΤΙΚΩΝ ΥΛΩΝ", TS))
    story.append(Paragraph(
        f"Περίοδος: {period_label}  |  Εκτύπωση: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        SS))

    # ── Πλάτη στηλών ─────────────────────────────────────────────────────────
    page_w = pagesize[0] - 1.4*cm

    # Αριστερά: Α/Α | Ημ/νία | Παραστ | Άδεια | Προμηθ | [υλικά...]
    # Δεξιά:    Ημ/νία κατ. | [υλικά...] | Παρατ.
    # Διαχωριστής: 0.15cm
    left_fixed  = [0.7, 1.6, 1.5, 1.4, 2.5]   # cm
    right_fixed = [1.6, 2.0]                    # Ημ/νία κατ. + Παρατ.
    sep         = 0.15                           # cm διαχωριστής

    left_fixed_w  = sum(left_fixed)
    right_fixed_w = sum(right_fixed)
    yliko_space   = page_w - left_fixed_w - right_fixed_w - sep - (0.15 * (n-1) if n > 1 else 0)
    yw = max(1.2, yliko_space / (2 * n)) if n else 1.5   # cm ανά υλικό

    left_col_w  = [x*cm for x in left_fixed]  + [yw*cm]*n
    right_col_w = [1.6*cm]                     + [yw*cm]*n + [2.0*cm]
    sep_col_w   = [sep*cm]

    all_col_w = left_col_w + sep_col_w + right_col_w
    total_cols_left  = len(left_col_w)
    total_cols_right = len(right_col_w)
    sep_col_idx      = total_cols_left
    total_cols       = len(all_col_w)

    # ── Headers ───────────────────────────────────────────────────────────────
    yliko_hdrs = [Paragraph(f"{on}\n({mo})", HS) for _, (on, mo) in ylika_order]

    left_hdr  = [Paragraph('Α/Α',HS), Paragraph('Ημερ.',HS),
                 Paragraph('Παραστ.',HS), Paragraph('Αρ.Άδ.',HS),
                 Paragraph('Προμηθευτής',HS)] + yliko_hdrs
    sep_hdr   = [Paragraph('',HS)]
    right_hdr = [Paragraph('Ημ.Κατ.',HS)] + yliko_hdrs + [Paragraph('Παρατ.',HS)]

    header_row = left_hdr + sep_hdr + right_hdr

    # ── Section headers ───────────────────────────────────────────────────────
    # Γραμμή τίτλου "ΑΓΟΡΕΣ / ΕΠΙΣΤΡΟΦΕΣ" και "ΚΑΤΑΝΑΛΩΣΕΙΣ"
    left_title_row  = [Paragraph('ΑΓΟΡΕΣ / ΕΠΙΣΤΡΟΦΕΣ', HS)] + ['']*(len(left_col_w)-1)
    sep_title        = [Paragraph('',HS)]
    right_title_row = [Paragraph('ΚΑΤΑΝΑΛΩΣΕΙΣ', HS)] + ['']*(len(right_col_w)-1)
    title_row = left_title_row + sep_title + right_title_row

    table_data = [title_row, header_row]
    style_cmds = [
        # Title row
        ('BACKGROUND', (0,0), (sep_col_idx-1, 0), colors.HexColor('#1a365d')),
        ('BACKGROUND', (sep_col_idx+1,0), (-1,0), colors.HexColor('#2d6a4f')),
        ('TEXTCOLOR',  (0,0), (-1,0), colors.white),
        ('SPAN',       (0,0), (sep_col_idx-1, 0)),
        ('SPAN',       (sep_col_idx+1,0), (-1,0)),
        ('ALIGN',      (0,0), (-1,0), 'CENTER'),
        # Header row
        ('BACKGROUND', (0,1), (sep_col_idx-1, 1), colors.HexColor('#4a7fc1')),
        ('BACKGROUND', (sep_col_idx+1,1), (-1,1), colors.HexColor('#52b788')),
        ('TEXTCOLOR',  (0,1), (-1,1), colors.white),
        ('ALIGN',      (0,0), (-1,-1), 'CENTER'),
        ('VALIGN',     (0,0), (-1,-1), 'MIDDLE'),
        # Separator column
        ('BACKGROUND', (sep_col_idx,0), (sep_col_idx,-1), colors.HexColor('#dee2e6')),
        # Grid
        ('GRID',       (0,0), (sep_col_idx-1,-1), 0.3, colors.HexColor('#aabbd0')),
        ('GRID',       (sep_col_idx+1,0), (-1,-1), 0.3, colors.HexColor('#8ece9e')),
        # Padding
        ('TOPPADDING',    (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('LEFTPADDING',   (0,0), (-1,-1), 2),
        ('RIGHTPADDING',  (0,0), (-1,-1), 2),
    ]

    # ── Data rows ─────────────────────────────────────────────────────────────
    data_row_idx = 2  # 0=title, 1=header
    alt = colors.HexColor('#eef2f7')
    alt2 = colors.HexColor('#d8f3dc')

    # Κατανάλωση — κατανέμεται στις γραμμές αγοράς ίδιας ημερομηνίας
    kat_used_dates = set()

    for row in rows:
        is_epi = row['type'] == 'epistrofi'
        imer   = row['imerominia']

        # Αριστερή πλευρά
        aa_cell    = Paragraph(str(row['aa']) if row['aa'] else '—', RS if is_epi else CS)
        imer_cell  = Paragraph(fmt_date(imer), RS if is_epi else CS)
        parst_cell = Paragraph(row['parstatiko'], RS if is_epi else CS)
        adeia_cell = Paragraph(row['adeia'], RS if is_epi else CS)
        prom_cell  = Paragraph(row['promitheftis'], RS if is_epi else NS)

        left_cells = [aa_cell, imer_cell, parst_cell, adeia_cell, prom_cell]
        for yid, _ in ylika_order:
            v = row['ylika'].get(yid)
            style = RS if is_epi else CS
            left_cells.append(Paragraph(fmt_num(v) if v else '—', style))

        # Δεξιά πλευρά — κατανάλωση
        if not is_epi and imer not in kat_used_dates:
            kat = kat_by_date.get(imer, {})
            kat_used_dates.add(imer)
            kat_imer = Paragraph(fmt_date(imer), CS)
            right_cells = [kat_imer]
            for yid, _ in ylika_order:
                v = kat.get(yid)
                right_cells.append(Paragraph(fmt_num(v) if v else '—', CS))
            right_cells.append(Paragraph('', CS))
        else:
            right_cells = [Paragraph('', CS)] + [Paragraph('', CS)]*n + [Paragraph('', CS)]

        data_row = left_cells + [Paragraph('', CS)] + right_cells
        table_data.append(data_row)

        # Χρώμα γραμμής
        if is_epi:
            style_cmds.append(('BACKGROUND', (0, data_row_idx), (sep_col_idx-1, data_row_idx), colors.HexColor('#fff0f0')))
            style_cmds.append(('TEXTCOLOR',  (0, data_row_idx), (sep_col_idx-1, data_row_idx), colors.HexColor('#c53030')))
        elif data_row_idx % 2 == 0:
            style_cmds.append(('BACKGROUND', (0, data_row_idx), (sep_col_idx-1, data_row_idx), alt))
            style_cmds.append(('BACKGROUND', (sep_col_idx+1, data_row_idx), (-1, data_row_idx), alt2))

        data_row_idx += 1

    t = Table(table_data, colWidths=all_col_w, repeatRows=2)
    t.setStyle(TableStyle(style_cmds))
    story.append(t)
    doc.build(story)
    return buf.getvalue()


# ─── Excel ────────────────────────────────────────────────────────────────────

def export_excel(kiniseis: list, yliko_label: str, period_label: str) -> bytes:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    ylika_order = get_ylika_order(kiniseis)
    rows, kat_by_date = build_book_rows(kiniseis)
    n = len(ylika_order)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Βιβλίο Εκρηκτικών"

    # Στήλες: Α/Α | Ημ | Παραστ | Άδεια | Προμηθ | [υλικά] | | Ημ.Κατ | [υλικά] | Παρατ
    total_left  = 5 + n
    sep_col     = total_left + 1
    total_right = 1 + n + 1
    total_cols  = total_left + 1 + total_right

    # Τίτλος
    ws.merge_cells(f'A1:{get_column_letter(total_cols)}1')
    ws['A1'] = "ΒΙΒΛΙΟ ΑΓΟΡΑΣ ΚΑΙ ΚΑΤΑΝΑΛΩΣΗΣ ΕΚΡΗΚΤΙΚΩΝ ΥΛΩΝ"
    ws['A1'].font = Font(bold=True, size=13)
    ws['A1'].alignment = Alignment(horizontal='center')

    ws.merge_cells(f'A2:{get_column_letter(total_cols)}2')
    ws['A2'] = f"Περίοδος: {period_label}  |  Εκτύπωση: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    ws['A2'].alignment = Alignment(horizontal='center')

    # Section headers
    ws.merge_cells(f'A3:{get_column_letter(total_left)}3')
    ws['A3'] = "ΑΓΟΡΕΣ / ΕΠΙΣΤΡΟΦΕΣ"
    ws['A3'].fill = PatternFill("solid", fgColor="1A365D")
    ws['A3'].font = Font(bold=True, color="FFFFFF", size=10)
    ws['A3'].alignment = Alignment(horizontal='center')

    r_start = sep_col + 1
    ws.merge_cells(f'{get_column_letter(r_start)}3:{get_column_letter(total_cols)}3')
    c = ws.cell(row=3, column=r_start, value="ΚΑΤΑΝΑΛΩΣΕΙΣ")
    c.fill = PatternFill("solid", fgColor="2D6A4F")
    c.font = Font(bold=True, color="FFFFFF", size=10)
    c.alignment = Alignment(horizontal='center')

    # Column headers
    left_hdrs  = ['Α/Α','Ημερομηνία','Παραστατικό','Αρ. Άδειας','Προμηθευτής'] + \
                 [f"{on}\n({mo})" for _,(on,mo) in ylika_order]
    right_hdrs = ['Ημ. Κατανάλωσης'] + \
                 [f"{on}\n({mo})" for _,(on,mo) in ylika_order] + ['Παρατηρήσεις']

    navy_fill  = PatternFill("solid", fgColor="4A7FC1")
    green_fill = PatternFill("solid", fgColor="52B788")
    navy_font  = Font(bold=True, color="FFFFFF", size=9)
    thin       = Side(style='thin', color="AABBD0")
    border     = Border(left=thin, right=thin, top=thin, bottom=thin)

    for ci, h in enumerate(left_hdrs, 1):
        cell = ws.cell(row=4, column=ci, value=h)
        cell.fill = navy_fill; cell.font = navy_font
        cell.alignment = Alignment(horizontal='center', wrap_text=True)
        cell.border = border
        fixed_widths = [5, 12, 12, 10, 18] + [12]*n
        ws.column_dimensions[get_column_letter(ci)].width = fixed_widths[ci-1] if ci <= len(fixed_widths) else 12

    for ci, h in enumerate(right_hdrs, sep_col+1):
        cell = ws.cell(row=4, column=ci, value=h)
        cell.fill = green_fill; cell.font = navy_font
        cell.alignment = Alignment(horizontal='center', wrap_text=True)
        cell.border = border

    ws.row_dimensions[3].height = 20
    ws.row_dimensions[4].height = 35

    alt_fill  = PatternFill("solid", fgColor="EEF2F7")
    alt2_fill = PatternFill("solid", fgColor="D8F3DC")
    red_font  = Font(color="C53030", bold=False, size=9)
    kat_used_dates = set()

    for ri, row in enumerate(rows, 5):
        is_epi = row['type'] == 'epistrofi'
        imer   = row['imerominia']
        fill   = alt_fill if ri % 2 == 0 else None

        left_vals = [
            row['aa'] if row['aa'] else '',
            fmt_date(imer), row['parstatiko'], row['adeia'], row['promitheftis']
        ] + [row['ylika'].get(yid) for yid,_ in ylika_order]

        for ci, val in enumerate(left_vals, 1):
            cell = ws.cell(row=ri, column=ci, value=val)
            cell.border = border
            if is_epi:
                cell.font = red_font
                cell.fill = PatternFill("solid", fgColor="FFF0F0")
            elif fill:
                cell.fill = fill
            if ci > 5 and val is not None and isinstance(val, (int,float)):
                cell.number_format = '#,##0.000'
                cell.alignment = Alignment(horizontal='right')
            elif ci <= 2:
                cell.alignment = Alignment(horizontal='center')

        # Κατανάλωση
        if not is_epi and imer not in kat_used_dates:
            kat = kat_by_date.get(imer, {})
            kat_used_dates.add(imer)
            right_vals = [fmt_date(imer)] + [kat.get(yid) for yid,_ in ylika_order] + ['']
            for ci, val in enumerate(right_vals, sep_col+1):
                cell = ws.cell(row=ri, column=ci, value=val)
                cell.border = border
                if fill: cell.fill = alt2_fill
                if isinstance(val, (int,float)) and val is not None:
                    cell.number_format = '#,##0.000'
                    cell.alignment = Alignment(horizontal='right')

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
