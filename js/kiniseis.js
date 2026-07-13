import { escapeHtml, py, todayInput, _lock, fmtDate } from './utils.js';
import { allYlika, ylikoLabel } from './state.js';
import { loadDashboard } from './dashboard.js';
import { openParstEditModal } from './parstatika.js';

// ── ΚΙΝΗΣΕΙΣ ─────────────────────────────────────────────────────────────────
export const KIN_PAGE_SIZE = 25;

export function toggleAgoraRefRow(prefix) {
  const tipos = document.getElementById(`${prefix}-tipos`).value;
  const row   = document.getElementById(`${prefix}-agora-ref-row`);
  if (tipos === 'ΕΠΙΣΤΡΟΦΗ') {
    row.style.display = '';
  } else {
    row.style.display = 'none';
    document.getElementById(`${prefix}-agora-ref`).value = '';
  }
}

export async function loadKiniseis() {
  const yl = document.getElementById('flt-yliko')?.value;
  const tp = document.getElementById('flt-tipos')?.value;
  const ap = document.getElementById('flt-apo')?.value;
  const eo = document.getElementById('flt-eos')?.value;

  const kin = await py('get_kiniseis', {
    yliko_id: yl ? parseInt(yl) : undefined,
    tipos: tp || undefined,
    apo: ap || undefined,
    eos: eo || undefined
  });

  window._kinAll = [...kin].reverse(); // νεότερες πρώτα
  renderKiniseis(KIN_PAGE_SIZE);
}

export function renderKiniseis(limit) {
  const body = document.getElementById('kin-body');
  const all  = window._kinAll || [];

  if (!all.length) {
    body.innerHTML = '<tr><td colspan="10"><div class="empty-state"><div class="icon">📋</div><p>Δεν βρέθηκαν κινήσεις</p></div></td></tr>';
    return;
  }

  const display  = limit ? all.slice(0, limit) : all;
  const hasMore  = limit && all.length > limit;

  body.innerHTML = display.map(k => `<tr>
    <td class="mono">${k.auxon_arithmos}</td>
    <td>${fmtDate(k.imerominia)}</td>
    <td><span class="badge ${k.tipos==='ΕΙΣΑΓΩΓΗ'?'badge-in':k.tipos==='ΚΑΤΑΝΑΛΩΣΗ'?'badge-kat':'badge-out'}">${k.tipos==='ΕΙΣΑΓΩΓΗ'?'📥 ΕΙΣ':k.tipos==='ΚΑΤΑΝΑΛΩΣΗ'?'🔥 ΚΑΤ':k.tipos==='ΕΠΙΣΤΡΟΦΗ'?'🔄 ΕΠΙ':'📤 ΕΞΑ'}</span></td>
    <td>${escapeHtml(k.yliko_onoma)}${k.diatomi_mm?` (${escapeHtml(k.diatomi_mm)}mm)`:''}</td>
    <td class="mono">${escapeHtml(k.arithmos_parstatikos)||'—'}</td>
    <td class="text-right mono">${k.posotita.toFixed(3)} ${escapeHtml(k.monada_metrisis)}</td>
    <td class="mono">${escapeHtml(k.arithmos_adeias)||'—'}</td>
    <td>${escapeHtml(k.promitheftis_onoma)||'—'}</td>
    <td>${escapeHtml(k.ypografi)||'—'}</td>
    <td class="text-center">
      <button class="btn btn-outline btn-sm" data-edit-id="${k.id}">✏️</button>
      <button class="btn btn-danger btn-sm" onclick="confirmDelete('kinisi',${k.id})">🗑</button>
    </td>
  </tr>`).join('') + (hasMore ? `<tr><td colspan="10" style="text-align:center;padding:10px;">
    <button class="btn btn-outline btn-sm" onclick="renderKiniseis(null)">
      ▼ Εμφάνιση όλων (${all.length} κινήσεις)
    </button>
  </td></tr>` : '');

  body.querySelectorAll('button[data-edit-id]').forEach(btn => {
    btn.addEventListener('click', () => {
      const k = (window._kinAll || []).find(x => x.id === parseInt(btn.dataset.editId));
      if (k) editKinisi(k);
    });
  });
}

