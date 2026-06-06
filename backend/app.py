import os
import tempfile
from flask import Flask, render_template, request, jsonify, send_file
import io

from database import (
    init_db,
    get_all_ylika, add_yliko, update_yliko, delete_yliko,
    get_all_promitheftes, add_promitheftis, update_promitheftis, delete_promitheftis,
    get_all_adeies, add_adeia, update_adeia, delete_adeia,
    get_kiniseis, add_kinisi, update_kinisi, delete_kinisi,
    get_apothemates
)
from pdf_parser import parse_pdf, PYPDF_OK
from exports import export_pdf, export_excel

app = Flask(__name__)
init_db()

# ─── ΚΥΡΙΑ ΣΕΛΙΔΑ ────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')

# ─── ΥΛΙΚΑ ───────────────────────────────────────────────────────────────────

@app.route('/api/ylika', methods=['GET'])
def api_get_ylika():
    return jsonify(get_all_ylika())

@app.route('/api/ylika', methods=['POST'])
def api_add_yliko():
    d = request.json
    try:
        add_yliko(d['onoma'], d.get('diatomi_mm'), d['monada_metrisis'], d.get('paratirishis'))
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400

@app.route('/api/ylika/<int:id>', methods=['PUT'])
def api_update_yliko(id):
    d = request.json
    try:
        update_yliko(id, d['onoma'], d.get('diatomi_mm'), d['monada_metrisis'], d.get('paratirishis'))
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400

@app.route('/api/ylika/<int:id>', methods=['DELETE'])
def api_delete_yliko(id):
    try:
        delete_yliko(id)
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400

# ─── ΠΡΟΜΗΘΕΥΤΕΣ ─────────────────────────────────────────────────────────────

@app.route('/api/promitheftes', methods=['GET'])
def api_get_prom():
    return jsonify(get_all_promitheftes())

@app.route('/api/promitheftes', methods=['POST'])
def api_add_prom():
    d = request.json
    try:
        add_promitheftis(d['onoma'])
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400

@app.route('/api/promitheftes/<int:id>', methods=['PUT'])
def api_update_prom(id):
    d = request.json
    try:
        update_promitheftis(id, d['onoma'])
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400

@app.route('/api/promitheftes/<int:id>', methods=['DELETE'])
def api_delete_prom(id):
    try:
        delete_promitheftis(id)
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400

# ─── ΑΔΕΙΕΣ ──────────────────────────────────────────────────────────────────

@app.route('/api/adeies', methods=['GET'])
def api_get_adeies():
    return jsonify(get_all_adeies())

@app.route('/api/adeies', methods=['POST'])
def api_add_adeia():
    d = request.json
    try:
        add_adeia(d['arithmos_adeias'], d.get('perigrafi'))
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400

@app.route('/api/adeies/<int:id>', methods=['PUT'])
def api_update_adeia(id):
    d = request.json
    try:
        update_adeia(id, d['arithmos_adeias'], d.get('perigrafi'))
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400

@app.route('/api/adeies/<int:id>', methods=['DELETE'])
def api_delete_adeia(id):
    try:
        delete_adeia(id)
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400

# ─── ΚΙΝΗΣΕΙΣ ────────────────────────────────────────────────────────────────

@app.route('/api/kiniseis', methods=['GET'])
def api_get_kiniseis():
    return jsonify(get_kiniseis(
        yliko_id=request.args.get('yliko_id', type=int),
        apo=request.args.get('apo'),
        eos=request.args.get('eos'),
        tipos=request.args.get('tipos')
    ))

@app.route('/api/kiniseis', methods=['POST'])
def api_add_kinisi():
    d = request.json
    try:
        add_kinisi(
            d['imerominia'], d['tipos'], d['yliko_id'], float(d['posotita']),
            d.get('arithmos_parstatikos'), d.get('adeia_id'), d.get('promitheftis_id'),
            d.get('paratirishis'), d.get('ypografi')
        )
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400

@app.route('/api/kiniseis/<int:id>', methods=['PUT'])
def api_update_kinisi(id):
    d = request.json
    try:
        update_kinisi(
            id, d['imerominia'], d['tipos'], d['yliko_id'], float(d['posotita']),
            d.get('arithmos_parstatikos'), d.get('adeia_id'), d.get('promitheftis_id'),
            d.get('paratirishis'), d.get('ypografi')
        )
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400

@app.route('/api/kiniseis/<int:id>', methods=['DELETE'])
def api_delete_kinisi(id):
    try:
        delete_kinisi(id)
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400

# ─── ΑΠΟΘΕΜΑΤΑ ───────────────────────────────────────────────────────────────

@app.route('/api/apothemates', methods=['GET'])
def api_apothemates():
    return jsonify(get_apothemates())

# ─── PDF PARSER ───────────────────────────────────────────────────────────────

@app.route('/api/parse-pdf', methods=['POST'])
def api_parse_pdf():
    if not PYPDF_OK:
        return jsonify({'ok': False, 'error': 'Η βιβλιοθήκη pypdf δεν είναι εγκατεστημένη.'}), 500
    if 'file' not in request.files:
        return jsonify({'ok': False, 'error': 'Δεν βρέθηκε αρχείο.'}), 400
    f = request.files['file']
    if not f.filename.lower().endswith('.pdf'):
        return jsonify({'ok': False, 'error': 'Το αρχείο πρέπει να είναι PDF.'}), 400
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
        f.save(tmp.name)
        try:
            result = parse_pdf(tmp.name)
            return jsonify({'ok': True, **result})
        except Exception as e:
            return jsonify({'ok': False, 'error': str(e)}), 500
        finally:
            os.unlink(tmp.name)

# ─── ΕΞΑΓΩΓΗ ─────────────────────────────────────────────────────────────────

@app.route('/api/export/pdf')
def api_export_pdf():
    yliko_id = request.args.get('yliko_id', type=int)
    apo = request.args.get('apo', '')
    eos = request.args.get('eos', '')
    kiniseis = get_kiniseis(yliko_id=yliko_id, apo=apo, eos=eos)

    yliko_label = "Όλα τα υλικά"
    if yliko_id:
        ylika = {y['id']: y for y in get_all_ylika()}
        if yliko_id in ylika:
            y = ylika[yliko_id]
            yliko_label = y['onoma'] + (f" ({y['diatomi_mm']}mm)" if y['diatomi_mm'] else '')

    period_label = f"{apo or '—'} έως {eos or '—'}"
    data = export_pdf(kiniseis, yliko_label, period_label)
    return send_file(io.BytesIO(data), mimetype='application/pdf',
                     as_attachment=True, download_name='vivlio_ekrktikon.pdf')

@app.route('/api/export/excel')
def api_export_excel():
    yliko_id = request.args.get('yliko_id', type=int)
    apo = request.args.get('apo', '')
    eos = request.args.get('eos', '')
    kiniseis = get_kiniseis(yliko_id=yliko_id, apo=apo, eos=eos)

    yliko_label = "Όλα τα υλικά"
    if yliko_id:
        ylika = {y['id']: y for y in get_all_ylika()}
        if yliko_id in ylika:
            y = ylika[yliko_id]
            yliko_label = y['onoma'] + (f" ({y['diatomi_mm']}mm)" if y['diatomi_mm'] else '')

    period_label = f"{apo or '—'} έως {eos or '—'}"
    data = export_excel(kiniseis, yliko_label, period_label)
    return send_file(io.BytesIO(data),
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                     as_attachment=True, download_name='vivlio_ekrktikon.xlsx')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
