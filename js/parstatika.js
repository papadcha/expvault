import { escapeHtml, py, fmtDate, _lock, showConfirm } from './utils.js';
import { loadKiniseis } from './kiniseis.js';
import { loadYpologismos, loadYpologismosAgora, showSenario } from './ypologismos.js';

// ── ΔΙΑΧΕΙΡΙΣΗ ΠΑΡΑΣΤΑΤΙΚΩΝ ──────────────────────────────────────────────────
export async function loadParstatikaPage() {
  const kiniseis = await py('get_kiniseis', {});

  // Γέμισμα dropdowns Άδεια / Προμηθευτής για μετονομασία
  const [adeies, proms] = await Promise.all([py('get_adeies'), py('get_promitheftes')]);
  document.getElementById('rn-new-adeia').innerHTML =
    '<option value="">— Δεν αλλάζει —</option>' +
    adeies.map(a => `<option value="${a.id}">${escapeHtml(a.arithmos_adeias)}${a.perigrafi?' — '+escapeHtml(a.perigrafi):''}</option>`).join('');
  document.getElementById('rn-new-prom').innerHTML =
    '<option value="">— Δεν αλλάζει —</option>' +
    proms.map(p => `<option value="${p.id}">${escapeHtml(p.onoma)}${p.syntomografia?' ('+escapeHtml(p.syntomografia)+')':''}</option>`).join('');

  // Datalist αγορών για agora_ref
  const agoresParst = [...new Set(
    kiniseis.filter(k => k.tipos==='ΕΙΣΑΓΩΓΗ' && k.arithmos_parstatikos).map(k=>k.arithmos_parstatikos)
  )].sort();
  document.getElementById('rn-agora-datalist').innerHTML =
    agoresParst.map(p => `<option value="${escapeHtml(p)}">`).join('');

  // Dropdown αγορών — μόνο αγορές με εκκρεμείς επιστροφές χωρίς παραστατικό
  const pendingAgores = await py('get_agores_with_pending_epistrofes', {});
  const agoraSel = document.getElementById('pp-agora-sel');
  if (pendingAgores.length) {
    agoraSel.innerHTML = '<option value="">— Επιλογή —</option>' +
      pendingAgores.map(k => `<option value="${escapeHtml(k.arithmos_parstatikos)}">${escapeHtml(k.arithmos_parstatikos)} (${fmtDate(k.imerominia)})</option>`).join('');
  } else {
    agoraSel.innerHTML = '<option value="">✅ Δεν υπάρχουν εκκρεμείς επιστροφές</option>';
  }

  // Datalist μετονομασίας (όλα τα μοναδικά παραστατικά)
  const allParst = [...new Set(
    kiniseis.filter(k => k.arithmos_parstatikos).map(k => k.arithmos_parstatikos)
  )].sort();

  document.getElementById('rn-datalist').innerHTML =
    allParst.map(p => `<option value="${escapeHtml(p)}">`).join('');

  document.getElementById('pp-preview').innerHTML = '';
  document.getElementById('pp-msg').innerHTML = '';
  document.getElementById('rn-msg').innerHTML = '';
  document.getElementById('rn-preview').innerHTML = '';
  document.getElementById('rn-search').value = '';
  document.getElementById('rn-new-adeia').value = '';
  document.getElementById('rn-new-prom').value = '';
  document.getElementById('rn-new-agora-ref').value = '';
  document.getElementById('rn-agora-ref-row').style.display = 'none';
  window._rnLinkedCount = 0;
  window._rnLinkedAgoraRef = null;
}