export async function editKinisi(k) {
  // Αν υπάρχει παραστατικό, άνοιγε group modal με όλες τις κινήσεις αυτού του υλικού
  const rootParstatiko = (k.tipos === 'ΕΠΙΣΤΡΟΦΗ' && k.agora_ref) ? k.agora_ref : k.arithmos_parstatikos;
  if (rootParstatiko) {
    const related = await py('get_kiniseis_by_parstatiko_yliko', {
      arithmos_parstatikos: rootParstatiko,
      yliko_id: k.yliko_id
    });
    const ylikoName = k.yliko_onoma + (k.diatomi_mm ? ` (${k.diatomi_mm}mm)` : '');
    openParstEditModal(related, ylikoName, rootParstatiko);
    return;
  }
  // Χωρίς παραστατικό → single modal
  document.getElementById('ek-title').textContent = `✏️ Επεξεργασία Κίνησης #${k.auxon_arithmos}`;
  document.getElementById('ek-id').value = k.id;

  // Γέμισε τα selects αν είναι άδεια
  const ekYliko = document.getElementById('ek-yliko');
  if (ekYliko.options.length <= 1) {
    const ylika = await py('get_ylika');
    ekYliko.innerHTML = '<option value="">— Επιλογή —</option>' +
      ylika.map(y => `<option value="${y.id}">${ylikoLabel(y)}</option>`).join('');
  }
  const ekProm = document.getElementById('ek-prom');
  if (ekProm.options.length <= 1) {
    const proms = await py('get_promitheftes');
    ekProm.innerHTML = '<option value="">— Κανένας —</option>' +
      proms.map(p => `<option value="${p.id}">${escapeHtml(p.onoma)}</option>`).join('');
  }
  const ekAdeia = document.getElementById('ek-adeia');
  if (ekAdeia.options.length <= 1) {
    const adeies = await py('get_adeies');
    ekAdeia.innerHTML = '<option value="">— Καμία —</option>' +
      adeies.map(a => `<option value="${a.id}">${escapeHtml(a.arithmos_adeias)}</option>`).join('');
  }

  document.getElementById('ek-imerominia').value = k.imerominia;
  document.getElementById('ek-tipos').value = k.tipos;
  document.getElementById('ek-yliko').value = k.yliko_id;
  document.getElementById('ek-posotita').value = k.posotita;
  document.getElementById('ek-parstatiko').value = k.arithmos_parstatikos || '';
  document.getElementById('ek-adeia').value = k.adeia_id || '';
  document.getElementById('ek-prom').value = k.promitheftis_id || '';
  document.getElementById('ek-paratirishis').value = k.paratirishis || '';
  document.getElementById('ek-ypografi').value = k.ypografi || '';
  document.getElementById('ek-agora-ref').value = k.agora_ref || '';
  document.getElementById('ek-agora-ref-row').style.display = k.tipos === 'ΕΠΙΣΤΡΟΦΗ' ? '' : 'none';

  document.getElementById('edit-kinisi-modal').classList.add('open');
}

export function closeEditKinisiModal() {
  document.getElementById('edit-kinisi-modal').classList.remove('open');
}

export async function saveEditKinisi() {
  const id = parseInt(document.getElementById('ek-id').value);
  const tipos = document.getElementById('ek-tipos').value;
  const body = {
    id,
    imerominia:           document.getElementById('ek-imerominia').value,
    tipos,
    yliko_id:             parseInt(document.getElementById('ek-yliko').value),
    posotita:             parseFloat(document.getElementById('ek-posotita').value),
    arithmos_parstatikos: document.getElementById('ek-parstatiko').value,
    adeia_id:             document.getElementById('ek-adeia').value || null,
    promitheftis_id:      document.getElementById('ek-prom').value || null,
    paratirishis:         document.getElementById('ek-paratirishis').value,
    ypografi:             document.getElementById('ek-ypografi').value,
    agora_ref:            tipos === 'ΕΠΙΣΤΡΟΦΗ' ? (document.getElementById('ek-agora-ref').value.trim() || null) : null,
  };
  if (!body.imerominia || !body.tipos || !body.yliko_id || isNaN(body.posotita)) {
    alert('Συμπληρώστε τα υποχρεωτικά πεδία (Ημερομηνία, Τύπος, Υλικό, Ποσότητα).');
    return;
  }
  const _unlock = _lock(event?.target);
  try {
    await py('update_kinisi', body);
    closeEditKinisiModal();
    await loadKiniseis();
    await checkEkkremotita(body.yliko_id, body.imerominia, body.arithmos_parstatikos);
  } catch(e) { alert('Σφάλμα αποθήκευσης: ' + e.message); }
  finally { _unlock(); }
}

