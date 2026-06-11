"""
Εξαγωγή βιβλίου εκρηκτικών.
2 σελίδες landscape A4:
  Σελίδα 1: Αγορές / Επιστροφές
  Σελίδα 2: Καταναλώσεις
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

FONT_SETS = {
    'iosevka':    ['Iosevka-Regular.ttc', 'JetBrainsMono-Regular.ttf', 'LiberationMono-Regular.ttf'],
    'jetbrains':  ['JetBrainsMono-Regular.ttf', 'Iosevka-Regular.ttc', 'LiberationMono-Regular.ttf'],
    'liberation': ['LiberationMono-Regular.ttf', 'FreeMono.ttf'],
}
FONT_SETS_BOLD = {
    'iosevka':    ['Iosevka-Bold.ttc', 'JetBrainsMono-Bold.ttf', 'LiberationMono-Bold.ttf'],
    'jetbrains':  ['JetBrainsMono-Bold.ttf', 'Iosevka-Bold.ttc', 'LiberationMono-Bold.ttf'],
    'liberation': ['LiberationMono-Bold.ttf', 'FreeMonoBold.ttf'],
}

FONT_REGULAR = find_font(FONT_SETS['iosevka'])
FONT_BOLD    = find_font(FONT_SETS_BOLD['iosevka'])

def register_fonts(font_name='iosevka'):
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    reg  = find_font(FONT_SETS.get(font_name, FONT_SETS['iosevka']))
    bold = find_font(FONT_SETS_BOLD.get(font_name, FONT_SETS_BOLD['iosevka']))
    fname = f'Font_{font_name}'
    fbold = f'Font_{font_name}_Bold'
    try:
        pdfmetrics.getFont(fname)
    except:
        if reg:
            pdfmetrics.registerFont(TTFont(fname, reg))
            pdfmetrics.registerFont(TTFont(fbold, bold or reg))
    return fname, fbold

def fmt_date(s):
    if not s: return ''
    try:
        p = s.split('-')
        if len(p)==3 and len(p[0])==4: return f"{p[2]}/{p[1]}/{p[0]}"
    except: pass
    return s

def fmt_num(val):
    if val is None or val == 0: return ''
    return f"{val:,.2f}".replace(',','X').replace('.',',').replace('X','.')

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

    for k in kiniseis:
        yid   = k['yliko_id']
        tipos = k['tipos']
        parst = k.get('arithmos_parstatikos') or ''
        imer  = k['imerominia']
        adeia = k.get('arithmos_adeias') or ''
        ekd   = k.get('ekdousa_archi') or ''
        prom  = k.get('promitheftis_onoma') or ''
        par   = k.get('paratirishis') or ''

        if tipos == 'ΕΙΣΑΓΩΓΗ':
            key = (imer, parst, adeia, prom)
            if key not in agores:
                agores[key] = {
                    'type':'agora', 'aa':0,
                    'imerominia':imer, 'parstatiko':parst,
                    'adeia':adeia, 'ekdousa':ekd, 'promitheftis':prom,
                    'ylika':{}, 'paratirishis':par,
                    'auxon': k.get('auxon_arithmos', 0)
                }
            agores[key]['ylika'][yid] = agores[key]['ylika'].get(yid,0) + k['posotita']

        elif tipos in ('ΕΠΙΣΤΡΟΦΗ', 'ΕΞΑΓΩΓΗ') and parst:
            found = next((e for e in epistrofes
                         if e['parstatiko']==parst and e['imerominia']==imer), None)
            if not found:
                found = {
                    'type':'epistrofi', 'aa':None,
                    'imerominia':imer, 'parstatiko':parst,
                    'adeia':adeia, 'ekdousa':ekd, 'promitheftis':prom,
                    'ylika':{}, 'paratirishis':'ΕΠΙΣΤΡΟΦΗ',
                    'auxon': k.get('auxon_arithmos', 0),
                    'agora_ref': k.get('agora_ref') or ''
                }
                epistrofes.append(found)
            found['ylika'][yid] = found['ylika'].get(yid,0) + k['posotita']

        else:
            # ΚΑΤΑΝΑΛΩΣΗ — ομαδοποίηση ανά parstatiko (αν υπάρχει) ή imerominia
            kat_key = parst if parst else imer
            found = next((c for c in katanaliseis if c['kat_key']==kat_key), None)
            if not found:
                found = {
                    'type':'katanalosi', 'aa':None,
                    'imerominia':imer, 'parstatiko':parst or '',
                    'kat_key': kat_key,
                    'adeia':'', 'ekdousa':'', 'promitheftis':'',
                    'ylika':{}, 'paratirishis':par
                }
                katanaliseis.append(found)
            found['ylika'][yid] = found['ylika'].get(yid,0) + k['posotita']

    # Χτίζουμε τις γραμμές χρονολογικά:
    # Ταξινομούμε αγορές + επιστροφές μαζί κατά ημερομηνία
    # Κάθε επιστροφή εισάγεται αμέσως μετά την αγορά με την οποία χρονολογικά συσχετίζεται

    # Ταξινόμηση αγορών κατά auxon_arithmos (χρονολογική σειρά εισαγωγής)
    agora_list = sorted(agores.values(), key=lambda a: a['auxon'])

    # Για κάθε επιστροφή, βρες την αμέσως προηγούμενη αγορά χρονολογικά
    # που έχει κοινά υλικά
    epi_to_agora = {}  # index επιστροφής → index αγοράς
    for i, e in enumerate(epistrofes):
        best_agora_idx = None
        best_agora_date = None
        for j, agora in enumerate(agora_list):
            common = set(e['ylika'].keys()) & set(agora['ylika'].keys())
            # Η αγορά πρέπει να έχει auxon ΜΙΚΡΟΤΕΡΟ από την επιστροφή
            if common and agora['auxon'] < e['auxon']:
                if best_agora_date is None or agora['auxon'] > (agora_list[best_agora_idx]['auxon'] if best_agora_idx is not None else -1):
                    best_agora_date = agora['imerominia']
                    best_agora_idx = j
        if best_agora_idx is not None:
            epi_to_agora[i] = best_agora_idx

    # Χτίσε τις γραμμές: για κάθε αγορά, βάλε αμέσως μετά τις επιστροφές της
    rows = []
    epi_used = set()
    for j, agora in enumerate(agora_list):
        rows.append(agora)
        for i, e in enumerate(epistrofes):
            if i not in epi_used and epi_to_agora.get(i) == j:
                e['aa'] = 0
                rows.append(e)
                epi_used.add(i)

    # Επιστροφές που δεν συσχετίστηκαν — στο τέλος
    for i, e in enumerate(epistrofes):
        if i not in epi_used:
            e['aa'] = 0
            rows.append(e)

    # Δώσε Α/Α με τη σωστή σειρά τώρα που οι γραμμές είναι στη θέση τους
    for i, row in enumerate(rows, 1):
        row['aa'] = i

    # ── Κατανάλωση ανά parstatiko αγοράς ──────────────────────────────────────
    # kat_by_parst: κλειδί = parstatiko αγοράς
    kat_by_parst = {}

    # Χάρτης ημερομηνία → parstatiko αγοράς (για συσχέτιση ΚΑΤΑΝΑΛΩΣΗ χωρίς parstatiko)
    agora_by_date = {}
    for agora in agora_list:
        agora_by_date[agora['imerominia']] = agora['parstatiko']

    # Καταναλώσεις — συσχέτισε με αγορά βάσει ημερομηνίας αν δεν έχουν parstatiko
    for k in katanaliseis:
        key = k['parstatiko'] if k['parstatiko'] else agora_by_date.get(k['imerominia'], k['imerominia'])
        if key not in kat_by_parst:
            kat_by_parst[key] = {'ylika':{}, 'paratirishis':k['paratirishis'], 'imerominia':k['imerominia'], 'auto':False, 'auxon': k.get('auxon_arithmos', 0)}
        for yid, pos in k['ylika'].items():
            kat_by_parst[key]['ylika'][yid] = kat_by_parst[key]['ylika'].get(yid,0) + pos

    # Για κάθε αγορά χωρίς χειροκίνητη κατανάλωση → αυτόματος υπολογισμός
    # Επιστροφές ανά αγορά — χρήση agora_ref για ακριβή συσχέτιση
    epi_by_agora = {}  # parstatiko αγοράς → {yid: posotita}
    for e in epistrofes:
        # Προτεραιότητα στο agora_ref, fallback στον αλγόριθμο auxon
        agora_parst = e.get('agora_ref') or ''
        if not agora_parst:
            # Fallback: αμέσως προηγούμενη αγορά βάσει auxon
            best = None
            for agora in agora_list:
                common = set(e['ylika'].keys()) & set(agora['ylika'].keys())
                if common and agora['auxon'] < e['auxon']:
                    if best is None or agora['auxon'] > best['auxon']:
                        best = agora
            agora_parst = best['parstatiko'] if best else ''
        if agora_parst:
            if agora_parst not in epi_by_agora:
                epi_by_agora[agora_parst] = {}
            for yid, pos in e['ylika'].items():
                epi_by_agora[agora_parst][yid] = epi_by_agora[agora_parst].get(yid,0) + pos

    for agora in agora_list:
        ap = agora['parstatiko']
        epi = epi_by_agora.get(ap, {})
        if ap not in kat_by_parst:
            # Δεν υπάρχει χειροκίνητη → αυτόματος υπολογισμός: Αγορά − Επιστροφές
            auto_ylika = {}
            for yid, pos in agora['ylika'].items():
                katanalosi = pos - epi.get(yid, 0)
                if katanalosi > 0:
                    auto_ylika[yid] = katanalosi
            if auto_ylika:
                kat_by_parst[ap] = {
                    'ylika': auto_ylika,
                    'paratirishis': 'Αυτόματος υπολογισμός',
                    'imerominia': agora['imerominia'],
                    'auto': True
                }
        else:
            # Υπάρχει χειροκίνητη κατανάλωση
            # Αφαίρεσε επιστροφές ΜΟΝΟ αν η κατανάλωση καταχωρήθηκε ΠΡΙΝ την επιστροφή
            # (δηλαδή η κατανάλωση δεν έχει ήδη αφαιρέσει την επιστροφή)
            if epi:
                # Βρες min auxon κατανάλωσης vs min auxon επιστροφής
                kat_auxon = kat_by_parst[ap].get('auxon', 999999)
                # Συμπεριλάβε ΟΛΕΣ τις επιστροφές που συσχετίστηκαν με αυτή την αγορά
                # (είτε μέσω agora_ref είτε μέσω fallback auxon-αλγόριθμου)
                epi_auxons = [e.get('auxon', 0) for e in epistrofes
                              if (e.get('agora_ref') == ap) or
                                 (not e.get('agora_ref') and
                                  set(e['ylika'].keys()) & set(agora['ylika'].keys()) and
                                  e['auxon'] > agora['auxon'])]
                min_epi_auxon = min(epi_auxons) if epi_auxons else 999999
                # Αφαίρεσε μόνο αν η κατανάλωση έγινε ΠΡΙΝ την επιστροφή
                if kat_auxon < min_epi_auxon:
                    for yid, epi_pos in epi.items():
                        if yid in kat_by_parst[ap]['ylika']:
                            new_pos = kat_by_parst[ap]['ylika'][yid] - epi_pos
                            if new_pos > 0:
                                kat_by_parst[ap]['ylika'][yid] = new_pos
                            else:
                                del kat_by_parst[ap]['ylika'][yid]

    return rows, kat_by_parst


# ─── PDF ─────────────────────────────────────────────────────────────────────

def export_pdf(kiniseis: list, yliko_label: str, period_label: str, font: str = 'iosevka') -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, PageBreak
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

    F, FB = register_fonts(font)
    if not FONT_REGULAR:
        F, FB = 'Helvetica', 'Helvetica-Bold'

    ylika_order = get_ylika_order(kiniseis)
    rows, kat_by_parst = build_book_rows(kiniseis)
    n = len(ylika_order)

    pagesize  = landscape(A4)
    page_w_cm = (pagesize[0] - 1.4*cm) / cm

    TS = ParagraphStyle('t', fontSize=9,  fontName=FB, alignment=TA_CENTER, spaceAfter=2)
    SS = ParagraphStyle('s', fontSize=6,  fontName=F,  alignment=TA_CENTER, spaceAfter=4)
    HS = ParagraphStyle('h', fontSize=5.5,fontName=FB, alignment=TA_CENTER, leading=7, textColor=colors.HexColor('#1C252E'))
    CS = ParagraphStyle('c', fontSize=5.5,fontName=F,  alignment=TA_CENTER, leading=7, textColor=colors.HexColor('#1C252E'))
    RS = ParagraphStyle('r', fontSize=5.5,fontName=F,  alignment=TA_RIGHT,  leading=7, textColor=colors.HexColor('#1C252E'))
    NS = ParagraphStyle('n', fontSize=5.5,fontName=F,  alignment=TA_LEFT,   leading=7, textColor=colors.HexColor('#1C252E'))
    ES = ParagraphStyle('e', fontSize=5.5,fontName=FB, alignment=TA_CENTER, leading=7,
                        textColor=colors.HexColor('#c0392b'))
    ER = ParagraphStyle('er',fontSize=5.5,fontName=FB, alignment=TA_RIGHT,  leading=7,
                        textColor=colors.HexColor('#c0392b'))

    # Χρώματα — ανοιχτό επαγγελματικό γκρι, ίδια και στις 2 σελίδες
    HDR_BG = colors.HexColor('#CDD5DB')  # Τίτλος - λίγο σκουρότερο
    SUB_BG = colors.HexColor('#E4E9ED')
    HDR_FG = colors.HexColor('#1C252E')
    ALT_BG = colors.HexColor('#F4F6F8')
    GRID_C = colors.HexColor('#D1D8DE')

    def p(txt, s=None): return Paragraph(str(txt), s or CS)

    yliko_hdrs = [p(f"{on}\n({mo})", HS) for _, (on, mo) in ylika_order]

    # ── Σελίδα 1: Αγορές / Επιστροφές ───────────────────────────────────────
    L_FIXED = [0.6, 2.2, 2.2, 2.5]
    yw_l = max(0.8, (page_w_cm - sum(L_FIXED)) / n) if n else 1.5
    L_WIDTHS = [L_FIXED[0]*cm, L_FIXED[1]*cm] + [yw_l*cm]*n + \
               [L_FIXED[2]*cm, L_FIXED[3]*cm]

    l_title = [p('ΒΙΒΛΙΟ ΑΓΟΡΑΣ ΚΑΙ ΚΑΤΑΝΑΛΩΣΗΣ ΕΚΡΗΚΤΙΚΩΝ ΥΛΩΝ — ΑΓΟΡΕΣ / ΕΠΙΣΤΡΟΦΕΣ', HS)] + \
              [''] * (len(L_WIDTHS)-1)
    l_hdr   = [p('Α/Α',HS), p('Αρ.Άδ./\nΕκδ.Αρχή',HS)] + yliko_hdrs + \
              [p('Ημερ.Αγ./\nΑρ.Δελτ.',HS), p('Στοιχεία\nΠρομηθευτή',HS)]

    l_data  = [l_title, l_hdr]
    n_ylika_cols = len(ylika_order)
    num_l_start = 2  # col index αρχή αριθμών αριστερά
    num_l_end   = 2 + n_ylika_cols - 1

    l_style = [
        ('SPAN',         (0,0), (-1,0)),
        ('BACKGROUND',   (0,0), (-1,0), HDR_BG),
        ('BACKGROUND',   (0,1), (-1,1), SUB_BG),
        ('TEXTCOLOR',    (0,0), (-1,0), HDR_FG),        # μαύρο στο ανοιχτό
        ('TEXTCOLOR',    (0,1), (-1,1), colors.black),  # λευκό στο σκούρο
        ('ALIGN',        (0,0), (-1,-1), 'CENTER'),
        ('ALIGN',        (num_l_start,2), (num_l_end,-1), 'RIGHT'),
        ('VALIGN',       (0,0), (-1,-1), 'MIDDLE'),
        ('GRID',         (0,0), (-1,-1), 0.3, GRID_C),
        ('LINEBELOW',    (0,1), (-1,1), 1.0, colors.HexColor('#9AAAB5')),
        ('TOPPADDING',   (0,0), (-1,-1), 3),
        ('BOTTOMPADDING',(0,0), (-1,-1), 3),
        ('LEFTPADDING',  (0,0), (-1,-1), 3),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
    ]

    for ri, row in enumerate(rows, 2):
        is_epi = row['type'] == 'epistrofi'
        txt_s  = ES if is_epi else CS
        num_s  = ER if is_epi else RS
        adeia_ekd = row['adeia']
        if row.get('ekdousa'):
            adeia_ekd += f"\n{row['ekdousa']}"

        cells = [
            p(str(row['aa']) if row['aa'] else '', txt_s),
            p(adeia_ekd, txt_s),
        ]
        for yid, _ in ylika_order:
            v = row['ylika'].get(yid)
            cells.append(p(fmt_num(v) if v else '—', num_s))
        cells += [
            p(f"{fmt_date(row['imerominia'])}\n{row['parstatiko']}", txt_s),
            p(row['promitheftis'], txt_s),
        ]
        l_data.append(cells)

        if ri % 2 == 0 and not is_epi:
            l_style.append(('BACKGROUND', (0,ri), (-1,ri), ALT_BG))

    # Σταθερό ύψος γραμμών — ίδιο και στους 2 πίνακες για αντικρυστή εμφάνιση
    ROW_H = 22  # points — αρκετό για 2 γραμμές κειμένου
    HDR_H = 28  # header
    n_data_rows = len(l_data) - 2  # εκτός header
    row_heights = [HDR_H, HDR_H] + [ROW_H] * n_data_rows

    left_t = Table(l_data, colWidths=L_WIDTHS, repeatRows=2, rowHeights=row_heights)
    left_t.setStyle(TableStyle(l_style))

    # ── Σελίδα 2: Καταναλώσεις ───────────────────────────────────────────────
    R_FIXED = [1.5, 1.5, 1.8]
    yw_r = max(0.8, (page_w_cm - sum(R_FIXED)) / n) if n else 1.5
    R_WIDTHS = [R_FIXED[0]*cm, R_FIXED[1]*cm] + [yw_r*cm]*n + [R_FIXED[2]*cm]

    r_title = [p('ΒΙΒΛΙΟ ΑΓΟΡΑΣ ΚΑΙ ΚΑΤΑΝΑΛΩΣΗΣ ΕΚΡΗΚΤΙΚΩΝ ΥΛΩΝ — ΚΑΤΑΝΑΛΩΣΕΙΣ', HS)] + \
              [''] * (len(R_WIDTHS)-1)
    r_hdr   = [p('Ημερ.\nΕισαγ.\nΑποθ.',HS), p('Ημερ.\nΚατανάλ.',HS)] + \
              yliko_hdrs + [p('Παρατηρήσεις',HS)]

    r_data  = [r_title, r_hdr]
    r_style = [
        ('SPAN',         (0,0), (-1,0)),
        ('BACKGROUND',   (0,0), (-1,0), HDR_BG),
        ('BACKGROUND',   (0,1), (-1,1), SUB_BG),
        ('TEXTCOLOR',    (0,0), (-1,0), HDR_FG),
        ('TEXTCOLOR',    (0,1), (-1,1), colors.black),
        ('ALIGN',        (0,0), (-1,-1), 'CENTER'),
        ('ALIGN',        (2,2), (1+n_ylika_cols,-1), 'RIGHT'),
        ('VALIGN',       (0,0), (-1,-1), 'MIDDLE'),
        ('GRID',         (0,0), (-1,-1), 0.3, GRID_C),
        ('LINEBELOW',    (0,1), (-1,1), 1.0, colors.HexColor('#9AAAB5')),
        ('TOPPADDING',   (0,0), (-1,-1), 3),
        ('BOTTOMPADDING',(0,0), (-1,-1), 3),
        ('LEFTPADDING',  (0,0), (-1,-1), 3),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
    ]

    kat_used = set()
    for ri, row in enumerate(rows, 2):
        is_epi = row['type'] == 'epistrofi'
        ap     = row.get('parstatiko', '')
        imer   = row['imerominia']

        if not is_epi and ap not in kat_used:
            kat = kat_by_parst.get(ap, kat_by_parst.get(imer, {}))
            kat_used.add(ap)
            kat_imer = kat.get('imerominia', imer)
            cells = [p(fmt_date(kat_imer), CS), p(fmt_date(kat_imer), CS)]
            for yid, _ in ylika_order:
                v = kat.get('ylika', {}).get(yid)
                cells.append(p(fmt_num(v) if v else '—', RS))
            cells.append(p(kat.get('paratirishis',''), CS))
            if ri % 2 == 0:
                r_style.append(('BACKGROUND', (0,ri), (-1,ri), ALT_BG))
        else:
            cells = [p('',CS), p('',CS)] + [p('',CS)]*n + [p('',CS)]

        r_data.append(cells)

    right_t = Table(r_data, colWidths=R_WIDTHS, repeatRows=2, rowHeights=row_heights)
    right_t.setStyle(TableStyle(r_style))

    # ── Build ─────────────────────────────────────────────────────────────────
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=pagesize,
                            leftMargin=0.7*cm, rightMargin=0.7*cm,
                            topMargin=1.2*cm, bottomMargin=1.2*cm)
    doc.build([left_t, PageBreak(), right_t])
    return buf.getvalue()


# ─── Excel ────────────────────────────────────────────────────────────────────

def export_excel(kiniseis: list, yliko_label: str, period_label: str) -> bytes:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    ylika_order = get_ylika_order(kiniseis)
    rows, kat_by_parst = build_book_rows(kiniseis)
    n = len(ylika_order)

    wb = openpyxl.Workbook()

    # ── Sheet 1: Αγορές ───────────────────────────────────────────────────────
    ws1 = wb.active
    ws1.title = "Αγορές-Επιστροφές"
    total_l = 2 + n + 2  # Α/Α | Άδεια | υλικά | Ημερ/Δελτ | Προμηθ

    thin      = Side(style='thin', color="AABBD0")
    border    = Border(left=thin, right=thin, top=thin, bottom=thin)
    navy_fill = PatternFill("solid", fgColor="1A365D")
    lnav_fill = PatternFill("solid", fgColor="4A7FC1")
    hdr_font  = Font(bold=True, color="FFFFFF", size=9)
    alt_fill  = PatternFill("solid", fgColor="EEF2F7")
    red_fill  = PatternFill("solid", fgColor="FFF0F0")
    red_font  = Font(color="C53030", bold=True, size=9)

    ws1.merge_cells(f'A1:{get_column_letter(total_l)}1')
    ws1['A1'] = "ΒΙΒΛΙΟ ΑΓΟΡΑΣ ΚΑΙ ΚΑΤΑΝΑΛΩΣΗΣ ΕΚΡΗΚΤΙΚΩΝ ΥΛΩΝ — ΑΓΟΡΕΣ / ΕΠΙΣΤΡΟΦΕΣ"
    ws1['A1'].fill = navy_fill
    ws1['A1'].font = Font(bold=True, color="FFFFFF", size=11)
    ws1['A1'].alignment = Alignment(horizontal='center')

    hdrs   = ['Α/Α','Αρ.Άδ./Εκδ.Αρχή'] + \
             [f"{on}\n({mo})" for _,(on,mo) in ylika_order] + \
             ['Ημερ.Αγ./\nΑρ.Δελτ.','Στοιχεία\nΠρομηθευτή']
    widths = [5, 18] + [13]*n + [12, 18]

    for ci,(h,w) in enumerate(zip(hdrs,widths),1):
        cell = ws1.cell(row=2,column=ci,value=h)
        cell.fill = lnav_fill; cell.font = hdr_font
        cell.alignment = Alignment(horizontal='center',wrap_text=True)
        cell.border = border
        ws1.column_dimensions[get_column_letter(ci)].width = w
    ws1.row_dimensions[2].height = 32

    for ri, row in enumerate(rows,3):
        is_epi = row['type'] == 'epistrofi'
        fill   = red_fill if is_epi else (alt_fill if ri%2==0 else None)
        font   = red_font if is_epi else None
        adeia  = row['adeia'] + (f"\n{row['ekdousa']}" if row.get('ekdousa') else '')

        vals = [row['aa'] or '', adeia] + \
               [row['ylika'].get(yid) for yid,_ in ylika_order] + \
               [f"{fmt_date(row['imerominia'])}\n{row['parstatiko']}",
                row['promitheftis']]

        for ci,val in enumerate(vals,1):
            cell = ws1.cell(row=ri,column=ci,value=val)
            cell.border = border
            if fill: cell.fill = fill
            if font: cell.font = font
            if ci > 2 and ci <= 2+n and isinstance(val,(int,float)):
                cell.number_format = '#,##0.000'
                cell.alignment = Alignment(horizontal='right')
            else:
                cell.alignment = Alignment(horizontal='center',wrap_text=True)

    # ── Sheet 2: Καταναλώσεις ─────────────────────────────────────────────────
    ws2 = wb.create_sheet("Καταναλώσεις")
    total_r = 2 + n + 1
    grn_fill  = PatternFill("solid", fgColor="2D6A4F")
    lgrn_fill = PatternFill("solid", fgColor="52B788")
    alt2_fill = PatternFill("solid", fgColor="D8F3DC")

    ws2.merge_cells(f'A1:{get_column_letter(total_r)}1')
    ws2['A1'] = "ΒΙΒΛΙΟ ΑΓΟΡΑΣ ΚΑΙ ΚΑΤΑΝΑΛΩΣΗΣ ΕΚΡΗΚΤΙΚΩΝ ΥΛΩΝ — ΚΑΤΑΝΑΛΩΣΕΙΣ"
    ws2['A1'].fill = grn_fill
    ws2['A1'].font = Font(bold=True, color="FFFFFF", size=11)
    ws2['A1'].alignment = Alignment(horizontal='center')

    hdrs2  = ['Ημερ.\nΕισαγ.\nΑποθ.','Ημερ.\nΚατανάλ.'] + \
             [f"{on}\n({mo})" for _,(on,mo) in ylika_order] + ['Παρατηρήσεις']
    widths2 = [14,14] + [13]*n + [20]

    for ci,(h,w) in enumerate(zip(hdrs2,widths2),1):
        cell = ws2.cell(row=2,column=ci,value=h)
        cell.fill = lgrn_fill; cell.font = hdr_font
        cell.alignment = Alignment(horizontal='center',wrap_text=True)
        cell.border = border
        ws2.column_dimensions[get_column_letter(ci)].width = w
    ws2.row_dimensions[2].height = 32

    kat_used = set()
    for ri, row in enumerate(rows,3):
        is_epi = row['type'] == 'epistrofi'
        ap     = row.get('parstatiko', '')
        imer   = row['imerominia']
        if not is_epi and ap not in kat_used:
            kat = kat_by_parst.get(ap, kat_by_parst.get(imer, {}))
            kat_used.add(ap)
            kat_imer = kat.get('imerominia', imer)
            fill = alt2_fill if ri%2==0 else None
            vals = [fmt_date(kat_imer), fmt_date(kat_imer)] + \
                   [kat.get('ylika',{}).get(yid) for yid,_ in ylika_order] + \
                   [kat.get('paratirishis','')]
            for ci,val in enumerate(vals,1):
                cell = ws2.cell(row=ri,column=ci,value=val)
                cell.border = border
                if fill: cell.fill = fill
                if ci>2 and ci<=2+n and isinstance(val,(int,float)):
                    cell.number_format = '#,##0.000'
                    cell.alignment = Alignment(horizontal='right')
                else:
                    cell.alignment = Alignment(horizontal='center')

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ─── PDF ΥΠΟΛΟΓΙΣΜΟΥ ─────────────────────────────────────────────────────────

def export_ypologismos_pdf(parstatiko_agoras: str, senario: int, grammes: list) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

    register_fonts()
    F  = 'Sans'      if FONT_REGULAR else 'Helvetica'
    FB = 'Sans-Bold' if FONT_BOLD    else 'Helvetica-Bold'

    buf = __import__('io').BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)

    TS = ParagraphStyle('t', fontSize=13, fontName=FB, alignment=TA_CENTER, spaceAfter=4)
    SS = ParagraphStyle('s', fontSize=9,  fontName=F,  alignment=TA_CENTER, spaceAfter=12)
    HS = ParagraphStyle('h', fontSize=9,  fontName=FB, alignment=TA_CENTER, leading=11)
    CS = ParagraphStyle('c', fontSize=9,  fontName=F,  alignment=TA_CENTER, leading=11)
    AS = ParagraphStyle('a', fontSize=10, fontName=FB, alignment=TA_CENTER, leading=12,
                        textColor=colors.HexColor('#2d6a4f'))

    from datetime import datetime
    senario_txt = 'Σενάριο 1: Αγορά + Κατανάλωση → Επιστροφή' if senario==1 \
                  else 'Σενάριο 2: Αγορά + Επιστροφή → Κατανάλωση'

    story = [
        Paragraph("ΔΕΛΤΙΟ ΥΠΟΛΟΓΙΣΜΟΥ ΕΚΡΗΚΤΙΚΩΝ ΥΛΩΝ", TS),
        Paragraph(f"Παραστατικό Αγοράς: {parstatiko_agoras}  |  {senario_txt}", SS),
        Paragraph(f"Ημερομηνία Εκτύπωσης: {datetime.now().strftime('%d/%m/%Y %H:%M')}", SS),
    ]

    input_lbl  = 'Κατανάλωση' if senario==1 else 'Επιστροφή'
    result_lbl = 'Επιστροφή'  if senario==1 else 'Κατανάλωση'

    headers = ['Υλικό', 'Μονάδα', 'Αγορά', input_lbl, result_lbl]
    rows = [headers]
    for g in grammes:
        val = g['posotita_epistrofis'] if senario==1 else g['posotita_katanalosis']
        inp = g['posotita_katanalosis'] if senario==1 else g['posotita_epistrofis']
        rows.append([
            g['yliko_onoma'], g['monada'],
            f"{g['posotita_agoras']:,.3f}".replace(',','X').replace('.',',').replace('X','.'),
            f"{inp:,.3f}".replace(',','X').replace('.',',').replace('X','.'),
            f"{val:,.3f}".replace(',','X').replace('.',',').replace('X','.')
        ])

    col_w = [7*cm, 1.5*cm, 2.5*cm, 2.5*cm, 2.5*cm]
    t = Table(rows, colWidths=col_w)
    t.setStyle(TableStyle([
        ('BACKGROUND',   (0,0), (-1,0), colors.HexColor('#1a365d')),
        ('TEXTCOLOR',    (0,0), (-1,0), colors.white),
        ('FONTNAME',     (0,0), (-1,0), FB),
        ('FONTNAME',     (0,1), (-1,-1), F),
        ('FONTSIZE',     (0,0), (-1,-1), 9),
        ('ALIGN',        (0,0), (-1,-1), 'CENTER'),
        ('ALIGN',        (0,1), (0,-1), 'LEFT'),
        ('BACKGROUND',   (4,1), (4,-1), colors.HexColor('#e6f7ee')),
        ('FONTNAME',     (4,1), (4,-1), FB),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white, colors.HexColor('#f7f9fc')]),
        ('GRID',         (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e0')),
        ('TOPPADDING',   (0,0), (-1,-1), 5),
        ('BOTTOMPADDING',(0,0), (-1,-1), 5),
    ]))
    story.append(t)
    story.append(Spacer(1, 1*cm))
    story.append(Paragraph(f"Αποτέλεσμα {result_lbl} — Για χρήση κατά την έκδοση παραστατικού", AS))

    doc.build(story)
    return buf.getvalue()
