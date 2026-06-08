"""
PDF parser για τιμολόγια εκρηκτικών NITROCHEM/EpsilonNet.
Πραγματική μορφή γραμμής (digital PDF):
  ΚΩΔΙΚΟΣ ΠΕΡΙΓΡΑΦΗ ΜΜ ΠΟΣΟΤΗΤΑ ΤΙΜΗ 0,00 ΑΞΙΑ
π.χ.: "40000000 ΠΕΤΡΑΜΜΩΝΙΤΗΣ (AN-FO) Κιλ 3.100,000 1,30 0,00 4.030,00"

Αρ. Παραστατικού = Σχετ. Παραστ. (π.χ. "ΔΙΧΝ - 19586")
Ημερομηνία       = η ημερομηνία δίπλα στο Σχετ. Παραστ. (π.χ. "5/1/2026")
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


def _normalize_date(d: str) -> str:
    """Μετατρέπει ημερομηνία σε DD/MM/YYYY."""
    for sep in ['-', '.']: d = d.replace(sep, '/')
    parts = d.split('/')
    if len(parts) == 3:
        return f"{parts[0].zfill(2)}/{parts[1].zfill(2)}/{parts[2]}"
    return d


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
        if re.search(r'Πιστωτικό|ΠΙΣΤΩΤΙΚΟ|Πιστ\.\s*Τιμ', line, re.IGNORECASE):
            suggested['tipos'] = 'ΕΠΙΣΤΡΟΦΗ'
            break

    # ── Σχετ. Παραστατικό → Αρ. Παραστατικού + Ημερομηνία ───────────────────
    # Μορφή: "ΔΙΧΝ - 19586 - 5/1/2026"  ή  "ΑΙΧΝ - 12345 - 12/3/2026"
    sxet_pat = re.compile(
        r'([Α-ΩA-Z0-9]{2,8}\s*[-–]\s*\d+)\s*[-–]\s*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{4})',
        re.IGNORECASE
    )
    for line in lines:
        m = sxet_pat.search(line)
        if m:
            suggested['arithmos_parstatikos'] = m.group(1).strip()
            suggested['imerominia'] = _normalize_date(m.group(2))
            break

    # Fallback: αν δεν βρέθηκε σχετ. παραστατικό, πάρε τον αριθμό τιμολογίου
    if not suggested['arithmos_parstatikos']:
        tim_pat = re.compile(
            r'(?:Τιμολόγιο|ΤΙΜΟΛΟΓΙΟ|Πιστωτικό|ΠΙΣΤΩΤΙΚΟ|Δελτίο|ΔΕΛΤΙΟ)\s+\w+\s+(\d+)',
            re.IGNORECASE
        )
        for line in lines:
            m = tim_pat.search(line)
            if m:
                suggested['arithmos_parstatikos'] = m.group(1)
                break

    # Fallback ημερομηνίας: πρώτη ημερομηνία στο κείμενο
    if not suggested['imerominia']:
        date_pat = re.compile(r'\b(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{4})\b')
        for line in lines:
            m = date_pat.search(line)
            if m:
                suggested['imerominia'] = _normalize_date(m.group(1))
                break

    # ── Άδεια + Εκδούσα Αρχή ─────────────────────────────────────────────────
    for i, line in enumerate(lines):
        stripped = line.strip()
        # Εκδούσα αρχή: "Δ.Α. ΧΑΛΚΙΔΙΚΗΣ" ή "Δ.Α. ΘΕΣΣΑΛΟΝΙΚΗΣ" κλπ
        if re.search(r'Δ\.Α\.\s+\w+', stripped, re.IGNORECASE):
            suggested['ekdousa_archi'] = stripped
            # Η άδεια είναι στην προηγούμενη γραμμή (standalone αριθμός)
            if i > 0:
                m = re.match(r'^\s*(\d{4,6})\s*$', lines[i-1])
                if m:
                    suggested['adeia'] = m.group(1)
            break
        # Fallback: "Αρ. Αδείας: 40923"
        m = re.search(r'Αρ\.\s*Αδείας[:\s]+(\d{4,6})', stripped, re.IGNORECASE)
        if m and not suggested['adeia']:
            suggested['adeia'] = m.group(1)

    # ── Προμηθευτής ───────────────────────────────────────────────────────────
    if suggested['tipos'] == 'ΕΠΙΣΤΡΟΦΗ':
        # Πιστωτικό: ο "προμηθευτής" είναι ο πελάτης (αυτός που επιστρέφει)
        # Βρίσκεται μετά τον κωδικό πελάτη (5ψήφιος αριθμός μόνος του σε γραμμή)
        for i, line in enumerate(lines):
            if re.match(r'^\d{5}$', line.strip()):
                if i + 1 < len(lines):
                    candidate = lines[i+1].strip()
                    if len(candidate) > 5 and re.search(r'[Α-Ω]{3}', candidate):
                        suggested['promitheftis'] = candidate[:60]
                        break
    else:
        # Αγορά: ο προμηθευτής είναι η εταιρεία εκρηκτικών
        known = ['NITROCHEM', 'DYNO NOBEL', 'ORICA', 'MAXAM', 'AUSTIN', 'ΕΛΒΙΕΜ', 'ELVIEM', 'ΕΠΕΚ', 'ΕΚΑΒΕ']
        for sup in known:
            for line in lines:
                if sup in line.upper():
                    if any(x in line for x in ['ΤΗΛ', 'FAX', 'email', '@', 'Α.Φ.Μ', 'ΛΟΦΙΣΚΟΣ']):
                        continue
                    idx = line.upper().find(sup)
                    clean = line[idx:].strip()[:40]
                    suggested['promitheftis'] = clean
                    break
            if suggested['promitheftis']:
                break

    # ── Υλικά — EpsilonNet/EpsilonDigital digital PDF ────────────────────────
    # Δύο μορφές:
    # Α) Αξία κολλητή με κωδικό: "1,30 4.030,0040000000 ΠΕΡΙΓΡΑΦΗ ΜΜ ΠΟΣΟΤΗΤΑ 0,00"
    # Β) Αξία με κενό:           "1,30 1.690,00 40000000 ΠΕΡΙΓΡΑΦΗ ΜΜ ΠΟΣΟΤΗΤΑ 0,00"
    item_pat = re.compile(
        r'^[\d,]+\s+'                               # Τιμή
        r'[\d\.,]+\s*'                              # Αξία (κολλητή ή με κενό)
        r'(\d{6,9})\s+'                             # Κωδικός
        r'(.+?)\s+'                                  # Περιγραφή
        r'(Κιλ|Τεμ|Μετρ|Κιλά|Τεμάχια|Μέτρα)\s+'   # Μονάδα
        r'([\d\.]+,\d+)\s+'                        # Ποσότητα
        r'0,0+\s*$',                                 # τέλος (0,00 ή 0,0)
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
