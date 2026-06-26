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
import importlib
import exports
import backup

def handle(cmd, payload):
    # ── ΥΛΙΚΑ ────────────────────────────────────────────────────────────────
    if cmd == 'get_ylika':
        return database.get_all_ylika()

    if cmd == 'add_yliko':
        database.add_yliko(payload['onoma'], payload.get('diatomi_mm'),
                           payload['monada_metrisis'], payload.get('paratirishis'), payload.get('export_group'), payload.get('export_subgroup'), payload.get('nomiki_katigoria'))
        return {'ok': True}

    if cmd == 'update_yliko':
        database.update_yliko(payload['id'], payload['onoma'], payload.get('diatomi_mm'),
                              payload['monada_metrisis'], payload.get('paratirishis'), payload.get('export_group'), payload.get('export_subgroup'), payload.get('nomiki_katigoria'))
        return {'ok': True}

    if cmd == 'delete_yliko':
        database.delete_yliko(payload['id'])
        return {'ok': True}

    # ── ΠΡΟΜΗΘΕΥΤΕΣ ──────────────────────────────────────────────────────────
    if cmd == 'get_promitheftes':
        return database.get_all_promitheftes()

    if cmd == 'add_promitheftis':
        database.add_promitheftis(payload['onoma'], payload.get('syntomografia'))
        return {'ok': True}

    if cmd == 'update_promitheftis':
        database.update_promitheftis(payload['id'], payload['onoma'], payload.get('syntomografia'))
        return {'ok': True}

    if cmd == 'delete_promitheftis':
        database.delete_promitheftis(payload['id'])
        return {'ok': True}

    # ── ΑΔΕΙΕΣ ───────────────────────────────────────────────────────────────
    if cmd == 'get_adeies':
        return database.get_all_adeies()

    if cmd == 'add_adeia':
        new_id = database.add_adeia(payload['arithmos_adeias'], payload.get('perigrafi'),
                                    payload.get('syntomografia_ekdousas'),
                                    payload.get('imerominia_ekdosis'), payload.get('imerominia_lixis'))
        return {'ok': True, 'id': new_id}

    if cmd == 'update_adeia':
        database.update_adeia(payload['id'], payload['arithmos_adeias'], payload.get('perigrafi'),
                              payload.get('syntomografia_ekdousas'),
                              payload.get('imerominia_ekdosis'), payload.get('imerominia_lixis'))
        return {'ok': True}

    if cmd == 'get_adeia_ylika':
        return database.get_adeia_ylika(payload['adeia_id'])

    if cmd == 'get_adeia_yliko_remaining':
        return database.get_adeia_yliko_remaining(payload['adeia_id'], payload['yliko_id']) or {}

    if cmd == 'set_adeia_yliko':
        database.set_adeia_yliko(payload['adeia_id'], payload['yliko_id'], float(payload['egekrimeni_posotita']))
        return {'ok': True}

    if cmd == 'delete_adeia_yliko':
        database.delete_adeia_yliko(payload['id'])
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
            payload.get('paratirishis'), payload.get('ypografi'),
            agora_ref=payload.get('agora_ref')
        )
        return {'ok': True}

    if cmd == 'update_kinisi':
        database.update_kinisi(
            payload['id'], payload['imerominia'], payload['tipos'],
            payload['yliko_id'], float(payload['posotita']),
            payload.get('arithmos_parstatikos'), payload.get('adeia_id'),
            payload.get('promitheftis_id'), payload.get('paratirishis'),
            payload.get('ypografi'), agora_ref=payload.get('agora_ref')
        )
        return {'ok': True}

    if cmd == 'update_agora_ref':
        database.update_agora_ref(payload['arithmos_parstatikos'], payload['agora_ref'])
        return {'ok': True}
        return {'ok': True}
    if cmd == 'delete_kinisi':
        database.delete_kinisi(payload['id'])
        return {'ok': True}

    if cmd == 'batch_update_parstatiko':
        n = database.batch_update_parstatiko(
            payload['old_parst'],
            payload.get('new_parst'),
            payload.get('new_date'),
            new_adeia_id=payload.get('new_adeia_id'),
            new_promitheftis_id=payload.get('new_promitheftis_id'),
            new_agora_ref=payload.get('new_agora_ref'),
        )
        return {'ok': True, 'updated': n}

    # ── ΑΠΟΘΕΜΑΤΑ ────────────────────────────────────────────────────────────
    if cmd == 'get_apothemates':
        return database.get_apothemates()

    # ── ΥΠΟΛΟΓΙΣΜΟΣ ──────────────────────────────────────────────────────────
    if cmd == 'save_ypologismos':
        yid = database.save_ypologismos(
            payload['parstatiko_agoras'], payload['imerominia_agoras'],
            payload['senario'], payload['grammes']
        )
        return {'ok': True, 'id': yid}

    if cmd == 'get_ypologismos':
        return database.get_ypologismos(payload['parstatiko_agoras']) or {}

    if cmd == 'delete_ypologismos':
        database.delete_ypologismos(payload['parstatiko_agoras'])
        return {'ok': True}

    if cmd == 'compare_ypologismos':
        return database.compare_ypologismos_with_vivlio(payload['parstatiko_agoras'])

    # ── ΕΛΕΓΧΟΣ ΠΑΡΑΣΤΑΤΙΚΟΥ ─────────────────────────────────────────────────
    if cmd == 'check_parstatiko':
        return database.check_parstatiko_exists(payload.get('arithmos_parstatikos'))

    if cmd == 'get_agores_with_pending_epistrofes':
        return database.get_agores_with_pending_epistrofes()

    if cmd == 'assign_epistrofi_parstatiko':
        n = database.assign_epistrofi_parstatiko(
            payload['agora_ref'], payload['new_parstatiko'], payload.get('new_date')
        )
        return {'ok': True, 'updated': n}

    if cmd == 'get_epistrofes_without_parstatiko':
        return database.get_epistrofes_without_parstatiko(payload['agora_ref'])

    if cmd == 'get_kiniseis_by_parstatiko_yliko':
        return database.get_kiniseis_by_parstatiko_yliko(
            payload['arithmos_parstatikos'], payload['yliko_id']
        )

    if cmd == 'delete_kiniseis_by_parstatiko':
        database.delete_kiniseis_by_parstatiko(payload.get('arithmos_parstatikos'))
        return {'ok': True}

    if cmd == 'delete_parstatiko_with_related':
        database.delete_parstatiko_with_related(
            payload['arithmos_parstatikos'],
            include_agora_ref=payload.get('include_agora_ref', True)
        )
        return {'ok': True}

    # ── ΕΛΕΓΧΟΣ ΕΚΚΡΕΜΟΤΗΤΑΣ ─────────────────────────────────────────────────
    if cmd == 'check_ekkremotita':
        return database.check_ekkremotita(
            payload.get('yliko_id'),
            payload.get('imerominia'),
            payload.get('parstatiko')
        )

    if cmd == 'get_last_eisagogi_parstatiko':
        return database.get_last_eisagogi_parstatiko()

    # ── PDF PARSER ────────────────────────────────────────────────────────────
    if cmd == 'parse_pdf':
        result = pdf_parser.parse_pdf(payload['path'])
        return {'ok': True, **result}

    # ── PDF TEMPLATES ─────────────────────────────────────────────────────────
    if cmd == 'extract_pdf_text':
        raw_text = pdf_parser.extract_text_from_pdf(payload['path'])
        return {'ok': True, 'raw_text': raw_text}

    if cmd == 'list_pdf_templates':
        import pdf_templates
        return {'ok': True, 'templates': pdf_templates.list_templates()}

    if cmd == 'delete_pdf_template':
        import pdf_templates
        pdf_templates.delete_template(payload['id'])
        return {'ok': True}

    if cmd == 'preview_pdf_template':
        import pdf_templates
        result = pdf_templates.preview_pattern(
            payload['raw_text'],
            payload['item_pattern'],
            payload.get('parstatiko_pattern'),
            payload.get('imerominia_pattern'),
            payload.get('adeia_pattern'),
            payload.get('ekdousa_archi_pattern'),
            payload.get('promitheftis_pattern'),
            payload.get('tipos_keyword'),
        )
        return {'ok': True, **result}

    if cmd == 'save_pdf_template':
        import pdf_templates
        tid = pdf_templates.save_template(
            payload['name'],
            payload['item_pattern'],
            payload.get('parstatiko_pattern'),
            payload.get('imerominia_pattern'),
            payload.get('adeia_pattern'),
            payload.get('ekdousa_archi_pattern'),
            payload.get('promitheftis_pattern'),
            payload.get('tipos_keyword'),
        )
        return {'ok': True, 'id': tid}

    if cmd == 'build_and_preview_pdf_template':
        import pdf_templates
        patterns = {}
        errors = []

        # Item pattern (onoma + posotita + optional monada)
        try:
            isel = payload['item_selection']
            patterns['item_pattern'] = pdf_templates.build_item_pattern(
                isel['line'],
                tuple(isel['onoma_range']),
                tuple(isel['posotita_range']),
                tuple(isel['monada_range']) if isel.get('monada_range') else None,
            )
        except Exception as e:
            errors.append(f'Γραμμή υλικού: {e}')
            patterns['item_pattern'] = ''

        # Header patterns
        for field, pat_key in [
            ('parstatiko',    'parstatiko_pattern'),
            ('imerominia',    'imerominia_pattern'),
            ('adeia',         'adeia_pattern'),
            ('ekdousa_archi', 'ekdousa_archi_pattern'),
            ('promitheftis',  'promitheftis_pattern'),
        ]:
            sel = payload.get(f'{field}_selection')
            if sel:
                try:
                    patterns[pat_key] = pdf_templates.build_header_pattern(
                        sel['line'], tuple(sel['value_range'])
                    )
                except Exception as e:
                    errors.append(f'{field}: {e}')
                    patterns[pat_key] = None
            else:
                patterns[pat_key] = None

        patterns['tipos_keyword'] = payload.get('tipos_keyword') or None

        preview = {}
        if patterns.get('item_pattern') and payload.get('raw_text'):
            preview = pdf_templates.preview_pattern(payload['raw_text'], **patterns)

        return {'ok': True, 'patterns': patterns, 'preview': preview, 'errors': errors}

    if cmd == 'export_ypologismos_pdf':
        pdf = exports.export_ypologismos_pdf(
            payload['parstatiko_agoras'], payload['senario'], payload['grammes']
        )
        with open(payload['out_path'], 'wb') as f: f.write(pdf)
        return {'ok': True}

    # ── EXPORT PDF ────────────────────────────────────────────────────────────
    if cmd in ('export_pdf', 'export_excel', 'export_docx'):
        importlib.reload(exports)
    if cmd == 'export_pdf':
        kiniseis = database.get_kiniseis(
            yliko_id=payload.get('yliko_id'),
            apo=payload.get('apo'),
            eos=payload.get('eos')
        )
        _mod = importlib.import_module('exports'); importlib.reload(_mod)
        try:
            data = _mod.export_pdf(kiniseis, payload.get('yliko_label','Όλα'), payload.get('period_label','—'), payload.get('font','iosevka'), payload.get('nonel_mode','detail'))
        except Exception as _e:
            import sys, traceback
            traceback.print_exc(file=sys.stderr)
            raise
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
        data = exports.export_excel(kiniseis, payload.get('yliko_label','Όλα'), payload.get('period_label','—'), payload.get('nonel_mode','detail'))
        out_path = payload['out_path']
        with open(out_path, 'wb') as f:
            f.write(data)
        return {'ok': True, 'path': out_path}

    # ── EXPORT DOCX ───────────────────────────────────────────────────────────
    if cmd == 'export_docx':
        kiniseis = database.get_kiniseis(
            yliko_id=payload.get('yliko_id'),
            apo=payload.get('apo'),
            eos=payload.get('eos')
        )
        _mod = importlib.import_module('exports'); importlib.reload(_mod)
        data = _mod.export_docx(kiniseis, payload.get('yliko_label','Όλα'), payload.get('period_label','—'), payload.get('nonel_mode','detail'))
        out_path = payload['out_path']
        with open(out_path, 'wb') as f:
            f.write(data)
        return {'ok': True, 'path': out_path}

    # ── EXPORT LISTA AGORES ───────────────────────────────────────────────────
    if cmd == 'export_lista_agores':
        kiniseis = database.get_kiniseis(
            apo=payload.get('apo'),
            eos=payload.get('eos'),
            tipos='ΕΙΣΑΓΩΓΗ'
        )
        data = exports.export_lista_agores(
            kiniseis,
            payload.get('apo_label', ''),
            payload.get('eos_label', '')
        )
        out_path = payload['out_path']
        with open(out_path, 'wb') as f:
            f.write(data)
        return {'ok': True, 'path': out_path}

    # ── ΔΕΛΤΙΟ ΔΡΑΣΤΗΡΙΟΤΗΤΑΣ ─────────────────────────────────────────────────
    if cmd in ('export_deltio_drastiriotitas_excel', 'export_deltio_drastiriotitas_pdf'):
        importlib.reload(exports)
        kiniseis = database.get_kiniseis(
            apo=payload.get('apo'),
            eos=payload.get('eos')
        )
        fn = exports.export_deltio_drastiriotitas_excel if cmd.endswith('excel') else exports.export_deltio_drastiriotitas_pdf
        data = fn(kiniseis, payload.get('apo_label', ''), payload.get('eos_label', ''))
        out_path = payload['out_path']
        with open(out_path, 'wb') as f:
            f.write(data)
        return {'ok': True, 'path': out_path}

    # ── BACKUP ───────────────────────────────────────────────────────────────
    if cmd == 'get_backup_config':
        return backup.get_config()

    if cmd == 'save_backup_config':
        return backup.save_config(payload['paths'], payload.get('max_keep', 30))

    if cmd == 'run_backup':
        return backup.run_all_backups()

    if cmd == 'list_backups':
        return backup.list_backups(payload['folder'])

    if cmd == 'restore_backup':
        return backup.restore_backup(payload['path'])

    if cmd == 'list_rclone_remotes':
        return backup.list_rclone_remotes()

    if cmd == 'list_remotes_detail':
        return backup.list_remotes_detail()

    if cmd == 'delete_remote':
        return backup.delete_remote(payload['name'])

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