export async function loadEpistrofesWithoutParst() {
  const agoraParst = document.getElementById('pp-agora-sel').value;
  const preview = document.getElementById('pp-preview');
  if (!agoraParst) { preview.innerHTML = ''; return; }

  const rows = await py('get_epistrofes_without_parstatiko', { agora_ref: agoraParst });
  if (!rows.length) {
    preview.innerHTML = '<div class="alert" style="background:#c6f6d5;border:1px solid #68d391;color:#276749;">✅ Δεν υπάρχουν επιστροφές χωρίς παραστατικό για αυτή την αγορά.</div>';
    return;
  }
  const trs = rows.map(r => `<tr>
    <td class="mono">${r.auxon_arithmos}</td>
    <td>${fmtDate(r.imerominia)}</td>
    <td>${escapeHtml(r.yliko_onoma)}${r.diatomi_mm ? ` (${escapeHtml(r.diatomi_mm)}mm)` : ''}</td>
    <td class="text-right mono">${r.posotita.toFixed(3)} ${escapeHtml(r.monada_metrisis)}</td>
  </tr>`).join('');
  preview.innerHTML = `
    <p style="font-size:12px;color:var(--muted);margin-bottom:6px;">Επιστροφές που θα ενημερωθούν (${rows.length}):</p>
    <table style="width:100%;border-collapse:collapse;font-size:13px;">
      <thead><tr style="background:var(--navy);color:white;">
        <th style="padding:6px 10px;text-align:left;font-size:11px;">Α/Α</th>
        <th style="padding:6px 10px;text-align:left;font-size:11px;">Ημ/νία</th>
        <th style="padding:6px 10px;text-align:left;font-size:11px;">Υλικό</th>
        <th style="padding:6px 10px;text-align:right;font-size:11px;">Ποσότητα</th>
      </tr></thead>
      <tbody>${trs}</tbody>
    </table>`;
}

export async function assignEpistrofiParst() {
  const agoraParst = document.getElementById('pp-agora-sel').value;
  const newParst   = document.getElementById('pp-new-parst').value.trim();
  const newDate    = document.getElementById('pp-new-date').value;
  const msg        = document.getElementById('pp-msg');

  if (!agoraParst || !newParst || !newDate) {
    msg.innerHTML = '<div class="alert" style="background:#fed7d7;border:1px solid #fc8181;color:#742a2a;margin-top:8px;">Συμπληρώστε αγορά, παραστατικό και ημερομηνία.</div>';
    return;
  }
  try {
    const r = await py('assign_epistrofi_parstatiko', { agora_ref: agoraParst, new_parstatiko: newParst, new_date: newDate });
    if (r.updated === 0) {
      msg.innerHTML = '<div class="alert" style="background:#fff3cd;border:1px solid #ffc107;color:#856404;margin-top:8px;">⚠️ Δεν βρέθηκαν επιστροφές χωρίς παραστατικό για αυτή την αγορά.</div>';
    } else {
      msg.innerHTML = `<div class="alert" style="background:#c6f6d5;border:1px solid #68d391;color:#276749;margin-top:8px;">✅ Ενημερώθηκαν ${r.updated} επιστροφές με παραστατικό <strong>${escapeHtml(newParst)}</strong>.</div>`;
      document.getElementById('pp-new-parst').value = '';
      document.getElementById('pp-new-date').value = '';
      await loadEpistrofesWithoutParst();
    }
  } catch(e) { msg.innerHTML = `<div class="alert" style="background:#fed7d7;border:1px solid #fc8181;color:#742a2a;margin-top:8px;">Σφάλμα: ${escapeHtml(e.message)}</div>`; }
}

