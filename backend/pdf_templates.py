"""
Εκμάθηση & αναγνώριση νέων τύπων παραστατικών (πρότυπα) από τον χρήστη.

Απομονωμένο module: δεν αγγίζει το pdf_parser.py ούτε επηρεάζει την υπάρχουσα
ροή εισαγωγής PDF. Χρησιμοποιείται μόνο όταν ο χρήστης ζητήσει ρητά να
"διδάξει" νέο τύπο παραστατικού, ή να δοκιμάσει τα ήδη αποθηκευμένα πρότυπα.

Πεδία που εξάγει κάθε πρότυπο (ίδια με pdf_parser.py):
  - imerominia          : ημερομηνία παραστατικού
  - arithmos_parstatikos: αριθμός παραστατικού
  - promitheftis        : προμηθευτής / επιχείρηση
  - adeia               : αριθμός άδειας
  - ekdousa_archi       : εκδούσα αρχή
  - tipos               : ΕΙΣΑΓΩΓΗ ή ΕΠΙΣΤΡΟΦΗ (βάσει keyword)
  - grammes             : λίστα υλικών {onoma, posotita, monada}

Ιδέα για item pattern: ο χρήστης επιλέγει σε μια παραδειγματική γραμμή υλικού
τα offsets για onoma, posotita και (προαιρετικά) monada.
Για τα header fields: ο χρήστης επιλέγει σε μια γραμμή την τιμή (value_range).
Για το tipos: ο χρήστης επιλέγει μια λέξη/φράση που χαρακτηρίζει το ΕΠΙΣΤΡΟΦΗ
(π.χ. "Πιστωτικό") — αν βρεθεί στο κείμενο → ΕΠΙΣΤΡΟΦΗ, αλλιώς → ΕΙΣΑΓΩΓΗ.
"""
import re
import sqlite3

from database import get_db

UNIT_WORDS = ['Κιλ', 'Κιλά', 'Τεμ', 'Τεμάχια', 'Μετρ', 'Μέτρα']
_UNIT_ALT = '(?:' + '|'.join(re.escape(u) for u in UNIT_WORDS) + ')'

TOKEN_RE = re.compile(r'\S+')


