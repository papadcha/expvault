import { escapeHtml, py, fmtDate, todayInput } from './utils.js';
import { loadKiniseis } from './kiniseis.js';
import { loadDashboard } from './dashboard.js';

// ── ΥΠΟΛΟΓΙΣΜΟΣ ──────────────────────────────────────────────────────────────
let _ypSenario = 1;
let _ypAgora = [];  // [{yliko_id, yliko_onoma, monada, posotita}]
let _ypResult = []; // αποτέλεσμα υπολογισμού

export function showSenario(s) {
  _ypSenario = s;
  document.getElementById('tab-s1').style.background = s===1 ? 'var(--accent)' : 'var(--surface2)';
  document.getElementById('tab-s1').style.color      = s===1 ? 'white' : 'var(--text)';
  document.getElementById('tab-s2').style.background = s===2 ? 'var(--accent)' : 'var(--surface2)';
  document.getElementById('tab-s2').style.color      = s===2 ? 'white' : 'var(--text)';
  document.getElementById('yp-input-header').textContent  = s===1 ? 'Κατανάλωση' : 'Επιστροφή';
  document.getElementById('yp-result-header').textContent = s===1 ? '→ Επιστροφή' : '→ Κατανάλωση';
  renderYpTable();
}

export async function loadYpologismos() {
  // Φόρτωσε παραστατικά αγοράς
  const kin = await py('get_kiniseis', {tipos: 'ΕΙΣΑΓΩΓΗ'});
  const parstatika = [...new Set(kin.filter(k=>k.arithmos_parstatikos).map(k=>k.arithmos_parstatikos))];
  const sel = document.getElementById('yp-parstatiko');
  sel.innerHTML = '<option value="">— Επιλογή —</option>' +
    parstatika.map(p => `<option value="${escapeHtml(p)}">${escapeHtml(p)}</option>`).join('');
}

export async function loadYpologismosAgora() {
  const parst = document.getElementById('yp-parstatiko').value;
  if (!parst) { _ypAgora = []; renderYpTable(); return; }

  const kin = await py('get_kiniseis', {});
  const agores = kin.filter(k => k.tipos==='ΕΙΣΑΓΩΓΗ' && k.arithmos_parstatikos===parst);

  // Ημερομηνία + άδεια
  if (agores.length) {
    document.getElementById('yp-imerominia').value = fmtDate(agores[0].imerominia);
    document.getElementById('yp-adeia').value = agores[0].arithmos_adeias || '';
  }

  // Αποθήκευση adeia/promitheftis από πρώτη γραμμή αγοράς
  window._ypAgoraAdeia     = agores[0]?.adeia_id || null;
  window._ypAgoraProm      = agores[0]?.promitheftis_id || null;
  window._ypAgoraImerominia = agores[0]?.imerominia || '';

  // Ομαδοποίηση ανά υλικό
  const byYliko = {};
  for (const k of agores) {
    if (!byYliko[k.yliko_id]) byYliko[k.yliko_id] = {
      yliko_id: k.yliko_id, yliko_onoma: k.yliko_onoma,
      monada: k.monada_metrisis, posotita: 0
    };
    byYliko[k.yliko_id].posotita += k.posotita;
  }
  _ypAgora = Object.values(byYliko);
  document.getElementById('yp-results').style.display = 'none';
  renderYpTable();
}

export function renderYpTable() {
  const body = document.getElementById('yp-table-body');
  if (!_ypAgora.length) {
    body.innerHTML = '<tr><td colspan="5" class="text-center" style="padding:24px;color:var(--muted);">Επιλέξτε παραστατικό αγοράς</td></tr>';
    return;
  }
  body.innerHTML = _ypAgora.map((y, i) => `
    <tr>
      <td>${escapeHtml(y.yliko_onoma)}</td>
      <td class="text-right mono">${y.posotita.toFixed(3).replace('.',',')}</td>
      <td class="text-right">
        <input type="number" id="yp-input-${i}" step="0.001" min="0"
          style="width:100px;text-align:right;" placeholder="0">
      </td>
      <td class="text-right mono" id="yp-result-${i}" style="color:var(--accent);">—</td>
      <td>${escapeHtml(y.monada)}</td>
    </tr>`).join('');
}

