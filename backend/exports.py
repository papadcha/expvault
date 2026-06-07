"""
Εξαγωγή βιβλίου εκρηκτικών.
Δύο ξεχωριστοί πίνακες δίπλα-δίπλα: αριστερά αγορές/επιστροφές, δεξιά καταναλώσεις.
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
    order = OrderedDict()
    for k in kiniseis:
        yid = k['yliko_id']
        if yid not in order:
            order[yid] = (k['yliko_onoma'], k['monada_metrisis'])
    return list(order.items())

def build_book_rows(kiniseis):
    agores     = OrderedDict()
    epistrofes = []
    katanaliseis = []
    aa = 1

    for k in kiniseis:
        yid   = k['yliko_id']
        tipos = k['tipos']
        parst = k.get('arithmos_parstatikos') or ''
        imer  = k['imerominia']
        adeia = k.get('arithmos_adeias') or ''
        prom  = k.get('promitheftis_onoma') or ''
        par   = k.get('paratirishis') or ''

        if tipos == 'ΕΙΣΑΓΩΓΗ':
            key = (imer, parst, adeia, prom)
            if key not in agores:
                agores[key] = {'type':'agora','aa':aa,'imerominia':imer,
                               'parstatiko':parst,'adeia':adeia,'promitheftis':prom,
                               'ylika':{},'paratirishis':par}
                aa += 1
            agores[key]['ylika'][yid] = agores[key]['ylika'].get(yid,0) + k['posotita']

        elif tipos == 'ΕΞΑΓΩΓΗ' and parst:
            found = next((e for e in epistrofes if e['parstatiko']==parst and e['imerominia']==imer), None)
            if not found:
                found = {'type':'epistrofi','aa':None,'imerominia':imer,
                         'parstatiko':parst,'adeia':adeia,'promitheftis':prom,
                         'ylika':{},'paratirishis':'ΕΠΙΣΤΡΟΦΗ'}
                epistrofes.append(found)
            found['ylika'][yid] = found['ylika'].get(yid,0) + k['posotita']

        else:
            found = next((c for c in katanaliseis if c['imerominia']==imer), None)
            if not found:
                found = {'type':'katanalosi','aa':None,'imerominia':imer,
                         'parstatiko':'','adeia':'','promitheftis':'',
                         'ylika':{},'paratirishis':par}
                katanaliseis.append(found)
            found['ylika'][yid] = found['ylika'].get(yid,0) + k['posotita']

    # Συναρμολόγηση: αγορά → επιστροφή ίδιας ημερομηνίας
    rows = []
    epi_used = set()
    for key, agora in agores.items():
        rows.append(agora)
        for i, e in enumerate(epistrofes):
            if i not in epi_used and e['imerominia'] == agora['imerominia']:
                rows.append(e)
                epi_used.add(i)
                break

    # Κατανάλωση ανά ημερομηνία
    kat_by_date = {}
    for k in katanaliseis:
        d = k['imerominia']
        if d not in kat_by_date:
            kat_by_date[d] = {}
        for yid, pos in k['ylika'].items():
            kat_by_date[d][yid] = kat_by_date[d].get(yid,0) + pos

    return rows, kat_by_date


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

    ylika_order = get_ylika_order(kiniseis)
    rows, kat_by_date = build_book_rows(kiniseis)
    n = len(ylika_order)

    pagesize = landscape(A4)
    page_w   = pagesize[0] - 1.4*cm

    # Υπολογισμός πλατών — page_w σε points, fixed_total σε cm → μετατροπή
    L_FIXED = [0.6, 1.5, 1.3, 1.2, 2.2]
    R_FIXED = [1.5, 1.5]
    SEP     = 0.15

    fixed_total_cm = sum(L_FIXED) + sum(R_FIXED) + SEP
    available_cm   = page_w / cm  # μετατροπή points → cm
    yw = max(0.9, (available_cm - fixed_total_cm) / (2 * n)) if n else 1.5

    L_WIDTHS = [x*cm for x in L_FIXED] + [yw*cm]*n
    R_WIDTHS = [R_FIXED[0]*cm] + [yw*cm]*n + [R_FIXED[1]*cm]

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=pagesize,
                            leftMargin=0.7*cm, rightMargin=0.7*cm,
                            topMargin=1.2*cm, bottomMargin=1.2*cm)

    TS = ParagraphStyle('t', fontSize=9,  fontName=SFB, alignment=TA_CENTER, spaceAfter=2)
    SS = ParagraphStyle('s', fontSize=6,  fontName=SF,  alignment=TA_CENTER, spaceAfter=4)
    HS = ParagraphStyle('h', fontSize=5,  fontName=FB,  alignment=TA_CENTER, leading=6)
    CS = ParagraphStyle('c', fontSize=5.5,fontName=F,   alignment=TA_CENTER, leading=6)
    NS = ParagraphStyle('n', fontSize=5,  fontName=F,   alignment=TA_LEFT,   leading=6)
    ES = ParagraphStyle('e', fontSize=5,  fontName=FB,  alignment=TA_CENTER, leading=6,
                        textColor=colors.HexColor('#c53030'))

    NAVY  = colors.HexColor('#1a365d')
    GREEN = colors.HexColor('#2d6a4f')
    LNAVY = colors.HexColor('#4a7fc1')
    LGRN  = colors.HexColor('#52b788')
    ALT   = colors.HexColor('#eef2f7')
    ALT2  = colors.HexColor('#d8f3dc')
    RED   = colors.HexColor('#fff0f0')
    GRID  = colors.HexColor('#aabbd0')
    GGRN  = colors.HexColor('#8ece9e')

    yliko_hdrs = [Paragraph(f"{on}\n({mo})", HS) for _, (on, mo) in ylika_order]

    def make_left_table():
        # Header rows
        title_row  = [Paragraph('ΑΓΟΡΕΣ / ΕΠΙΣΤΡΟΦΕΣ', HS)] + ['']*(len(L_WIDTHS)-1)
        header_row = [Paragraph('Α/Α',HS), Paragraph('Ημ/νία',HS),
                      Paragraph('Παραστ.',HS), Paragraph('Αρ.Άδ.',HS),
                      Paragraph('Προμηθευτής',HS)] + yliko_hdrs

        data = [title_row, header_row]
        style = [
            ('SPAN',         (0,0), (-1,0)),
            ('BACKGROUND',   (0,0), (-1,0), NAVY),
            ('BACKGROUND',   (0,1), (-1,1), LNAVY),
            ('TEXTCOLOR',    (0,0), (-1,1), colors.white),
            ('ALIGN',        (0,0), (-1,-1), 'CENTER'),
            ('VALIGN',       (0,0), (-1,-1), 'MIDDLE'),
            ('GRID',         (0,0), (-1,-1), 0.3, GRID),
            ('TOPPADDING',   (0,0), (-1,-1), 2),
            ('BOTTOMPADDING',(0,0), (-1,-1), 2),
            ('LEFTPADDING',  (0,0), (-1,-1), 2),
            ('RIGHTPADDING', (0,0), (-1,-1), 2),
        ]

        kat_used = set()
        for ri, row in enumerate(rows, 2):
            is_epi = row['type'] == 'epistrofi'
            S = ES if is_epi else CS

            cells = [
                Paragraph(str(row['aa']) if row['aa'] else '', S),
                Paragraph(fmt_date(row['imerominia']), S),
                Paragraph(row['parstatiko'], S),
                Paragraph(row['adeia'], S),
                Paragraph(row['promitheftis'], ES if is_epi else NS),
            ]
            for yid, _ in ylika_order:
                v = row['ylika'].get(yid)
                cells.append(Paragraph(fmt_num(v) if v else '', S))
            data.append(cells)

            if is_epi:
                style.append(('BACKGROUND', (0,ri), (-1,ri), RED))
            elif ri % 2 == 1:
                style.append(('BACKGROUND', (0,ri), (-1,ri), ALT))

        return Table(data, colWidths=L_WIDTHS, repeatRows=2), style

    def make_right_table():
        title_row  = [Paragraph('ΚΑΤΑΝΑΛΩΣΕΙΣ', HS)] + ['']*(len(R_WIDTHS)-1)
        header_row = [Paragraph('Ημ. Κατ.',HS)] + yliko_hdrs + [Paragraph('Παρατ.',HS)]

        data = [title_row, header_row]
        style = [
            ('SPAN',         (0,0), (-1,0)),
            ('BACKGROUND',   (0,0), (-1,0), GREEN),
            ('BACKGROUND',   (0,1), (-1,1), LGRN),
            ('TEXTCOLOR',    (0,0), (-1,1), colors.white),
            ('ALIGN',        (0,0), (-1,-1), 'CENTER'),
            ('VALIGN',       (0,0), (-1,-1), 'MIDDLE'),
            ('GRID',         (0,0), (-1,-1), 0.3, GGRN),
            ('TOPPADDING',   (0,0), (-1,-1), 2),
            ('BOTTOMPADDING',(0,0), (-1,-1), 2),
            ('LEFTPADDING',  (0,0), (-1,-1), 2),
            ('RIGHTPADDING', (0,0), (-1,-1), 2),
        ]

        kat_used = set()
        for ri, row in enumerate(rows, 2):
            is_epi = row['type'] == 'epistrofi'
            imer   = row['imerominia']

            if not is_epi and imer not in kat_used:
                kat = kat_by_date.get(imer, {})
                kat_used.add(imer)
                cells = [Paragraph(fmt_date(imer), CS)]
                for yid, _ in ylika_order:
                    v = kat.get(yid)
                    cells.append(Paragraph(fmt_num(v) if v else '', CS))
                cells.append(Paragraph('', CS))
                if ri % 2 == 1:
                    style.append(('BACKGROUND', (0,ri), (-1,ri), ALT2))
            else:
                cells = [Paragraph('', CS)] + [Paragraph('', CS)]*(n+1)

            data.append(cells)

        return Table(data, colWidths=R_WIDTHS, repeatRows=2), style

    left_t,  left_s  = make_left_table()
    right_t, right_s = make_right_table()
    left_t.setStyle(TableStyle(left_s))
    right_t.setStyle(TableStyle(right_s))

    # Outer table: [left | sep | right]
    outer = Table(
        [[left_t, '', right_t]],
        colWidths=[sum(L_WIDTHS), SEP*cm, sum(R_WIDTHS)]
    )
    outer.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING',  (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING',   (0,0), (-1,-1), 0),
        ('BOTTOMPADDING',(0,0), (-1,-1), 0),
    ]))

    story = [
        Paragraph("ΒΙΒΛΙΟ ΑΓΟΡΑΣ ΚΑΙ ΚΑΤΑΝΑΛΩΣΗΣ ΕΚΡΗΚΤΙΚΩΝ ΥΛΩΝ", TS),
        Paragraph(f"Περίοδος: {period_label}  |  Εκτύπωση: {datetime.now().strftime('%d/%m/%Y %H:%M')}", SS),
        outer
    ]

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

    wb  = openpyxl.Workbook()
    ws  = wb.active
    ws.title = "Βιβλίο Εκρηκτικών"

    total_left  = 5 + n
    sep_col     = total_left + 1
    total_right = 1 + n + 1
    total_cols  = total_left + 1 + total_right
    last_col    = get_column_letter(total_cols)

    # Τίτλος
    ws.merge_cells(f'A1:{last_col}1')
    ws['A1'] = "ΒΙΒΛΙΟ ΑΓΟΡΑΣ ΚΑΙ ΚΑΤΑΝΑΛΩΣΗΣ ΕΚΡΗΚΤΙΚΩΝ ΥΛΩΝ"
    ws['A1'].font = Font(bold=True, size=12)
    ws['A1'].alignment = Alignment(horizontal='center')

    ws.merge_cells(f'A2:{last_col}2')
    ws['A2'] = f"Περίοδος: {period_label}  |  Εκτύπωση: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    ws['A2'].alignment = Alignment(horizontal='center')

    # Section headers
    ws.merge_cells(f'A3:{get_column_letter(total_left)}3')
    c = ws.cell(row=3, column=1, value="ΑΓΟΡΕΣ / ΕΠΙΣΤΡΟΦΕΣ")
    c.fill = PatternFill("solid", fgColor="1A365D")
    c.font = Font(bold=True, color="FFFFFF", size=10)
    c.alignment = Alignment(horizontal='center')

    ws.merge_cells(f'{get_column_letter(sep_col+1)}3:{last_col}3')
    c = ws.cell(row=3, column=sep_col+1, value="ΚΑΤΑΝΑΛΩΣΕΙΣ")
    c.fill = PatternFill("solid", fgColor="2D6A4F")
    c.font = Font(bold=True, color="FFFFFF", size=10)
    c.alignment = Alignment(horizontal='center')

    # Column headers
    navy_fill  = PatternFill("solid", fgColor="4A7FC1")
    green_fill = PatternFill("solid", fgColor="52B788")
    hdr_font   = Font(bold=True, color="FFFFFF", size=9)
    thin       = Side(style='thin', color="AABBD0")
    border     = Border(left=thin, right=thin, top=thin, bottom=thin)

    left_hdrs  = ['Α/Α','Ημερομηνία','Παραστατικό','Αρ. Άδειας','Προμηθευτής'] + \
                 [f"{on}\n({mo})" for _,(on,mo) in ylika_order]
    right_hdrs = ['Ημ. Κατανάλωσης'] + \
                 [f"{on}\n({mo})" for _,(on,mo) in ylika_order] + ['Παρατηρήσεις']
    left_widths = [5,12,12,10,20] + [13]*n

    for ci, (h, w) in enumerate(zip(left_hdrs, left_widths), 1):
        cell = ws.cell(row=4, column=ci, value=h)
        cell.fill = navy_fill; cell.font = hdr_font
        cell.alignment = Alignment(horizontal='center', wrap_text=True)
        cell.border = border
        ws.column_dimensions[get_column_letter(ci)].width = w

    for ci, h in enumerate(right_hdrs, sep_col+1):
        cell = ws.cell(row=4, column=ci, value=h)
        cell.fill = green_fill; cell.font = hdr_font
        cell.alignment = Alignment(horizontal='center', wrap_text=True)
        cell.border = border
        ws.column_dimensions[get_column_letter(ci)].width = 13 if ci > sep_col+1 else 16

    ws.row_dimensions[3].height = 18
    ws.row_dimensions[4].height = 32

    alt_fill  = PatternFill("solid", fgColor="EEF2F7")
    alt2_fill = PatternFill("solid", fgColor="D8F3DC")
    red_fill  = PatternFill("solid", fgColor="FFF0F0")
    red_font  = Font(color="C53030", bold=True, size=9)
    kat_used  = set()

    for ri, row in enumerate(rows, 5):
        is_epi = row['type'] == 'epistrofi'
        imer   = row['imerominia']
        fill   = red_fill if is_epi else (alt_fill if ri%2==0 else None)

        left_vals = [
            row['aa'] if row['aa'] else '',
            fmt_date(imer), row['parstatiko'], row['adeia'], row['promitheftis']
        ] + [row['ylika'].get(yid) for yid,_ in ylika_order]

        for ci, val in enumerate(left_vals, 1):
            cell = ws.cell(row=ri, column=ci, value=val)
            cell.border = border
            if fill: cell.fill = fill
            if is_epi: cell.font = red_font
            if ci > 5 and isinstance(val, (int,float)):
                cell.number_format = '#,##0.000'
                cell.alignment = Alignment(horizontal='right')
            else:
                cell.alignment = Alignment(horizontal='center' if ci<=2 else 'left')

        # Κατανάλωση δεξιά
        if not is_epi and imer not in kat_used:
            kat = kat_by_date.get(imer, {})
            kat_used.add(imer)
            right_vals = [fmt_date(imer)] + [kat.get(yid) for yid,_ in ylika_order] + ['']
            for ci, val in enumerate(right_vals, sep_col+1):
                cell = ws.cell(row=ri, column=ci, value=val)
                cell.border = border
                if ri%2==0: cell.fill = alt2_fill
                if isinstance(val, (int,float)):
                    cell.number_format = '#,##0.000'
                    cell.alignment = Alignment(horizontal='right')

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