export async function loadRenamePreview() {
  const val = document.getElementById('rn-search').value.trim();
  const preview = document.getElementById('rn-preview');
  if (!val) { preview.innerHTML = ''; return; }

  // Έλεγχος αν το παραστατικό υπάρχει στο datalist
  const opts = [...document.getElementById('rn-datalist').options].map(o => o.value);
  if (!opts.includes(val)) { preview.innerHTML = ''; return; }

  const kiniseis = await py('get_kiniseis', {});
  const related = kiniseis.filter(k => k.arithmos_parstatikos === val);
  if (!related.length) { preview.innerHTML = ''; return; }

  // Επιστροφές συνδεδεμένες μέσω agora_ref (έχουν δικό τους parstatiko)
  const linkedEpistrofes = kiniseis.filter(k =>
    k.tipos === 'ΕΠΙΣΤΡΟΦΗ' && k.agora_ref === val && k.arithmos_parstatikos !== val
  );
  window._rnLinkedCount = linkedEpistrofes.length; // για χρήση στη διαγραφή

  // Ομαδοποίηση ανά τύπο
  const agores     = related.filter(k => k.tipos === 'ΕΙΣΑΓΩΓΗ');
  const epistrofes = [
    ...related.filter(k => k.tipos === 'ΕΠΙΣΤΡΟΦΗ'),
    ...linkedEpistrofes
  ];

  // Αν το παραστατικό είναι επιστροφή → φόρτωσε και την αγορά (agora_ref)
  const firstEpi = related.find(k => k.tipos === 'ΕΠΙΣΤΡΟΦΗ');
  const linkedAgoraRef = (agores.length === 0 && firstEpi?.agora_ref) ? firstEpi.agora_ref : null;
  const linkedAgora = linkedAgoraRef
    ? kiniseis.filter(k => k.tipos === 'ΕΙΣΑΓΩΓΗ' && k.arithmos_parstatikos === linkedAgoraRef)
    : [];
  window._rnLinkedAgoraRef = linkedAgoraRef; // για χρήση στη διαγραφή

  const tipoLbl = { 'ΕΙΣΑΓΩΓΗ': '📥 Αγορά', 'ΕΠΙΣΤΡΟΦΗ': '🔄 Επιστροφή' };
  const tipoCls = { 'ΕΙΣΑΓΩΓΗ': '#2b6cb0', 'ΕΠΙΣΤΡΟΦΗ': '#c53030' };

  const allRows = [...agores, ...epistrofes];

  // Πληροφορίες — προτεραιότητα στην αγορά (είτε άμεση είτε linked)
  const firstAgora = agores[0] || linkedAgora[0] || related[0];
  const infoLines = [
    firstAgora?.imerominia ? `📅 ${fmtDate(firstAgora.imerominia)}` : '',
    firstAgora?.arithmos_adeias ? `📋 Άδεια: ${escapeHtml(firstAgora.arithmos_adeias)}` : '',
    firstAgora?.promitheftis_onoma ? `🏭 ${escapeHtml(firstAgora.promitheftis_onoma)}` : '',
    linkedAgoraRef ? `🔗 Αγορά: ${escapeHtml(linkedAgoraRef)}` : '',
  ].filter(Boolean).join('&emsp;');

  // Προεπιλογή τρεχουσών τιμών στα dropdowns
  const dropSrc = agores[0] || related[0];
  if (dropSrc?.adeia_id) document.getElementById('rn-new-adeia').value = dropSrc.adeia_id;
  if (dropSrc?.promitheftis_id) document.getElementById('rn-new-prom').value = dropSrc.promitheftis_id;

  // Agora-ref row: εμφάνιση μόνο αν υπάρχουν επιστροφές
  const agoraRefRow = document.getElementById('rn-agora-ref-row');
  if (epistrofes.length) {
    agoraRefRow.style.display = '';
    const currentRef = epistrofes[0].agora_ref || '';
    document.getElementById('rn-new-agora-ref').value = currentRef;
    document.getElementById('rn-new-agora-ref').placeholder = currentRef || 'αφήστε κενό αν δεν αλλάζει';
  } else {
    agoraRefRow.style.display = 'none';
    document.getElementById('rn-new-agora-ref').value = '';
  }

  const makeRows = (kins, dimmed) => kins.map(k => `
    <tr style="border-bottom:1px solid #e2e8f0;${dimmed?'opacity:0.55;background:#f8f8f8;':''}" >
      <td style="padding:5px 8px;">
        <span style="font-size:11px;font-weight:600;color:${tipoCls[k.tipos]||'#555'};">
          ${tipoLbl[k.tipos]||k.tipos}${dimmed?' (συνδεδεμένη αγορά)':''}
        </span>
        ${k.arithmos_parstatikos && k.arithmos_parstatikos !== val
          ? `<br><span style="font-size:10px;color:#718096;">Παρ: ${escapeHtml(k.arithmos_parstatikos)}</span>` : ''}
      </td>
      <td style="padding:5px 8px;font-size:12px;">${fmtDate(k.imerominia)}</td>
      <td style="padding:5px 8px;font-size:12px;">${escapeHtml(k.yliko_onoma)}${k.diatomi_mm?` (${escapeHtml(k.diatomi_mm)}mm)`:''}</td>
      <td style="padding:5px 8px;font-size:12px;text-align:right;font-family:monospace;">
        ${k.posotita.toFixed(3)} ${escapeHtml(k.monada_metrisis)}
      </td>
    </tr>`).join('');

  const allHtml = makeRows(allRows, false) + makeRows(linkedAgora, true);

  preview.innerHTML = `
    <div style="border:1px solid #bee3f8;background:#ebf8ff;border-radius:8px;padding:10px 14px;margin-bottom:4px;">
      <div style="font-size:12px;color:#2c5282;margin-bottom:8px;">${infoLines}</div>
      <table style="width:100%;border-collapse:collapse;">
        <thead>
          <tr style="background:#dbeafe;">
            <th style="padding:4px 8px;font-size:11px;text-align:left;">Τύπος</th>
            <th style="padding:4px 8px;font-size:11px;text-align:left;">Ημ/νία</th>
            <th style="padding:4px 8px;font-size:11px;text-align:left;">Υλικό</th>
            <th style="padding:4px 8px;font-size:11px;text-align:right;">Ποσότητα</th>
          </tr>
        </thead>
        <tbody>${allHtml}</tbody>
      </table>
      <div style="font-size:11px;color:#4a5568;margin-top:6px;">${related.length} κινήσεις${linkedAgora.length?` + ${linkedAgora.length} της συνδεδεμένης αγοράς`:''}</div>
    </div>`;
}

