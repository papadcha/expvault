import { escapeHtml, py, _lock, showConfirm } from './utils.js';

// ── PDF TEMPLATES ────────────────────────────────────────────────────────────

let _tplRawText = '';
let _tplSels = {};
let _tplBuiltPatterns = null;

const TPL_HEADER_FIELDS = ['parstatiko','imerominia','adeia','ekdousa_archi','promitheftis'];
const TPL_ALL_FIELDS = ['onoma','posotita','monada',...TPL_HEADER_FIELDS,'tipos_keyword'];

export function tplReset() {
  _tplSels = {};
  _tplBuiltPatterns = null;
  TPL_ALL_FIELDS.forEach(f => {
    const el = document.getElementById('tpl-cap-' + f);
    if (el) el.innerHTML = '';
  });
  document.getElementById('tpl-preview-section').style.display = 'none';
}

export async function tplLoadPdf() {
  if (!window.api) { alert('Χρησιμοποιήστε την εφαρμογή μέσω Electron'); return; }
  const path = await window.api.openFile();
  if (!path) return;
  const statusEl = document.getElementById('tpl-pdf-status');
  statusEl.textContent = '⏳ Ανάγνωση…';
  try {
    const res = await py('extract_pdf_text', { path });
    _tplRawText = res.raw_text;
    document.getElementById('tpl-raw-text').value = _tplRawText;
    document.getElementById('tpl-capture-section').style.display = 'block';
    statusEl.textContent = '✅ ' + path.split(/[\\/]/).pop();
    tplReset();
  } catch(e) {
    statusEl.textContent = '❌ ' + e.message;
  }
}

export function tplCapture(field) {
  const ta = document.getElementById('tpl-raw-text');
  const start = ta.selectionStart;
  const end   = ta.selectionEnd;
  if (start === end) { alert('Επέλεξε πρώτα κείμενο στο πλαίσιο PDF.'); return; }

  const fullText = ta.value;
  const lineStart = fullText.lastIndexOf('\n', start - 1) + 1;
  const lineEndIdx = fullText.indexOf('\n', end);
  const line = fullText.slice(lineStart, lineEndIdx === -1 ? undefined : lineEndIdx);
  const selStart = start - lineStart;
  const selEnd   = end   - lineStart;
  const preview  = fullText.slice(start, end);

  _tplSels[field] = { line, sel_start: selStart, sel_end: selEnd, preview };

  const badge = document.getElementById('tpl-cap-' + field);
  if (badge) {
    badge.innerHTML = `<span style="background:#e8f4ea;color:#1a7a4a;border:1px solid #c3e6cb;
      border-radius:4px;padding:2px 8px;display:inline-block;max-width:220px;
      overflow:hidden;text-overflow:ellipsis;white-space:nowrap;cursor:default;"
      title="${escapeHtml(preview)}">✓ "${escapeHtml(preview)}"</span>`;
  }

  // Έλεγχος: onoma/posotita/monada πρέπει στην ίδια γραμμή
  if (['onoma','posotita','monada'].includes(field)) {
    const defined = ['onoma','posotita','monada'].filter(f => _tplSels[f]);
    const lines = new Set(defined.map(f => _tplSels[f].line));
    if (lines.size > 1 && badge) {
      badge.innerHTML += '<span style="color:var(--danger);font-size:11px;margin-left:6px;">⚠ διαφ. γραμμή!</span>';
    }
  }
}