export async function checkAdeiaYpoloipo() {
  const hint    = document.getElementById('kin-adeia-hint');
  const adeia_id = parseInt(document.getElementById('kin-adeia').value);
  const yliko_id = parseInt(document.getElementById('kin-yliko').value);
  const tipos    = document.getElementById('kin-tipos').value;
  if (!adeia_id || !yliko_id || tipos !== 'ΕΙΣΑΓΩΓΗ') { hint.style.display='none'; return; }
  const yliko = allYlika.find(y => y.id === yliko_id);
  const nomiki_katigoria = yliko?.nomiki_katigoria;
  if (!nomiki_katigoria) { hint.style.display='none'; return; }
  const r = await py('get_adeia_katigoria_remaining', { adeia_id, nomiki_katigoria });
  if (!r || r.egekrimeni_posotita === undefined) { hint.style.display='none'; return; }
  const yp = r.ypoloipo;
  const ok = yp > 0;
  hint.style.display = '';
  hint.style.background = ok ? '#c6f6d5' : '#fed7d7';
  hint.style.border = ok ? '1px solid #68d391' : '1px solid #fc8181';
  hint.style.color  = ok ? '#276749' : '#742a2a';
  hint.innerHTML = `📋 Υπόλοιπο άδειας (${nomiki_katigoria}): <strong>${yp.toFixed(3)} ${escapeHtml(r.monada_metrisis)}</strong> (εγκεκρ. ${r.egekrimeni_posotita.toFixed(3)}, χρησιμ. ${r.xrisimopoiimeni.toFixed(3)})`;
}

export async function saveKinisi() {
  const id = document.getElementById('kin-edit-id').value;
  const tipos = document.getElementById('kin-tipos').value;
  const body = {
    imerominia:  document.getElementById('kin-imerominia').value,
    tipos,
    yliko_id:    parseInt(document.getElementById('kin-yliko').value),
    posotita:    parseFloat(document.getElementById('kin-posotita').value),
    arithmos_parstatikos: document.getElementById('kin-parstatiko').value,
    adeia_id:    document.getElementById('kin-adeia').value || null,
    promitheftis_id: document.getElementById('kin-prom').value || null,
    paratirishis: document.getElementById('kin-paratirishis').value,
    ypografi:    document.getElementById('kin-ypografi').value,
    agora_ref:   tipos === 'ΕΠΙΣΤΡΟΦΗ' ? (document.getElementById('kin-agora-ref').value.trim() || null) : null,
  };
  if (!body.imerominia || !body.tipos || !body.yliko_id || isNaN(body.posotita)) {
    alert('Συμπληρώστε τα υποχρεωτικά πεδία (Ημερομηνία, Τύπος, Υλικό, Ποσότητα).');
    return;
  }
  const _unlock = _lock(event?.target);
  try {
    if (id) await py('update_kinisi', { id: parseInt(id), ...body });
    else     await py('add_kinisi', body);
    clearKinisiForm();
    await loadKiniseis();
    await checkEkkremotita(body.yliko_id, body.imerominia, body.arithmos_parstatikos);
  } catch(e) { alert('Σφάλμα: ' + e.message); }
  finally { _unlock(); }
}

export async function checkEkkremotita(yliko_id, imerominia, parstatiko='') {
  const banner = document.getElementById('ekkremotita-banner');
  try {
    const payload = { yliko_id, imerominia };
    if (parstatiko) payload.parstatiko = parstatiko;
    const r = await py('check_ekkremotita', payload);
    if (!r.ekkremotita) { banner.style.display='none'; banner.innerHTML=''; return; }

    window._ekkData = r.ekkremes;

    const lines = r.ekkremes.map(e => {
      const tipo_label = e.tipo === 'ΚΑΤΑΝΑΛΩΣΗ' ? '🔥 Κατανάλωση' : '🔄 Επιστροφή';
      const fmt = e.posotita.toFixed(3).replace('.',',');
      return `<div>• ${tipo_label} <strong>${escapeHtml(e.yliko_onoma)}</strong>: ${fmt} ${escapeHtml(e.monada)}</div>`;
    }).join('');

    banner.innerHTML = `
      <div class="alert" style="background:#fff3cd;border:1px solid #ffc107;color:#856404;">
        <strong>⚠️ Εκκρεμείς καταχωρήσεις:</strong>
        <div style="margin:8px 0;font-size:12px;">${lines}</div>
        <div style="display:flex;gap:8px;margin-top:8px;">
          <button class="btn btn-sm btn-accent" id="ekk-save-btn">✅ Καταχώρηση Όλων</button>
          <button class="btn btn-sm btn-outline" id="ekk-close-btn">✖ Κλείσιμο</button>
        </div>
      </div>`;
    banner.style.display = 'block';

    document.getElementById('ekk-save-btn').addEventListener('click', autoKataxorisiAll);
    document.getElementById('ekk-close-btn').addEventListener('click', () => {
      banner.style.display='none'; banner.innerHTML='';
    });
  } catch(e) { banner.style.display='none'; }
}