export async function applyRename() {
  const oldParst       = document.getElementById('rn-search').value.trim();
  const newParst       = document.getElementById('rn-new-parst').value.trim() || null;
  const newDate        = document.getElementById('rn-new-date').value || null;
  const newAdeiaId     = document.getElementById('rn-new-adeia').value || null;
  const newPromId      = document.getElementById('rn-new-prom').value || null;
  const agoraRefRow    = document.getElementById('rn-agora-ref-row');
  const newAgoraRef    = agoraRefRow.style.display !== 'none'
                         ? (document.getElementById('rn-new-agora-ref').value.trim() || null)
                         : undefined;
  const msg = document.getElementById('rn-msg');

  if (!oldParst || (!newParst && !newDate && !newAdeiaId && !newPromId && newAgoraRef === undefined)) {
    msg.innerHTML = '<div class="alert" style="background:#fed7d7;border:1px solid #fc8181;color:#742a2a;margin-top:8px;">Επιλέξτε παραστατικό και εισάγετε τουλάχιστον ένα πεδίο για αλλαγή.</div>';
    return;
  }
  // Προειδοποίηση αν το νέο παραστατικό ήδη υπάρχει (θα γίνει merge)
  if (newParst && newParst !== oldParst) {
    const existingParst = [...document.getElementById('rn-datalist').options].map(o => o.value);
    if (existingParst.includes(newParst)) {
      showConfirm(
        `⚠️ Το παραστατικό "${newParst}" υπάρχει ήδη.\nΌλες οι κινήσεις του "${oldParst}" θα ΣΥΓΧΩΝΕΥΤΟΥΝ με το "${newParst}". Είστε σίγουροι;`,
        async () => {
          try {
            const payload = { old_parst: oldParst, new_parst: newParst, new_date: newDate };
            if (newAdeiaId)   payload.new_adeia_id       = parseInt(newAdeiaId);
            if (newPromId)    payload.new_promitheftis_id = parseInt(newPromId);
            if (newAgoraRef !== undefined) payload.new_agora_ref = newAgoraRef;
            const r = await py('batch_update_parstatiko', payload);
            msg.innerHTML = `<div class="alert" style="background:#c6f6d5;border:1px solid #68d391;color:#276749;margin-top:8px;">✅ Ενημερώθηκαν ${r.updated} κινήσεις.</div>`;
            document.getElementById('rn-new-parst').value = '';
            document.getElementById('rn-new-date').value  = '';
            document.getElementById('rn-new-adeia').value = '';
            document.getElementById('rn-new-prom').value  = '';
            document.getElementById('rn-new-agora-ref').value = '';
            document.getElementById('rn-search').value = newParst || oldParst;
            document.getElementById('rn-preview').innerHTML = '';
            await loadParstatikaPage();
          } catch(e) { msg.innerHTML = `<div class="alert" style="background:#fed7d7;border:1px solid #fc8181;color:#742a2a;margin-top:8px;">Σφάλμα: ${escapeHtml(e.message)}</div>`; }
        }
      );
      return;
    }
  }
  try {
    const payload = { old_parst: oldParst, new_parst: newParst, new_date: newDate };
    if (newAdeiaId)   payload.new_adeia_id      = parseInt(newAdeiaId);
    if (newPromId)    payload.new_promitheftis_id = parseInt(newPromId);
    if (newAgoraRef !== undefined) payload.new_agora_ref = newAgoraRef;

    const r = await py('batch_update_parstatiko', payload);
    msg.innerHTML = `<div class="alert" style="background:#c6f6d5;border:1px solid #68d391;color:#276749;margin-top:8px;">✅ Ενημερώθηκαν ${r.updated} κινήσεις.</div>`;
    document.getElementById('rn-new-parst').value = '';
    document.getElementById('rn-new-date').value = '';
    document.getElementById('rn-new-adeia').value = '';
    document.getElementById('rn-new-prom').value = '';
    document.getElementById('rn-new-agora-ref').value = '';
    document.getElementById('rn-search').value = newParst || oldParst;
    document.getElementById('rn-preview').innerHTML = '';
    await loadParstatikaPage();
  } catch(e) { msg.innerHTML = `<div class="alert" style="background:#fed7d7;border:1px solid #fc8181;color:#742a2a;margin-top:8px;">Σφάλμα: ${escapeHtml(e.message)}</div>`; }
}