export async function tplPreview(evt) {
  if (!_tplSels.onoma || !_tplSels.posotita) {
    alert('Υποχρεωτικά πεδία: Όνομα Υλικού και Ποσότητα.');
    return;
  }
  // Έλεγχος ότι item fields είναι στην ίδια γραμμή
  const itemDefined = ['onoma','posotita','monada'].filter(f => _tplSels[f]);
  const itemLines = new Set(itemDefined.map(f => _tplSels[f].line));
  if (itemLines.size > 1) {
    alert('Τα πεδία Όνομα, Ποσότητα, Μονάδα πρέπει να είναι στην ίδια γραμμή.');
    return;
  }

  const _unlock = _lock(evt?.target);
  try {
    const payload = {
      raw_text: _tplRawText,
      item_selection: {
        line:          _tplSels.onoma.line,
        onoma_range:   [_tplSels.onoma.sel_start,    _tplSels.onoma.sel_end],
        posotita_range:[_tplSels.posotita.sel_start, _tplSels.posotita.sel_end],
        monada_range:  _tplSels.monada ? [_tplSels.monada.sel_start, _tplSels.monada.sel_end] : null,
      },
    };
    for (const f of TPL_HEADER_FIELDS) {
      if (_tplSels[f]) {
        payload[f + '_selection'] = {
          line:        _tplSels[f].line,
          value_range: [_tplSels[f].sel_start, _tplSels[f].sel_end],
        };
      }
    }
    if (_tplSels.tipos_keyword) payload.tipos_keyword = _tplSels.tipos_keyword.preview;

    const res = await py('build_and_preview_pdf_template', payload);
    _tplBuiltPatterns = res.patterns;
    _tplRenderPreview(res.preview, res.errors || []);
    document.getElementById('tpl-preview-section').style.display = 'block';
    document.getElementById('tpl-preview-section').scrollIntoView({ behavior: 'smooth', block: 'start' });
  } catch(e) {
    alert('Σφάλμα: ' + e.message);
  } finally { _unlock(); }
}

function _tplRenderPreview(preview, errors) {
  const alertEl = document.getElementById('tpl-preview-alert');
  const bodyEl  = document.getElementById('tpl-preview-body');

  alertEl.innerHTML = errors.length
    ? errors.map(e => `<div class="alert alert-error">⚠ ${escapeHtml(e)}</div>`).join('')
    : '';

  if (!preview || Object.keys(preview).length === 0) {
    bodyEl.innerHTML = '<p style="color:var(--muted);">Δεν επιστράφηκαν αποτελέσματα.</p>';
    return;
  }

  const tiposBadge = preview.tipos === 'ΕΠΙΣΤΡΟΦΗ'
    ? '<span class="badge badge-out">🔄 ΕΠΙΣΤΡΟΦΗ</span>'
    : '<span class="badge badge-in">📥 ΕΙΣΑΓΩΓΗ</span>';

  const grammes = (preview.grammes || []);
  const grammeRows = grammes.map(g =>
    `<tr><td>${escapeHtml(g.onoma)||'—'}</td>
         <td class="mono text-right">${escapeHtml(g.posotita)||'—'}</td>
         <td>${escapeHtml(g.monada)||'—'}</td></tr>`
  ).join('') || '<tr><td colspan="3" style="color:var(--muted);text-align:center;padding:12px;">Δεν βρέθηκαν υλικά</td></tr>';

  bodyEl.innerHTML = `
    <div class="form-row cols-3" style="margin-bottom:14px;">
      <div><label>Τύπος</label><div style="margin-top:4px;">${tiposBadge}</div></div>
      <div><label>Αρ. Παραστατικού</label><div class="mono" style="font-size:13px;margin-top:4px;">${escapeHtml(preview.arithmos_parstatikos)||'—'}</div></div>
      <div><label>Ημερομηνία</label><div class="mono" style="font-size:13px;margin-top:4px;">${escapeHtml(preview.imerominia)||'—'}</div></div>
    </div>
    <div class="form-row cols-3" style="margin-bottom:16px;">
      <div><label>Άδεια</label><div class="mono" style="font-size:13px;margin-top:4px;">${escapeHtml(preview.adeia)||'—'}</div></div>
      <div><label>Εκδούσα Αρχή</label><div style="font-size:13px;margin-top:4px;">${escapeHtml(preview.ekdousa_archi)||'—'}</div></div>
      <div><label>Προμηθευτής</label><div style="font-size:13px;margin-top:4px;">${escapeHtml(preview.promitheftis)||'—'}</div></div>
    </div>
    <div style="font-size:11px;font-weight:600;letter-spacing:1px;text-transform:uppercase;
                color:var(--navy2);margin-bottom:8px;">Υλικά (${grammes.length})</div>
    <div class="table-wrap">
      <table><thead><tr>
        <th>Όνομα</th><th class="text-right">Ποσότητα</th><th>Μονάδα</th>
      </tr></thead><tbody>${grammeRows}</tbody></table>
    </div>`;
}