def ensure_table():
    with get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS pdf_templates (
                id                   INTEGER PRIMARY KEY AUTOINCREMENT,
                name                 TEXT NOT NULL,
                item_pattern         TEXT NOT NULL,
                parstatiko_pattern   TEXT,
                imerominia_pattern   TEXT,
                adeia_pattern        TEXT,
                ekdousa_archi_pattern TEXT,
                promitheftis_pattern  TEXT,
                tipos_keyword        TEXT,
                created_at           TEXT DEFAULT (datetime('now'))
            )
        ''')
        # Migration: προσθήκη νέων στηλών αν δεν υπάρχουν (backwards compat)
        existing = {r[1] for r in conn.execute("PRAGMA table_info(pdf_templates)").fetchall()}
        for col in ('adeia_pattern', 'ekdousa_archi_pattern', 'promitheftis_pattern', 'tipos_keyword'):
            if col not in existing:
                conn.execute(f'ALTER TABLE pdf_templates ADD COLUMN {col} TEXT')


def _tokens(line):
    return [(m.group(), m.start(), m.end()) for m in TOKEN_RE.finditer(line)]


def _classify_token(tok):
    """Γενικεύει ένα token που ΔΕΝ επέλεξε ο χρήστης, βάσει σχήματος."""
    if tok in UNIT_WORDS:
        return _UNIT_ALT
    if re.fullmatch(r'\d+', tok):
        return r'\d+'
    if re.fullmatch(r'[\d\.,]+', tok):
        return r'[\d\.,]+'
    return re.escape(tok)


def build_item_pattern(line, onoma_range, posotita_range, monada_range=None):
    """
    line           : κείμενο της παραδειγματικής γραμμής υλικού
    onoma_range    : (start, end) offsets του ονόματος υλικού
    posotita_range : (start, end) offsets της ποσότητας
    monada_range   : (start, end) offsets της μονάδας (προαιρετικό)

    Επιστρέφει regex (str) με named groups 'onoma', 'posotita' και
    προαιρετικά 'monada'.
    """
    toks = _tokens(line)
    if not toks:
        raise ValueError("Άδεια γραμμή παραδείγματος")

    def token_indices_for(rng):
        s, e = rng
        idxs = [i for i, (_, ts, te) in enumerate(toks) if ts < e and te > s]
        if not idxs:
            raise ValueError("Η επιλογή δεν αντιστοιχεί σε κανένα token")
        return idxs[0], idxs[-1]

    first_name_i, last_name_i = token_indices_for(onoma_range)
    pos_i, _ = token_indices_for(posotita_range)
    mon_range_i = None
    if monada_range:
        mon_i, _ = token_indices_for(monada_range)
        mon_range_i = mon_i

    hi = max(last_name_i, pos_i, mon_range_i if mon_range_i is not None else 0)

    parts = []
    i = 0
    while i <= hi:
        if i == pos_i:
            parts.append(r'(?P<posotita>[\d\.,]+)')
            i += 1
        elif mon_range_i is not None and i == mon_range_i:
            parts.append(r'(?P<monada>' + _UNIT_ALT + r')')
            i += 1
        elif first_name_i <= i <= last_name_i:
            parts.append(r'(?P<onoma>.+?)')
            i = last_name_i + 1
        else:
            parts.append(_classify_token(toks[i][0]))
            i += 1
    return r'\s+'.join(parts)


def _shape_pattern(value):
    """Γενικεύει την επιλεγμένη τιμή βάσει σχήματος.
    Για free-text: μετράει τα tokens του παραδείγματος ώστε να ταιριάζει ακριβώς τόσα
    (αντί για lazy quantifier που πιάνει μόνο 1 char)."""
    if re.fullmatch(r'\d{1,2}[/\-.]\d{1,2}[/\-.]\d{4}', value):
        return r'(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{4})'
    if re.fullmatch(r'\d+', value):
        return r'(\d+)'
    # Μέτρηση tokens στο παράδειγμα → ακριβής αντιστοίχιση πλήθους λέξεων
    n = len(value.split())
    if n <= 1:
        return r'(\S+)'
    return r'(\S+(?:\s+\S+){' + str(n - 1) + r'})'


def build_header_pattern(line, value_range, context_chars=25, next_line=None):
    """
    line        : γραμμή που περιέχει την τιμή
    value_range : (start, end) offsets της επιλεγμένης τιμής
    next_line   : η αμέσως επόμενη γραμμή (για anchor όταν η τιμή είναι μόνη της)
    Επιστρέφει regex (str) με 1 capture group.

    Αν υπάρχει αρκετό κείμενο αριστερά → αριστερός anchor.
    Αν η τιμή είναι στην αρχή της γραμμής → '^...$' ή multiline αν next_line διαθέσιμο.
    """
    start, end = value_range
    value = line[start:end]
    left_anchor = line[max(0, start - context_chars):start]

    if left_anchor.strip():
        # Κανονική περίπτωση: υπάρχει αριστερό κείμενο-άγκυρα
        return re.escape(left_anchor) + _shape_pattern(value)

    # Τιμή στην αρχή (ή κοντά): αγκύρωση ολόκληρης γραμμής
    right = line[end:].strip()
    if right:
        # Η τιμή ακολουθείται από άλλο κείμενο στην ίδια γραμμή
        right_anchor = line[end:end + context_chars]
        return _shape_pattern(value) + re.escape(right_anchor)

    # Η τιμή είναι μόνη στη γραμμή — αν υπάρχει επόμενη γραμμή χρησιμοποίησέ τη ως anchor
    if next_line and next_line.strip():
        next_anchor = re.escape(next_line.strip()[:context_chars])
        return _shape_pattern(value) + r'\n' + next_anchor

    # Fallback: anchored line match (γενικό — μπορεί να ταιριάξει λάθος γραμμή)
    return r'^' + _shape_pattern(value) + r'\s*$'


def save_template(name, item_pattern, parstatiko_pattern=None,
                  imerominia_pattern=None, adeia_pattern=None,
                  ekdousa_archi_pattern=None, promitheftis_pattern=None,
                  tipos_keyword=None):
    ensure_table()
    with get_db() as conn:
        cur = conn.execute(
            '''INSERT INTO pdf_templates
               (name, item_pattern, parstatiko_pattern, imerominia_pattern,
                adeia_pattern, ekdousa_archi_pattern, promitheftis_pattern, tipos_keyword)
               VALUES (?,?,?,?,?,?,?,?)''',
            (name, item_pattern, parstatiko_pattern, imerominia_pattern,
             adeia_pattern, ekdousa_archi_pattern, promitheftis_pattern, tipos_keyword)
        )
        return cur.lastrowid


def list_templates():
    ensure_table()
    with get_db() as conn:
        return [dict(r) for r in conn.execute(
            'SELECT * FROM pdf_templates ORDER BY created_at DESC').fetchall()]


def delete_template(template_id):
    ensure_table()
    with get_db() as conn:
        conn.execute('DELETE FROM pdf_templates WHERE id=?', (template_id,))


EXPORT_FIELDS = [
    'name', 'item_pattern', 'parstatiko_pattern', 'imerominia_pattern',
    'adeia_pattern', 'ekdousa_archi_pattern', 'promitheftis_pattern', 'tipos_keyword',
]


def export_to_file(path):
    import json
    ensure_table()
    with get_db() as conn:
        rows = [dict(r) for r in conn.execute('SELECT * FROM pdf_templates ORDER BY id').fetchall()]
    data = [{f: r.get(f) for f in EXPORT_FIELDS} for r in rows]
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump({'version': 1, 'templates': data}, fh, ensure_ascii=False, indent=2)
    return len(data)


def import_from_file(path):
    import json
    with open(path, encoding='utf-8') as fh:
        payload = json.load(fh)
    templates = payload.get('templates', [])
    ensure_table()
    imported = 0
    skipped = []
    with get_db() as conn:
        existing_names = {r[0] for r in conn.execute('SELECT name FROM pdf_templates').fetchall()}
        for t in templates:
            name = t.get('name')
            if name in existing_names:
                skipped.append(name)
                continue
            conn.execute(
                '''INSERT INTO pdf_templates
                   (name, item_pattern, parstatiko_pattern, imerominia_pattern,
                    adeia_pattern, ekdousa_archi_pattern, promitheftis_pattern, tipos_keyword)
                   VALUES (?,?,?,?,?,?,?,?)''',
                (name, t.get('item_pattern'), t.get('parstatiko_pattern'),
                 t.get('imerominia_pattern'), t.get('adeia_pattern'),
                 t.get('ekdousa_archi_pattern'), t.get('promitheftis_pattern'),
                 t.get('tipos_keyword'))
            )
            existing_names.add(name)
            imported += 1
    return {'imported': imported, 'skipped': skipped}


def _apply_item_pattern(pattern, raw_text):
    grammes = []
    try:
        compiled = re.compile(pattern)
    except re.error:
        return grammes
    for line in raw_text.split('\n'):
        m = compiled.search(line)
        if m:
            try:
                onoma    = m.group('onoma').strip()
                posotita = m.group('posotita').replace('.', '').replace(',', '.')
                try:
                    monada = m.group('monada').strip()
                except IndexError:
                    monada = ''
                grammes.append({'onoma': onoma, 'posotita': posotita, 'monada': monada})
            except (IndexError, re.error):
                continue
    return grammes


def _apply_header_pattern(pattern, raw_text):
    if not pattern:
        return ''
    try:
        if '\\n' in pattern:
            # Multiline pattern — ψάχνω στο ολόκληρο κείμενο
            m = re.search(pattern, raw_text)
            if m:
                return m.group(1).strip()
            return ''
        compiled = re.compile(pattern)
    except re.error:
        return ''
    for line in raw_text.split('\n'):
        m = compiled.search(line)
        if m:
            return m.group(1).strip()
    return ''


def _normalize_date(d):
    for sep in ['-', '.']: d = d.replace(sep, '/')
    parts = d.split('/')
    if len(parts) == 3:
        return f"{parts[0].zfill(2)}/{parts[1].zfill(2)}/{parts[2]}"
    return d


def preview_pattern(raw_text, item_pattern, parstatiko_pattern=None,
                    imerominia_pattern=None, adeia_pattern=None,
                    ekdousa_archi_pattern=None, promitheftis_pattern=None,
                    tipos_keyword=None):
    """Δοκιμάζει patterns πριν αποθήκευση — για προεπισκόπηση."""
    imerominia_raw = _apply_header_pattern(imerominia_pattern, raw_text)
    tipos = 'ΕΙΣΑΓΩΓΗ'
    if tipos_keyword and tipos_keyword.strip():
        if re.search(re.escape(tipos_keyword.strip()), raw_text, re.IGNORECASE):
            tipos = 'ΕΠΙΣΤΡΟΦΗ'
    return {
        'grammes':              _apply_item_pattern(item_pattern, raw_text),
        'arithmos_parstatikos': _apply_header_pattern(parstatiko_pattern, raw_text),
        'imerominia':           _normalize_date(imerominia_raw) if imerominia_raw else '',
        'adeia':                _apply_header_pattern(adeia_pattern, raw_text),
        'ekdousa_archi':        _apply_header_pattern(ekdousa_archi_pattern, raw_text),
        'promitheftis':         _apply_header_pattern(promitheftis_pattern, raw_text),
        'tipos':                tipos,
    }


def try_parse_with_templates(raw_text):
    """Δοκιμάζει όλα τα αποθηκευμένα πρότυπα· επιστρέφει το πρώτο που βρίσκει υλικά."""
    for tpl in list_templates():
        grammes = _apply_item_pattern(tpl['item_pattern'], raw_text)
        if grammes:
            tipos = 'ΕΙΣΑΓΩΓΗ'
            kw = tpl.get('tipos_keyword') or ''
            if kw.strip() and re.search(re.escape(kw.strip()), raw_text, re.IGNORECASE):
                tipos = 'ΕΠΙΣΤΡΟΦΗ'
            imerominia_raw = _apply_header_pattern(tpl.get('imerominia_pattern'), raw_text)
            return {
                'imerominia':           _normalize_date(imerominia_raw) if imerominia_raw else '',
                'arithmos_parstatikos': _apply_header_pattern(tpl.get('parstatiko_pattern'), raw_text),
                'promitheftis':         _apply_header_pattern(tpl.get('promitheftis_pattern'), raw_text),
                'adeia':                _apply_header_pattern(tpl.get('adeia_pattern'), raw_text),
                'ekdousa_archi':        _apply_header_pattern(tpl.get('ekdousa_archi_pattern'), raw_text),
                'tipos':                tipos,
                'grammes':              grammes,
                'template_used':        tpl['name'],
            }
    return None