export function promptDeleteParstatiko() {
  const val = document.getElementById('rn-search').value.trim();
  if (!val) return;

  const hasRelated = (window._rnLinkedCount || 0) > 0;
  const confirmDiv = document.getElementById('rn-delete-confirm');
  const infoDiv    = document.getElementById('rn-delete-info');
  const bothBtn    = document.getElementById('rn-del-both-btn');

  const linkedAgoraRef = window._rnLinkedAgoraRef || null;
  let msg = `⚠️ Πρόκειται να διαγραφούν <strong>όλες οι κινήσεις</strong> με παραστατικό <strong>${escapeHtml(val)}</strong>.`;
  if (hasRelated) {
    msg += `<br>Υπάρχουν ${window._rnLinkedCount} συσχετισμένες επιστροφές (agora_ref = ${escapeHtml(val)}).`;
    msg += `<br><em>Αν διαγραφεί μόνο η αγορά, οι επιστροφές μένουν ορφανές και οι ποσότητες δεν θα υπολογίζονται σωστά.</em>`;
    bothBtn.style.display = '';
  } else if (linkedAgoraRef) {
    msg += `<br>Αυτή η επιστροφή συνδέεται με την αγορά <strong>${escapeHtml(linkedAgoraRef)}</strong>.`;
    msg += `<br><em>Αν διαγραφεί μόνο η επιστροφή, η αγορά θα υπολογίζει πλήρη κατανάλωση (χωρίς επιστροφή).</em>`;
    bothBtn.style.display = 'none';
  } else {
    bothBtn.style.display = 'none';
  }
  infoDiv.innerHTML = msg;
  confirmDiv.style.display = '';
  document.getElementById('rn-msg').innerHTML = '';
}

