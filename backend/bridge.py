"""
bridge.py — Python IPC bridge για ExpVault
Διαβάζει JSON commands από stdin, εκτελεί, γράφει JSON response στο stdout.
"""
import sys
import json
import os
import traceback

# Ορισμός path βάσης δεδομένων δίπλα στο bridge.py
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'expvault.db')

import database
database.DB_NAME = DB_PATH
database.init_db()

import pdf_parser
import exports

def handle(cmd, payload):
    # ── ΥΛΙΚΑ ────────────────────────────────────────────────────────────────
    if cmd == 'get_ylika':
        return database.get_all_ylika()

    if cmd == 'add_yliko':
        database.add_yliko(payload['onoma'], payload.get('diatomi_mm'),
                           payload['monada_metrisis'], payload.get('paratirishis'))
        return {'ok': True}

    if cmd == 'update_yliko':
        database.update_yliko(payload['id'], payload['onoma'], payload.get('diatomi_mm'),
                              payload['monada_metrisis'], payload.get('paratirishis'))
        return {'ok': True}

    if cmd == 'delete_yliko':
        database.delete_yliko(payload['id'])
        return {'ok': True}

    # ── ΠΡΟΜΗΘΕΥΤΕΣ ──────────────────────────────────────────────────────────
    if cmd == 'get_promitheftes':
        return database.get_all_promitheftes()

    if cmd == 'add_promitheftis':
        database.add_promitheftis(payload['onoma'])
        return {'ok': True}

    if cmd == 'update_promitheftis':
        database.update_promitheftis(payload['id'], payload['onoma'])
        return {'ok': True}

    if cmd == 'delete_promitheftis':
        database.delete_promitheftis(payload['id'])
        return {'ok': True}

    # ── ΑΔΕΙΕΣ ───────────────────────────────────────────────────────────────
    if cmd == 'get_adeies':
        return database.get_all_adeies()

    if cmd == 'add_adeia':
        database.add_adeia(payload['arithmos_adeias'], payload.get('perigrafi'))
        return {'ok': True}

    if cmd == 'update_adeia':
        database.update_adeia(payload['id'], payload['arithmos_adeias'], payload.get('perigrafi'))
        return {'ok': True}

    if cmd == 'delete_adeia':
        database.delete_adeia(payload['id'])
        return {'ok': True}

    # ── ΚΙΝΗΣΕΙΣ ─────────────────────────────────────────────────────────────
    if cmd == 'get_kiniseis':
        return database.get_kiniseis(
            yliko_id=payload.get('yliko_id'),
            apo=payload.get('apo'),
            eos=payload.get('eos'),
            tipos=payload.get('tipos')
        )

    if cmd == 'add_kinisi':
        database.add_kinisi(
            payload['imerominia'], payload['tipos'], payload['yliko_id'],
            float(payload['posotita']), payload.get('arithmos_parstatikos'),
            payload.get('adeia_id'), payload.get('promitheftis_id'),
            payload.get('paratirishis'), payload.get('ypografi')
        )
        return {'ok': True}

    if cmd == 'update_kinisi':
        database.update_kinisi(
            payload['id'], payload['imerominia'], payload['tipos'],
            payload['yliko_id'], float(payload['posotita']),
            payload.get('arithmos_parstatikos'), payload.get('adeia_id'),
            payload.get('promitheftis_id'), payload.get('paratirishis'),
            payload.get('ypografi')
        )
        return {'ok': True}

    if cmd == 'delete_kinisi':
        database.delete_kinisi(payload['id'])
        return {'ok': True}

    # ── ΑΠΟΘΕΜΑΤΑ ────────────────────────────────────────────────────────────
    if cmd == 'get_apothemates':
        return database.get_apothemates()

    # ── ΕΛΕΓΧΟΣ ΠΑΡΑΣΤΑΤΙΚΟΥ ─────────────────────────────────────────────────
    if cmd == 'check_parstatiko':
        return database.check_parstatiko_exists(payload.get('arithmos_parstatikos'))

    # ── ΕΛΕΓΧΟΣ ΕΚΚΡΕΜΟΤΗΤΑΣ ─────────────────────────────────────────────────
    if cmd == 'check_ekkremotita':
        return database.check_ekkremotita(
            payload.get('yliko_id'),
            payload.get('imerominia'),
            payload.get('parstatiko')
        )

    # ── PDF PARSER ────────────────────────────────────────────────────────────
    if cmd == 'parse_pdf':
        result = pdf_parser.parse_pdf(payload['path'])
        return {'ok': True, **result}

    # ── EXPORT PDF ────────────────────────────────────────────────────────────
    if cmd == 'export_pdf':
        kiniseis = database.get_kiniseis(
            yliko_id=payload.get('yliko_id'),
            apo=payload.get('apo'),
            eos=payload.get('eos')
        )
        data = exports.export_pdf(kiniseis, payload.get('yliko_label','Όλα'), payload.get('period_label','—'))
        out_path = payload['out_path']
        with open(out_path, 'wb') as f:
            f.write(data)
        return {'ok': True, 'path': out_path}

    # ── EXPORT EXCEL ──────────────────────────────────────────────────────────
    if cmd == 'export_excel':
        kiniseis = database.get_kiniseis(
            yliko_id=payload.get('yliko_id'),
            apo=payload.get('apo'),
            eos=payload.get('eos')
        )
        data = exports.export_excel(kiniseis, payload.get('yliko_label','Όλα'), payload.get('period_label','—'))
        out_path = payload['out_path']
        with open(out_path, 'wb') as f:
            f.write(data)
        return {'ok': True, 'path': out_path}

    return {'error': f'Άγνωστη εντολή: {cmd}'}


def main():
    # Flush αμέσως — χωρίς buffering
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)

    # Σήμα ότι το bridge είναι έτοιμο
    print(json.dumps({'ready': True}), flush=True)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
            req_id = msg.get('id')
            cmd    = msg.get('cmd')
            payload = msg.get('payload', {})
            result = handle(cmd, payload)
            print(json.dumps({'id': req_id, 'result': result}), flush=True)
        except Exception as e:
            print(json.dumps({
                'id': msg.get('id') if 'msg' in dir() else None,
                'error': str(e),
                'trace': traceback.format_exc()
            }), flush=True)

if __name__ == '__main__':
    main()