export function checkBannerEmpty() {}
export async function autoKataxorisi(btn) {}

export async function autoKataxorisiAll() {
  const banner = document.getElementById('ekkremotita-banner');
  const data = window._ekkData || [];
  if (!data.length) return;

  banner.innerHTML = '<div class="alert" style="background:#fff3cd;border:1px solid #ffc107;color:#856404;">⏳ Καταχώρηση σε εξέλιξη...</div>';

  let errors = [];
  for (const ekk of data) {
    if (!ekk) continue;
    try {
      // Χρήση parstatiko από το window._ekkParstatiko (αγορά) ή ekk-parst-input (επιστροφή)
      const ekkParst = window._ekkParstatiko ||
                       document.getElementById('ekk-parst-input')?.value?.trim() || '';
      // Ημερομηνία: πάντα από την αγορά (window._ekkImerominia) αν υπάρχει
      const ekkImer = window._ekkImerominia || ekk.imerominia;
      // Αποθήκευση μόνο ΕΠΙΣΤΡΟΦΗ — η ΚΑΤΑΝΑΛΩΣΗ υπολογίζεται on-the-fly στο export
      if (ekk.tipo === 'ΚΑΤΑΝΑΛΩΣΗ') continue;
      await py('add_kinisi', {
        imerominia:           ekkImer,
        tipos:                ekk.tipo,
        yliko_id:             ekk.yliko_id,
        posotita:             ekk.posotita,
        arithmos_parstatikos: ekkParst,
        adeia_id:             null,
        promitheftis_id:      null,
        paratirishis:         'Αυτόματος υπολογισμός',
        ypografi:             ''
      });
    } catch(e) { errors.push(ekk.yliko_onoma + ': ' + e.message); }
  }

  window._ekkData = [];
  window._ekkParstatiko = null;
  window._ekkImerominia = null;
  banner.style.display = 'none';
  banner.innerHTML = '';
  const pdfAlert = document.getElementById('pdf-alert');
  if (pdfAlert) pdfAlert.innerHTML = '<div class="alert" style="background:#c6f6d5;border:1px solid #68d391;color:#276749;">✅ Όλες οι καταχωρήσεις ολοκληρώθηκαν.</div>';
  if (errors.length) alert('Σφάλματα: ' + errors.join(', '));
  await loadKiniseis();
  await loadDashboard();
}

export function clearKinisiForm() {
  document.getElementById('kin-edit-id').value = '';
  document.getElementById('kin-form-title').textContent = 'Νέα Καταχώρηση';
  ['kin-imerominia','kin-posotita','kin-parstatiko','kin-paratirishis','kin-ypografi','kin-agora-ref'].forEach(id => {
    document.getElementById(id).value = '';
  });
  document.getElementById('kin-imerominia').value = todayInput();
  document.getElementById('kin-tipos').value = 'ΕΙΣΑΓΩΓΗ';
  document.getElementById('kin-yliko').value = '';
  document.getElementById('kin-adeia').value = '';
  document.getElementById('kin-prom').value = '';
  document.getElementById('kin-agora-ref-row').style.display = 'none';
  document.getElementById('kin-adeia-hint').style.display = 'none';
}

export function clearFilters() {
  ['flt-yliko','flt-tipos','flt-apo','flt-eos'].forEach(id => document.getElementById(id).value='');
  loadKiniseis();
}

// Κλείσιμο edit-kinisi-modal με click στο overlay
document.getElementById('edit-kinisi-modal').addEventListener('click', function(e) {
  if (e.target === this) closeEditKinisiModal();
});