export function cancelDeleteParstatiko() {
  document.getElementById('rn-delete-confirm').style.display = 'none';
}

export async function confirmDeleteParstatiko(includeRelated) {
  const val           = document.getElementById('rn-search').value.trim();
  const linkedAgoraRef = window._rnLinkedAgoraRef || null;
  const msg = document.getElementById('rn-msg');
  document.getElementById('rn-delete-confirm').style.display = 'none';
  try {
    await py('delete_parstatiko_with_related', {
      arithmos_parstatikos: val,
      include_agora_ref: includeRelated
    });

    // Αν διαγράφηκε επιστροφή (όχι αγορά) → άνοιξε Υπολογιστή με την αγορά
    if (linkedAgoraRef && !includeRelated) {
      await navigateToYpologismos(linkedAgoraRef);
      return;
    }

    msg.innerHTML = `<div class="alert" style="background:#c6f6d5;border:1px solid #68d391;color:#276749;margin-top:8px;">✅ Το παραστατικό <strong>${escapeHtml(val)}</strong> διαγράφηκε${includeRelated?' μαζί με τις συσχετισμένες επιστροφές':''} .</div>`;
    document.getElementById('rn-search').value = '';
    document.getElementById('rn-preview').innerHTML = '';
    document.getElementById('rn-new-parst').value = '';
    document.getElementById('rn-new-date').value = '';
    document.getElementById('rn-new-adeia').value = '';
    document.getElementById('rn-new-prom').value = '';
    document.getElementById('rn-new-agora-ref').value = '';
    document.getElementById('rn-agora-ref-row').style.display = 'none';
    await loadParstatikaPage();
  } catch(e) {
    msg.innerHTML = `<div class="alert" style="background:#fed7d7;border:1px solid #fc8181;color:#742a2a;margin-top:8px;">Σφάλμα: ${escapeHtml(e.message)}</div>`;
  }
}

export async function navigateToYpologismos(parstatiko) {
  // Πλοήγηση στον Υπολογιστή
  document.querySelectorAll('.nav-item').forEach(x => x.classList.remove('active'));
  document.querySelectorAll('.page').forEach(x => x.classList.remove('active'));
  const navEl = document.querySelector('.nav-item[data-page="ypologismos"]');
  if (navEl) navEl.classList.add('active');
  document.getElementById('page-ypologismos').classList.add('active');

  // Φόρτωσε τη λίστα αγορών και επέλεξε το παραστατικό
  await loadYpologismos();
  showSenario(1);
  const sel = document.getElementById('yp-parstatiko');
  sel.value = parstatiko;
  await loadYpologismosAgora();
}

// ── ΕΠΕΞΕΡΓΑΣΙΑ ΟΜΑΔΑΣ ΚΙΝΗΣΕΩΝ (ΠΑΡΑΣΤΑΤΙΚΟ + ΥΛΙΚΟ) ───────────────────────
let _peKiniseis = [];

