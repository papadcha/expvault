# import_data.py — parsing JSON/CSV αρχείων που παρήγαγε εξωτερικό LLM (π.χ.
# Claude/Gemini free web UI, μέσω upload φωτογραφίας τιμολογίου/δελτίου) στο
# ίδιο "suggested" σχήμα που επιστρέφει το exports_pdf.parse_pdf, ώστε να
# περνάει από το ΙΔΙΟ preview/edit/submit flow του js/pdf-import.js.

import csv
import io
import json
import re

REQUIRED_MONADES = {'Κιλ', 'Τεμ', 'Μετρ'}


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


def parse_json_text(text):
    stripped = text.strip()
    # LLMs τυπικά τυλίγουν την απάντηση σε ```json ... ``` markdown fence.
    fence = re.match(r'^```(?:json)?\s*(.*?)\s*```$', stripped, re.DOTALL)
    if fence:
        stripped = fence.group(1)
    try:
        data = json.loads(stripped)
    except json.JSONDecodeError as e:
        raise ValueError(f'Μη έγκυρο JSON: {e}')
    if isinstance(data, list):
        if not data:
            raise ValueError('Κενή λίστα JSON')
        data = data[0]  # ένα παραστατικό ανά εισαγωγή, βλ. σχόλιο πάνω
    if not isinstance(data, dict):
        raise ValueError('Το JSON πρέπει να είναι object (ή λίστα με ένα object)')
    grammes_raw = data.get('grammes') or []
    return _build_suggested(data, grammes_raw)


def parse_csv_text(text):
    sample = text[:2048]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=',;')
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    rows = [row for row in reader if any((v or '').strip() for v in row.values())]
    if not rows:
        raise ValueError('Το CSV δεν έχει γραμμές δεδομένων')
    header = rows[0]  # κοινά πεδία (ημερομηνία, παραστατικό, ...) επαναλαμβάνονται σε κάθε γραμμή
    return _build_suggested(header, rows)


def parse_import_text(text, fmt):
    if fmt == 'json':
        return parse_json_text(text)
    if fmt == 'csv':
        return parse_csv_text(text)
    raise ValueError(f'Άγνωστη μορφή αρχείου: {fmt}')