export async function tplSave(evt) {
  if (!_tplBuiltPatterns) { alert('Κάνε πρώτα Δοκιμή.'); return; }
  const name = document.getElementById('tpl-name').value.trim();
  if (!name) { alert('Δώσε όνομα στο πρότυπο.'); return; }
  const _unlock = _lock(evt?.target);
  try {
    await py('save_pdf_template', { name, ..._tplBuiltPatterns });
    document.getElementById('tpl-name').value = '';
    document.getElementById('tpl-preview-section').style.display = 'none';
    tplReset();
    await loadTplList();
  } catch(e) {
    alert('Σφάλμα αποθήκευσης: ' + e.message);
  } finally { _unlock(); }
}

export async function loadTplList() {
  try {
    const res = await py('list_pdf_templates');
    const body = document.getElementById('tpl-list-body');
    if (!res.templates || !res.templates.length) {
      body.innerHTML = '<div class="empty-state"><div class="icon">🧩</div><p>Δεν υπάρχουν πρότυπα ακόμα</p></div>';
      return;
    }
    const rows = res.templates.map(t => {
      const fields = [
        t.parstatiko_pattern   ? 'Παρ/κό' : null,
        t.imerominia_pattern   ? 'Ημ/νία' : null,
        t.adeia_pattern        ? 'Άδεια'  : null,
        t.ekdousa_archi_pattern? 'Εκδ.Αρχή': null,
        t.promitheftis_pattern ? 'Προμ.'  : null,
        t.tipos_keyword        ? `ΕΠΙΣΤ.: "${escapeHtml(t.tipos_keyword)}"` : null,
      ].filter(Boolean).join(' · ');
      return `
        <tr>
          <td style="font-weight:500;">${escapeHtml(t.name)}</td>
          <td style="font-size:12px;color:var(--muted);">${fields || '—'}</td>
          <td class="mono" style="font-size:11px;color:var(--muted);">${(t.created_at||'').slice(0,16)}</td>
          <td style="text-align:right;">
            <button class="btn btn-danger btn-sm" onclick="tplDelete(${t.id},${escapeHtml(JSON.stringify(t.name))})">🗑</button>
          </td>
        </tr>`;
    }).join('');
    body.innerHTML = `<div class="table-wrap"><table>
      <thead><tr>
        <th>Όνομα</th><th>Πεδία</th><th>Δημιουργήθηκε</th><th></th>
      </tr></thead>
      <tbody>${rows}</tbody>
    </table></div>`;
  } catch(e) {
    document.getElementById('tpl-list-body').innerHTML =
      `<div class="alert alert-error">Σφάλμα φόρτωσης: ${escapeHtml(e.message)}</div>`;
  }
}

export async function tplDelete(id, name) {
  showConfirm(`Διαγραφή προτύπου "${name}";`, async () => {
    try {
      await py('delete_pdf_template', { id });
      await loadTplList();
    } catch(e) { alert('Σφάλμα: ' + e.message); }
  });
}

export async function tplExport() {
  if (!window.api) { alert('Χρησιμοποιήστε την εφαρμογή μέσω Electron'); return; }
  try {
    const path = await window.api.saveJson({ defaultName: 'protupa_parstatikon.json' });
    if (!path) return;
    const res = await py('export_pdf_templates', { path });
    window._showToast(`✅ Εξαγωγή ${res.count} προτύπ${res.count === 1 ? 'ου' : 'ων'} ολοκληρώθηκε`, 'success');
  } catch(e) { alert('Σφάλμα εξαγωγής: ' + e.message); }
}

export async function tplImport() {
  if (!window.api) { alert('Χρησιμοποιήστε την εφαρμογή μέσω Electron'); return; }
  try {
    const path = await window.api.openJson();
    if (!path) return;
    const res = await py('import_pdf_templates', { path });
    const n = res.imported;
    let msg = `✅ Εισαγωγή ${n} προτύπ${n === 1 ? 'ου' : 'ων'} ολοκληρώθηκε`;
    if (res.skipped && res.skipped.length) {
      msg += ` — παραλείφθηκ${res.skipped.length === 1 ? 'ε' : 'αν'} ${res.skipped.length} (ήδη υπάρχ${res.skipped.length === 1 ? 'ει' : 'ουν'}): ${res.skipped.join(', ')}`;
    }
    window._showToast(msg, n > 0 ? 'success' : 'info');
    await loadTplList();
  } catch(e) { alert('Σφάλμα εισαγωγής: ' + e.message); }
}
