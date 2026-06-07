"""
PDF parser για τιμολόγια εκρηκτικών NITROCHEM/EpsilonNet.
Πραγματική μορφή γραμμής:
  ΤΙΜΗ ΑΞΙΑ ΚΩΔΙΚΟΣ ΠΕΡΙΓΡΑΦΗ ΜΜ ΠΟΣΟΤΗΤΑ 0,00
π.χ.: "1,30 2.600,00 40000000 ΠΕΤΡΑΜΜΩΝΙΤΗΣ (AN-FO) Κιλ 2.000,000 0,00"
"""
import re

try:
    import pypdf
    PYPDF_OK = True
except ImportError:
    PYPDF_OK = False


def extract_text_from_pdf(filepath: str) -> str:
    if not PYPDF_OK:
        raise RuntimeError("Η βιβλιοθήκη pypdf δεν είναι εγκατεστημένη.")
    reader = pypdf.PdfReader(filepath)
    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        pages.append(f"--- Σελίδα {i+1} ---\n{text}")
    return "\n".join(pages)


def parse_pdf(filepath: str) -> dict:
    raw_text = extract_text_from_pdf(filepath)
    suggested = {
        'imerominia': '',
        'arithmos_parstatikos': '',
        'promitheftis': '',
        'adeia': '',
        'ekdousa_archi': '',
        'tipos': 'ΕΙΣΑΓΩΓΗ',  # default
        'grammes': []
    }

    lines = raw_text.split('\n')

    # ── Τύπος εγγράφου ────────────────────────────────────────────────────────
    for line in lines:
        if re.search(r'Πιστωτικό|ΠΙΣΤΩΤΙΚΟ|Επιστροφή|ΕΠΙΣΤΡΟΦΗ|Πιστ\.\s*Τιμ', line, re.IGNORECASE):
            suggested['tipos'] = 'ΕΠΙΣΤΡΟΦΗ'
            break

    lines = raw_text.split('\n')

    # ── Ημερομηνία ────────────────────────────────────────────────────────────
    date_pat = re.compile(r'\b(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{4})\b')
    for line in lines:
        m = date_pat.search(line)
        if m:
            d = m.group(1)
            for sep in ['-', '.']: d = d.replace(sep, '/')
            parts = d.split('/')
            if len(parts) == 3:
                suggested['imerominia'] = f"{parts[0].zfill(2)}/{parts[1].zfill(2)}/{parts[2]}"
            break

    # ── Αριθμός παραστατικού ─────────────────────────────────────────────────
    tim_pat = re.compile(r'(?:Τιμολόγιο|ΤΙΜΟΛΟΓΙΟ|Πιστωτικό|ΠΙΣΤΩΤΙΚΟ|Δελτίο|ΔΕΛΤΙΟ)\s+\w+\s+(\d+)', re.IGNORECASE)
    for line in lines:
        m = tim_pat.search(line)
        if m:
            suggested['arithmos_parstatikos'] = m.group(1)
            break

    # ── Άδεια + Εκδούσα Αρχή ─────────────────────────────────────────────────
    # Το αρ. άδειας είναι στη γραμμή πριν το "Δ.Α. ..."
    # Το "Δ.Α. ΧΑΛΚΙΔΙΚΗΣ" είναι η εκδούσα αρχή
    for i, line in enumerate(lines):
        if re.search(r'^Δ\.Α\.\s+\w+', line.strip(), re.IGNORECASE):
            suggested['ekdousa_archi'] = line.strip()
            if i > 0:
                m = re.match(r'^\s*(\d{4,6})\s*$', lines[i-1])
                if m:
                    suggested['adeia'] = m.group(1)
            break

    # ── Προμηθευτής / Αποστολέας ─────────────────────────────────────────────
    if suggested['tipos'] == 'ΕΞΑΓΩΓΗ':
        # Επιστροφή: ο "προμηθευτής" είναι ο πελάτης — βρίσκεται μετά τον κωδικό πελάτη
        for i, line in enumerate(lines):
            if re.match(r'^\d{5}\s*$', line.strip()):  # Κωδικός πελάτη (5ψήφιος)
                # Το όνομα είναι στην αμέσως επόμενη γραμμή
                if i + 1 < len(lines):
                    candidate = lines[i+1].strip()
                    if len(candidate) > 5 and re.search(r'[Α-Ω]{3}', candidate):
                        suggested['promitheftis'] = candidate[:50]
                        break
    else:
        # Αγορά: ο προμηθευτής είναι η εταιρεία εκρηκτικών
        known = ['NITROCHEM', 'DYNO NOBEL', 'ORICA', 'MAXAM', 'AUSTIN', 'ΕΛΒΙΕΜ', 'ELVIEM', 'ΕΠΕΚ', 'ΕΚΑΒΕ']
        for sup in known:
            for line in lines:
                if sup in line.upper():
                    if any(x in line for x in ['ΤΗΛ', 'FAX', 'email', '@', 'Α.Φ.Μ']):
                        continue
                    idx = line.upper().find(sup)
                    clean = line[idx:].strip()[:40]
                    suggested['promitheftis'] = clean
                    break
            if suggested['promitheftis']:
                break

    # ── Υλικά — Πραγματική μορφή EpsilonNet ──────────────────────────────────
    # "ΤΙΜΗ ΑΞΙΑ ΚΩΔΙΚΟΣ ΠΕΡΙΓΡΑΦΗ ΜΜ ΠΟΣΟΤΗΤΑ 0,00"
    item_pat = re.compile(
        r'^[\d,]+\s+'                               # Τιμή
        r'[\d\.,]+\s*'                              # Αξία (κολλητή με κωδικό)
        r'(\d{6,9})\s+'                             # Κωδικός
        r'(.+?)\s+'                                 # Περιγραφή
        r'(Κιλ|Τεμ|Μετρ|Κιλά|Τεμάχια|Μέτρα)\s+'   # Μονάδα
        r'([\d\.]+,\d+)\s+'                         # Ποσότητα
        r'0,00\s*$',                                # 0,00 στο τέλος
        re.IGNORECASE
    )

    monada_map = {
        'κιλ': 'Κιλ', 'κιλά': 'Κιλ',
        'τεμ': 'Τεμ', 'τεμάχια': 'Τεμ',
        'μετρ': 'Μετρ', 'μέτρα': 'Μετρ'
    }

    for line in lines:
        m = item_pat.match(line.strip())
        if m:
            onoma    = m.group(2).strip()
            monada   = monada_map.get(m.group(3).lower(), m.group(3))
            posotita = m.group(4).replace('.', '').replace(',', '.')
            suggested['grammes'].append({
                'onoma': onoma,
                'posotita': posotita,
                'monada': monada
            })

    return {'raw_text': raw_text, 'suggested': suggested}