export function openParstEditModal(kiniseis, ylikoName, parstatiko) {
  _peKiniseis = kiniseis;
  document.getElementById('pe-title').textContent = `✏️ ${ylikoName}  —  Παρ. ${parstatiko}`;

  const tipoLabel = { 'ΕΙΣΑΓΩΓΗ': '📥 Αγορά', 'ΚΑΤΑΝΑΛΩΣΗ': '🔥 Κατανάλωση', 'ΕΠΙΣΤΡΟΦΗ': '🔄 Επιστροφή' };
  const tipoCls   = { 'ΕΙΣΑΓΩΓΗ': 'badge-in', 'ΚΑΤΑΝΑΛΩΣΗ': 'badge-kat', 'ΕΠΙΣΤΡΟΦΗ': 'badge-out' };

  const rows = kiniseis.map(k => `
    <tr style="border-bottom:1px solid var(--border);">
      <td style="padding:10px 12px;">
        <span class="badge ${tipoCls[k.tipos]||''}">${tipoLabel[k.tipos]||k.tipos}</span>
      </td>
      <td style="padding:10px 12px;">
        <input type="date" id="pe-date-${k.id}" value="${k.imerominia}"
          style="border:1px solid var(--border);border-radius:4px;padding:5px 7px;font-size:13px;width:140px;">
      </td>
      <td style="padding:10px 12px;text-align:right;">
        <input type="number" id="pe-pos-${k.id}" value="${k.posotita}" step="0.001" min="0.001"
          style="border:1px solid var(--border);border-radius:4px;padding:5px 7px;font-size:13px;width:100px;text-align:right;font-family:var(--mono);">
        <span style="font-size:12px;color:var(--muted);margin-left:4px;">${escapeHtml(k.monada_metrisis)}</span>
      </td>
      <td style="padding:10px 12px;">
        <input type="text" id="pe-ypografi-${k.id}" value="${escapeHtml(k.ypografi)||''}"
          style="border:1px solid var(--border);border-radius:4px;padding:5px 7px;font-size:13px;width:120px;">
      </td>
    </tr>`).join('');

  document.getElementById('pe-body').innerHTML = kiniseis.length ? `
    <table style="width:100%;border-collapse:collapse;">
      <thead><tr style="background:var(--navy);color:white;">
        <th style="padding:8px 12px;text-align:left;font-size:11px;font-weight:600;letter-spacing:.8px;">Τύπος</th>
        <th style="padding:8px 12px;text-align:left;font-size:11px;font-weight:600;letter-spacing:.8px;">Ημ/νία</th>
        <th style="padding:8px 12px;text-align:right;font-size:11px;font-weight:600;letter-spacing:.8px;">Ποσότητα</th>
        <th style="padding:8px 12px;text-align:left;font-size:11px;font-weight:600;letter-spacing:.8px;">Υπογραφή</th>
      </tr></thead>
      <tbody>${rows}</tbody>
    </table>` : '<p style="color:var(--muted);text-align:center;padding:20px;">Δεν βρέθηκαν κινήσεις</p>';

  document.getElementById('parst-edit-modal').classList.add('open');
}

export function closeParstEditModal() {
  document.getElementById('parst-edit-modal').classList.remove('open');
}

export async function saveParstEdit() {
  const _unlock = _lock(event?.target);
  try {
    for (const k of _peKiniseis) {
      const posotita  = parseFloat(document.getElementById(`pe-pos-${k.id}`).value);
      const imerominia = document.getElementById(`pe-date-${k.id}`).value;
      const ypografi  = document.getElementById(`pe-ypografi-${k.id}`).value;
      if (!imerominia || isNaN(posotita) || posotita <= 0) {
        alert('Ελέγξτε ημερομηνία και ποσότητα.');
        return;
      }
      await py('update_kinisi', {
        id: k.id, imerominia, tipos: k.tipos, yliko_id: k.yliko_id,
        posotita, arithmos_parstatikos: k.arithmos_parstatikos,
        adeia_id: k.adeia_id, promitheftis_id: k.promitheftis_id,
        paratirishis: k.paratirishis, ypografi
      });
    }
    closeParstEditModal();
    await loadKiniseis();
  } catch(e) { alert('Σφάλμα αποθήκευσης: ' + e.message); }
  finally { _unlock(); }
}

document.getElementById('parst-edit-modal').addEventListener('click', function(e) {
  if (e.target === this) closeParstEditModal();
});