export function calculateYpologismos() {
  if (!_ypAgora.length) { alert('Επιλέξτε παραστατικό αγοράς'); return; }

  _ypResult = _ypAgora.map((y, i) => {
    const input = parseFloat(document.getElementById(`yp-input-${i}`)?.value) || 0;
    const agora = y.posotita;
    let katanalosi, epistrofi;

    if (_ypSenario === 1) {
      katanalosi = input;
      epistrofi  = Math.max(0, agora - katanalosi);
    } else {
      epistrofi  = input;
      katanalosi = Math.max(0, agora - epistrofi);
    }

    document.getElementById(`yp-result-${i}`).textContent =
      (_ypSenario===1 ? epistrofi : katanalosi).toFixed(3).replace('.',',');

    return {
      yliko_id: y.yliko_id, yliko_onoma: y.yliko_onoma, monada: y.monada,
      posotita_agoras: agora, posotita_katanalosis: katanalosi, posotita_epistrofis: epistrofi
    };
  });

  // Αποθήκευση στη βάση
  const parst = document.getElementById('yp-parstatiko').value;
  const imer  = _ypAgora[0] ? document.getElementById('yp-imerominia').value : '';

  py('save_ypologismos', {
    parstatiko_agoras: parst,
    imerominia_agoras: imer,
    senario: _ypSenario,
    grammes: _ypResult
  });

  showYpResults();
}

export function showYpResults() {
  const title = _ypSenario===1 ? 'Επιστροφή προς NITROCHEM' : 'Κατανάλωση';
  document.getElementById('yp-results-title').textContent = `Αποτέλεσμα: ${title}`;

  const rows = _ypResult.map(r => {
    const val = _ypSenario===1 ? r.posotita_epistrofis : r.posotita_katanalosis;
    return `<tr>
      <td>${escapeHtml(r.yliko_onoma)}</td>
      <td class="text-right mono">${r.posotita_agoras.toFixed(3).replace('.',',')}</td>
      <td class="text-right mono">${(_ypSenario===1?r.posotita_katanalosis:r.posotita_epistrofis).toFixed(3).replace('.',',')}</td>
      <td class="text-right mono" style="color:var(--accent);font-weight:bold;">${val.toFixed(3).replace('.',',')}</td>
      <td>${escapeHtml(r.monada)}</td>
    </tr>`;
  }).join('');

  document.getElementById('yp-results-body').innerHTML = `
    <table>
      <thead><tr>
        <th>Υλικό</th>
        <th class="text-right">Αγορά</th>
        <th class="text-right">${_ypSenario===1?'Κατανάλωση':'Επιστροφή'}</th>
        <th class="text-right" style="color:var(--accent);">${_ypSenario===1?'Επιστροφή':'Κατανάλωση'}</th>
        <th>Μονάδα</th>
      </tr></thead>
      <tbody>${rows}</tbody>
    </table>`;

  document.getElementById('yp-results').style.display = 'block';
  document.getElementById('yp-kataxorisi-btn').style.display = 'none';
  document.getElementById('yp-compare-body').innerHTML = '';
  document.getElementById('yp-epi-msg').innerHTML = '';
  // Σενάριο 1 → εμφάνισε section καταχώρησης επιστροφής
  const epiSection = document.getElementById('yp-save-epistrofi');
  if (_ypSenario === 1) {
    epiSection.style.display = 'block';
    document.getElementById('yp-epi-date').value = todayInput();
    document.getElementById('yp-epi-parst').value = '';
  } else {
    epiSection.style.display = 'none';
  }
  compareYpWithVivlio();
}

export async function compareYpWithVivlio() {
  const parst = document.getElementById('yp-parstatiko').value;
  const r = await py('compare_ypologismos', { parstatiko_agoras: parst });
  const div = document.getElementById('yp-compare-body');

  if (r.ok) {
    div.innerHTML = `<div class="alert" style="background:#c6f6d5;border:1px solid #68d391;color:#276749;">
      ✅ Συμφωνία με το Βιβλίο — οι υπολογισμοί ταιριάζουν.
    </div>`;
    document.getElementById('yp-kataxorisi-btn').style.display = 'inline-flex';
  } else if (r.differences && r.differences.length > 0) {
    const diffs = r.differences.map(d => `
      <tr>
        <td>${escapeHtml(d.yliko_onoma)}</td>
        <td class="text-right mono">${d.katanalosi_ypologistis.toFixed(3).replace('.',',')}</td>
        <td class="text-right mono">${d.katanalosi_vivliou.toFixed(3).replace('.',',')}</td>
        <td class="text-right mono" style="color:var(--danger);">${d.diafora.toFixed(3).replace('.',',')}</td>
        <td>${escapeHtml(d.monada)}</td>
      </tr>`).join('');
    div.innerHTML = `<div class="alert" style="background:#fed7d7;border:1px solid #fc8181;color:#742a2a;">
      ❌ Διαφορά με το Βιβλίο — ελέγξτε τα δεδομένα πριν καταχωρήσετε.
      <table style="margin-top:8px;width:100%;">
        <thead><tr><th>Υλικό</th><th class="text-right">Υπολογιστής</th><th class="text-right">Βιβλίο</th><th class="text-right">Διαφορά</th><th>Μονάδα</th></tr></thead>
        <tbody>${diffs}</tbody>
      </table>
    </div>`;
    document.getElementById('yp-kataxorisi-btn').style.display = 'none';
  } else {
    div.innerHTML = `<div class="alert" style="background:#fff3cd;border:1px solid #ffc107;color:#856404;">
      ⚠️ Εκκρεμεί καταχώρηση επιστροφής στο βιβλίο — η σύγκριση θα γίνει μετά.
    </div>`;
    document.getElementById('yp-kataxorisi-btn').style.display = 'none';
  }
}

