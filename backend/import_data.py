# import_data.py — parsing JSON/CSV (μεμονωμένο αρχείο, φάκελος, ή zip) που
# παρήγαγε εξωτερικό LLM (π.χ. Claude/Gemini free web UI, μέσω upload
# φωτογραφίας τιμολογίου/δελτίου) στο ίδιο "suggested" σχήμα που επιστρέφει
# το pdf_parser.parse_pdf, ώστε να περνάει από το ΙΔΙΟ preview/edit/submit
# flow του js/pdf-import.js — ένα παραστατικό τη φορά, ακόμα κι αν το αρχείο
# (ή ο φάκελος/zip) περιέχει πολλά.

import csv
import io
import json
import os
import re
import zipfile

IMPORT_EXTENSIONS = ('.json', '.csv')


def _norm_date(s):
    s = (s or '').strip()
    if not s:
        return ''
    m = re.match(r'^(\d{4})-(\d{2})-(\d{2})$', s)
    if m:
        y, mo, d = m.groups()
        return f'{d}/{mo}/{y}'
    return s


def _norm_num(v):
    if isinstance(v, (int, float)):
        return float(v)
    return float(str(v).strip().replace(',', '.'))


def _build_grammi(onoma, posotita, monada):
    onoma = (onoma or '').strip()
    monada = (monada or '').strip()
    if not onoma:
        raise ValueError('Γραμμή υλικού χωρίς όνομα')
    try:
        pos = _norm_num(posotita)
    except (ValueError, TypeError):
        raise ValueError(f'Μη έγκυρη ποσότητα για "{onoma}": {posotita!r}')
    return {'onoma': onoma, 'posotita': pos, 'monada': monada or 'Κιλ'}


def _build_suggested(header, grammes_raw):
    if not grammes_raw:
        raise ValueError('Δεν βρέθηκε καμία γραμμή υλικού')
    grammes = [_build_grammi(g.get('onoma'), g.get('posotita'), g.get('monada')) for g in grammes_raw]
    tipos = (header.get('tipos') or 'ΕΙΣΑΓΩΓΗ').strip().upper()
    if tipos not in ('ΕΙΣΑΓΩΓΗ', 'ΚΑΤΑΝΑΛΩΣΗ', 'ΕΠΙΣΤΡΟΦΗ'):
        tipos = 'ΕΙΣΑΓΩΓΗ'
    return {
        'imerominia': _norm_date(header.get('imerominia')),
        'tipos': tipos,
        'arithmos_parstatikos': (header.get('arithmos_parstatikou') or header.get('arithmos_parstatikos') or '').strip(),
        'adeia': (header.get('adeia') or '').strip(),
        'ekdousa_archi': (header.get('ekdousa_archi') or '').strip(),
        'promitheftis': (header.get('promitheftis') or '').strip(),
        'grammes': grammes,
    }


def parse_json_multi(text):
    """Επιστρέφει λίστα από 'suggested' dicts — ένα JSON object -> 1 στοιχείο,
    λίστα από objects -> ένα στοιχείο ανά object (πολλά παραστατικά)."""
    stripped = text.strip()
    # LLMs τυπικά τυλίγουν την απάντηση σε ```json ... ``` markdown fence.
    fence = re.match(r'^```(?:json)?\s*(.*?)\s*```$', stripped, re.DOTALL)
    if fence:
        stripped = fence.group(1)
    try:
        data = json.loads(stripped)
    except json.JSONDecodeError as e:
        raise ValueError(f'Μη έγκυρο JSON: {e}')
    if isinstance(data, dict):
        objs = [data]
    elif isinstance(data, list):
        objs = [d for d in data if isinstance(d, dict)]
    else:
        objs = []
    if not objs:
        raise ValueError('Το JSON πρέπει να είναι object, ή λίστα από objects (ένα ανά παραστατικό)')
    return [_build_suggested(o, o.get('grammes') or []) for o in objs]


def parse_csv_multi(text):
    """Ομαδοποιεί τις γραμμές ανά αριθμό παραστατικού — πολλά παραστατικά
    μπορούν να συνυπάρχουν στο ίδιο CSV (μία γραμμή ανά υλικό ανά παραστατικό)."""
    sample = text[:2048]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=',;')
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    rows = [row for row in reader if any((v or '').strip() for v in row.values())]
    if not rows:
        raise ValueError('Το CSV δεν έχει γραμμές δεδομένων')
    groups = {}
    for i, row in enumerate(rows):
        key = (row.get('arithmos_parstatikou') or row.get('arithmos_parstatikos') or '').strip()
        if not key:
            key = f'__row_{i}__'  # χωρίς αριθμό παραστατικού -> κάθε γραμμή δικό της παραστατικό
        groups.setdefault(key, []).append(row)
    return [_build_suggested(group_rows[0], group_rows) for group_rows in groups.values()]


def parse_import_items(text, fmt):
    if fmt == 'json':
        return parse_json_multi(text)
    if fmt == 'csv':
        return parse_csv_multi(text)
    raise ValueError(f'Άγνωστη μορφή αρχείου: {fmt}')


def _fmt_for(filename):
    return 'csv' if filename.lower().endswith('.csv') else 'json'


def _wrap_items(items, source):
    return [
        {'source': source, 'raw_text': json.dumps(it, ensure_ascii=False, indent=2), 'suggested': it}
        for it in items
    ]


def parse_single_file(path):
    fmt = _fmt_for(path)
    with open(path, 'r', encoding='utf-8-sig') as f:
        text = f.read()
    return _wrap_items(parse_import_items(text, fmt), os.path.basename(path))


def parse_folder(dirpath):
    """Μη-αναδρομικό: μόνο τα .json/.csv απευθείας μέσα στον φάκελο."""
    names = sorted(n for n in os.listdir(dirpath) if n.lower().endswith(IMPORT_EXTENSIONS))
    if not names:
        raise ValueError('Ο φάκελος δεν περιέχει αρχεία .json ή .csv')
    results, errors = [], []
    for name in names:
        try:
            results.extend(parse_single_file(os.path.join(dirpath, name)))
        except Exception as e:
            errors.append({'source': name, 'error': str(e)})
    return results, errors


def parse_zip(zippath):
    with zipfile.ZipFile(zippath) as zf:
        names = sorted(
            n for n in zf.namelist()
            if n.lower().endswith(IMPORT_EXTENSIONS) and not n.endswith('/')
        )
        if not names:
            raise ValueError('Το zip δεν περιέχει αρχεία .json ή .csv')
        results, errors = [], []
        for name in names:
            try:
                text = zf.read(name).decode('utf-8-sig')
                items = parse_import_items(text, _fmt_for(name))
                results.extend(_wrap_items(items, name))
            except Exception as e:
                errors.append({'source': name, 'error': str(e)})
    return results, errors
