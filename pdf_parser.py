"""
Γενικός PDF parser για τιμολόγια/δελτία εκρηκτικών.
Εξάγει κείμενο, προσπαθεί να αναγνωρίσει βασικά πεδία,
και επιστρέφει τόσο τα αναγνωρισμένα όσο και το πλήρες κείμενο
ώστε ο χρήστης να συμπληρώσει χειροκίνητα.
"""
import re
from datetime import datetime

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
    """
    Επιστρέφει:
    {
      'raw_text': str,           # πλήρες κείμενο για εμφάνιση στον χρήστη
      'suggested': {             # τιμές που βρέθηκαν αυτόματα (μπορεί να είναι '')
        'imerominia': str,
        'arithmos_parstatikos': str,
        'promitheftis': str,
        'adeia': str,
        'grammes': [             # κάθε γραμμή υλικού που αναγνωρίστηκε
          {'onoma': str, 'posotita': str, 'monada': str}
        ]
      }
    }
    """
    raw_text = extract_text_from_pdf(filepath)
    suggested = {
        'imerominia': '',
        'arithmos_parstatikos': '',
        'promitheftis': '',
        'adeia': '',
        'grammes': []
    }

    lines = raw_text.split('\n')

    # Ημερομηνία: ΗΗ/ΜΜ/ΕΕΕΕ ή ΗΗ-ΜΜ-ΕΕΕΕ
    date_pattern = re.compile(r'\b(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{4})\b')
    for line in lines:
        m = date_pattern.search(line)
        if m and not suggested['imerominia']:
            raw_date = m.group(1)
            # Κανονικοποίηση σε ΗΗ/ΜΜ/ΕΕΕΕ
            for sep in ['-', '.']:
                raw_date = raw_date.replace(sep, '/')
            parts = raw_date.split('/')
            if len(parts) == 3:
                suggested['imerominia'] = f"{parts[0].zfill(2)}/{parts[1].zfill(2)}/{parts[2]}"
            break

    # Αριθμός παραστατικού: αριθμός μετά από ΤΙΜΟΛΟΓ/ΠΑΡΑΣΤ/ΔΕΛΤ/ΑΡ.
    parst_pattern = re.compile(
        r'(?:ΤΙΜΟΛΟΓ|ΠΑΡΑΣΤ|ΔΕΛΤ|ΔΕΛ\.|ΑΡ\.?\s*(?:ΤΙΜ\.?|ΠΑΡ\.?|ΔΕΛ\.?))[\s\.:]*(\d+)',
        re.IGNORECASE
    )
    for line in lines:
        m = parst_pattern.search(line)
        if m:
            suggested['arithmos_parstatikos'] = m.group(1)
            break

    # Αν δεν βρέθηκε, ψάξε για μεγάλο αριθμό σε γραμμή με "No" ή "Νο"
    if not suggested['arithmos_parstatikos']:
        no_pattern = re.compile(r'\bN[oο°]\.?\s*:?\s*(\d{3,})', re.IGNORECASE)
        for line in lines:
            m = no_pattern.search(line)
            if m:
                suggested['arithmos_parstatikos'] = m.group(1)
                break

    # Αριθμός άδειας: ΑΔΕΙΑ + αριθμός >=4 ψηφίων
    adeia_pattern = re.compile(r'ΑΔΕ[ΙΎ]Α[Σ]?[\s\.:]*(\d{4,})', re.IGNORECASE)
    for line in lines:
        m = adeia_pattern.search(line)
        if m:
            suggested['adeia'] = m.group(1)
            break

    # Προμηθευτής: γνωστές εταιρείες εκρηκτικών
    known_suppliers = [
        'NITROCHEM', 'DYNO NOBEL', 'ORICA', 'MAXAM', 'AUSTIN', 'SOLARIS',
        'EΛΒΙΕΜ', 'ΕΛΒΙΕΜ', 'ELVIEM', 'ΕΠΕΚ', 'EPEK', 'ΕΚΑΒΕ', 'EKAVE'
    ]
    full_upper = raw_text.upper()
    for sup in known_suppliers:
        if sup.upper() in full_upper:
            # Βρες το πλήρες όνομα (μέχρι το τέλος της γραμμής)
            for line in lines:
                if sup.upper() in line.upper():
                    # Καθάρισε και κράτα μέχρι 50 χαρακτήρες
                    clean = line.strip()[:50]
                    suggested['promitheftis'] = clean
                    break
            break

    # Υλικά: ψάξε για γνωστά patterns ποσότητας (αριθμός + μονάδα)
    quantity_pattern = re.compile(
        r'^(.{5,60}?)\s+([\d\.,]+)\s*(kg|kgr|κιλ|χιλγρ|τεμ|τεμάχ|μέτρ|μετρ|m|τμχ)\b',
        re.IGNORECASE
    )
    for line in lines:
        m = quantity_pattern.search(line)
        if m:
            onoma_candidate = m.group(1).strip()
            # Φιλτράρισμα: απόρριψη γραμμών που μοιάζουν με header/σύνολο
            skip_words = ['ΣΥΝΟΛ', 'TOTAL', 'ΑΞΙΑ', 'ΦΠΑ', 'ΠΟΣΟ', 'ΤΙΜΗ', 'ΑΡΙΘΜ']
            if any(w in onoma_candidate.upper() for w in skip_words):
                continue
            posotita_str = m.group(2).replace('.', '').replace(',', '.')
            monada = m.group(3).lower()
            # Κανονικοποίηση μονάδας
            monada_map = {
                'kg': 'Κιλ', 'kgr': 'Κιλ', 'κιλ': 'Κιλ', 'χιλγρ': 'Κιλ',
                'τεμ': 'Τεμ', 'τεμάχ': 'Τεμ', 'τμχ': 'Τεμ',
                'μέτρ': 'Μετρ', 'μετρ': 'Μετρ', 'm': 'Μετρ'
            }
            monada_clean = monada_map.get(monada, monada.capitalize())
            suggested['grammes'].append({
                'onoma': onoma_candidate,
                'posotita': posotita_str,
                'monada': monada_clean
            })

    return {
        'raw_text': raw_text,
        'suggested': suggested
    }