export async function kataxoriYpologismos() {
  // Σενάριο 2 μόνο: καταχώρηση κατανάλωσης (η επιστροφή ήδη υπάρχει στο βιβλίο)
  const parst = document.getElementById('yp-parstatiko').value;
  const imer  = window._ypAgoraImerominia || null;
  if (!imer) { alert('Δεν βρέθηκε ημερομηνία'); return; }

  for (const r of _ypResult) {
    const val = r.posotita_katanalosis;
    if (val <= 0) continue;
    await py('add_kinisi', {
      imerominia: imer, tipos: 'ΚΑΤΑΝΑΛΩΣΗ',
      yliko_id: r.yliko_id, posotita: val,
      arithmos_parstatikos: parst, adeia_id: null,
      promitheftis_id: null, paratirishis: 'Από Υπολογισμό',
      ypografi: ''
    });
  }
  await py('delete_ypologismos', { parstatiko_agoras: parst });
  alert('✅ Καταχωρήθηκε στο Βιβλίο');
  loadKiniseis();
  loadDashboard();
}

export async function saveEpistrofiFromYpologismos() {
  const agoraParst = document.getElementById('yp-parstatiko').value;
  const epiParst   = document.getElementById('yp-epi-parst').value.trim() || null;
  const epiDate    = document.getElementById('yp-epi-date').value;
  const msg        = document.getElementById('yp-epi-msg');

  if (!epiDate) {
    msg.innerHTML = '<div class="alert" style="background:#fed7d7;border:1px solid #fc8181;color:#742a2a;">Εισάγετε ημερομηνία επιστροφής.</div>';
    return;
  }

  let saved = 0, errors = [];
  for (const r of _ypResult) {
    if (r.posotita_epistrofis <= 0) continue;
    try {
      await py('add_kinisi', {
        imerominia:           epiDate,
        tipos:                'ΕΠΙΣΤΡΟΦΗ',
        yliko_id:             r.yliko_id,
        posotita:             r.posotita_epistrofis,
        arithmos_parstatikos: epiParst || '',
        adeia_id:             window._ypAgoraAdeia,
        promitheftis_id:      window._ypAgoraProm,
        paratirishis:         '',
        ypografi:             '',
        agora_ref:            agoraParst
      });
      saved++;
    } catch(e) { errors.push(r.yliko_onoma + ': ' + e.message); }
  }

  if (errors.length) {
    msg.innerHTML = `<div class="alert" style="background:#fed7d7;border:1px solid #fc8181;color:#742a2a;">Σφάλματα: ${escapeHtml(errors.join(', '))}</div>`;
  } else {
    msg.innerHTML = `<div class="alert" style="background:#c6f6d5;border:1px solid #68d391;color:#276749;">✅ Καταχωρήθηκαν ${saved} επιστροφές.${!epiParst ? ' Χωρίς παραστατικό — χρησιμοποίησε τη σελίδα Παραστατικά για να το συμπληρώσεις αργότερα.' : ''}</div>`;
    document.getElementById('yp-epi-parst').value = '';
    await loadKiniseis();
  }
}

export async function exportYpologismosPdf() {
  const savePath = await window.api.saveFile({ defaultName: 'ypologismos.pdf', ext: 'pdf' });
  if (!savePath) return;
  const parst = document.getElementById('yp-parstatiko').value;
  await py('export_ypologismos_pdf', {
    parstatiko_agoras: parst, senario: _ypSenario,
    grammes: _ypResult, out_path: savePath
  });
  document.getElementById('export-msg') &&
    (document.getElementById('export-msg').innerHTML = `<div class="alert alert-success">✅ ${escapeHtml(savePath)}</div>`);
}
