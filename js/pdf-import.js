import { escapeHtml, py } from './utils.js';
import { allYlika, allProm, allAdeies, setYlika, setProm, setAdeies } from './state.js';

// ── PDF IMPORT ────────────────────────────────────────────────────────────────

// Κοινό preview/edit UI για ό,τι επιστρέφει parse_pdf ή parse_import_data —
// ίδιο σχήμα { raw_text, suggested: {imerominia, tipos, arithmos_parstatikos,
// adeia, ekdousa_archi, promitheftis, grammes[]}, template_used }.
function _populatePdfForm(r) {
  document.getElementById('pdf-raw-text').textContent = r.raw_text || '(Δεν εξήχθη κείμενο)';
  document.getElementById('pdf-results').style.display = 'block';
  document.getElementById('pdf-alert').innerHTML = '';
  window._lastEpistrofiParst = null;
  const s = r.suggested;
  // Hint από το ίδιο το παραστατικό (πεδίο agora_ref, βλ. IMPORT_DATA_PROMPT) —
  // used στο submitPdfEntries() για σωστό matching αγοράς/επιστροφής σε batch.
  window._pdfSuggestedAgoraRef = s.agora_ref || '';
  if (s.imerominia && typeof s.imerominia === 'string') {
    const [d,m,y] = s.imerominia.split('/');
    document.getElementById('pdf-imerominia').value = y && m && d ? `${y}-${m.padStart(2,'0')}-${d.padStart(2,'0')}` : '';
  }
  document.getElementById('pdf-tipos').value   = s.tipos || 'ΕΙΣΑΓΩΓΗ';
  document.getElementById('pdf-parstatiko').value = s.arithmos_parstatikos||'';
  document.getElementById('pdf-adeia-txt').value  = s.adeia||'';
  document.getElementById('pdf-ekdousa-txt').value = s.ekdousa_archi||'';
  document.getElementById('pdf-prom-txt').value   = s.promitheftis||'';
  const container = document.getElementById('pdf-grammes-container');
  if (s.grammes.length) {
    container.innerHTML = '<div class="card-title" style="margin-top:16px;margin-bottom:10px;">Αναγνωρισμένα Υλικά</div>' +
      s.grammes.map((g,i)=>`
        <div class="form-row cols-3" style="margin-bottom:8px;">
          <div><label>Υλικό ${i+1}</label><input type="text" id="pdf-g-onoma-${i}" value="${escapeHtml(g.onoma)}"></div>
          <div><label>Ποσότητα</label><input type="number" id="pdf-g-pos-${i}" value="${escapeHtml(g.posotita)}" step="0.001"></div>
          <div><label>Μονάδα</label>
            <select id="pdf-g-mon-${i}">
              <option ${g.monada==='Κιλ'?'selected':''}>Κιλ</option>
              <option ${g.monada==='Τεμ'?'selected':''}>Τεμ</option>
              <option ${g.monada==='Μετρ'?'selected':''}>Μετρ</option>
            </select>
          </div>
        </div>`).join('');
  } else {
    container.innerHTML = '<div style="padding:12px;color:var(--muted);font-size:13px;">⚠️ Δεν αναγνωρίστηκαν αυτόματα υλικά. Συμπληρώστε χειροκίνητα.</div>';
  }
  if (r.template_used) {
    window._showToast(`✅ Χρησιμοποιήθηκε πρότυπο: ${r.template_used}`, 'success');
  }
  window.pdfGrammesCount = s.grammes.length;
}

function _clearImportQueue() {
  window._importQueue = [];
  window._importQueueIndex = 0;
  window._importErrors = [];
  const bar = document.getElementById('import-queue-bar');
  if (bar) bar.style.display = 'none';
}

export async function parsePdf() {
  const status = document.getElementById('pdf-status');
  status.textContent = '⏳ Επιλογή αρχείου...';
  const filePath = await window.api.openFile();
  if (!filePath) { status.textContent = ''; return; }
  status.textContent = '⏳ Ανάλυση...';
  try {
    const r = await py('parse_pdf', { path: filePath });
    status.textContent = '';
    _clearImportQueue();
    _populatePdfForm(r);
  } catch(e) { status.textContent = ''; alert('Σφάλμα: ' + e.message); }
}

// Εναλλακτικό στο PDF parsing: JSON/CSV που παρήγαγε εξωτερικό LLM (π.χ.
// upload φωτογραφίας τιμολογίου σε Claude/Gemini free web UI) — βλ.
// IMPORT_DATA_PROMPT για το prompt που δίνει στον χειριστή το σωστό σχήμα.
// Ένα αρχείο (ή φάκελος/zip) μπορεί να περιέχει πολλά παραστατικά — γίνονται
// review/submit ΕΝΑ-ΕΝΑ μέσα από την ίδια φόρμα, με το "Επόμενο Παραστατικό".
function _loadImportResult(r) {
  window._importQueue  = r.items || [];
  window._importErrors = r.errors || [];
  if (!window._importQueue.length) {
    const errTxt = window._importErrors.length
      ? '\n' + window._importErrors.map(e => `${e.source}: ${e.error}`).join('\n')
      : '';
    alert('Δεν βρέθηκε κανένα έγκυρο παραστατικό.' + errTxt);
    return;
  }
  _showImportQueueItem(0);
}

function _showImportQueueItem(i) {
  const queue = window._importQueue;
  window._importQueueIndex = i;
  _populatePdfForm(queue[i]);

  const bar = document.getElementById('import-queue-bar');
  const showBar = queue.length > 1 || window._importErrors.length > 0;
  bar.style.display = showBar ? 'flex' : 'none';
  if (!showBar) return;

  document.getElementById('import-queue-pos').textContent =
    `Παραστατικό ${i+1} από ${queue.length}` + (queue[i].source ? ` — ${queue[i].source}` : '');
  document.getElementById('import-queue-next-btn').style.display = i < queue.length - 1 ? '' : 'none';

  const errBox = document.getElementById('import-queue-errors');
  if (window._importErrors.length) {
    errBox.style.display = '';
    errBox.innerHTML = '⚠️ Απέτυχαν: ' + window._importErrors.map(e => `${escapeHtml(e.source)} (${escapeHtml(e.error)})`).join(', ');
  } else {
    errBox.style.display = 'none';
  }
}

export function nextImportQueueItem() {
  const queue = window._importQueue || [];
  const next = (window._importQueueIndex || 0) + 1;
  if (next < queue.length) _showImportQueueItem(next);
}

export async function parseImportData() {
  const status = document.getElementById('pdf-status');
  status.textContent = '⏳ Επιλογή αρχείου...';
  const filePath = await window.api.openImportData();
  if (!filePath) { status.textContent = ''; return; }
  status.textContent = '⏳ Ανάλυση...';
  try {
    const r = await py('parse_import_data', { path: filePath });
    status.textContent = '';
    _loadImportResult(r);
  } catch(e) { status.textContent = ''; alert('Σφάλμα: ' + e.message); }
}

export async function parseImportFolder() {
  const status = document.getElementById('pdf-status');
  status.textContent = '⏳ Επιλογή φακέλου...';
  const dirPath = await window.api.openImportFolder();
  if (!dirPath) { status.textContent = ''; return; }
  status.textContent = '⏳ Ανάλυση...';
  try {
    const r = await py('parse_import_data', { path: dirPath });
    status.textContent = '';
    _loadImportResult(r);
  } catch(e) { status.textContent = ''; alert('Σφάλμα: ' + e.message); }
}

const IMPORT_DATA_PROMPT = `Ανάλυσε αυτή τη φωτογραφία τιμολογίου/δελτίου εκρηκτικών υλών και απάντησε ΜΟΝΟ με το παρακάτω JSON (χωρίς άλλο κείμενο πριν/μετά):

{
  "imerominia": "ΗΗ/ΜΜ/ΕΕΕΕ",
  "tipos": "ΕΙΣΑΓΩΓΗ ή ΕΠΙΣΤΡΟΦΗ",
  "arithmos_parstatikou": "ο αριθμός του παραστατικού όπως αναγράφεται",
  "adeia": "ο αριθμός άδειας αγοράς/εκμετάλλευσης, αν αναφέρεται",
  "ekdousa_archi": "η εκδούσα αρχή της άδειας, αν αναφέρεται",
  "promitheftis": "το όνομα του προμηθευτή/εταιρείας",
  "agora_ref": "ΜΟΝΟ αν tipos=ΕΠΙΣΤΡΟΦΗ και το παραστατικό αναφέρει τον αριθμό του αρχικού τιμολογίου αγοράς που αφορά — αλλιώς άσε κενό",
  "grammes": [
    { "onoma": "όνομα υλικού με ΚΕΦΑΛΑΙΑ όπως στο πρωτότυπο", "posotita": αριθμός, "monada": "Κιλ ή Τεμ ή Μετρ" }
  ]
}`;

export async function copyImportDataPrompt() {
  try {
    await navigator.clipboard.writeText(IMPORT_DATA_PROMPT);
    window._showToast('✅ Το prompt αντιγράφηκε — επικόλλησέ το στο Claude/Gemini μαζί με τη φωτογραφία', 'success');
  } catch(e) {
    alert('Δεν ήταν δυνατή η αντιγραφή: ' + e.message);
  }
}

export async function submitPdfEntries() {
  const imerominia = document.getElementById('pdf-imerominia').value;
  const tipos      = document.getElementById('pdf-tipos').value;
  const parstatiko = document.getElementById('pdf-parstatiko').value;
  const adeiaNum    = document.getElementById('pdf-adeia-txt').value.trim();
  const ekdousaArchi = document.getElementById('pdf-ekdousa-txt').value.trim();
  const promName   = document.getElementById('pdf-prom-txt').value.trim();
  if (!imerominia) { alert('Συμπληρώστε ημερομηνία.'); return; }
  if (!window.pdfGrammesCount) { alert('Δεν υπάρχουν γραμμές υλικών.'); return; }

  // Έλεγχος διπλοεγγραφής παραστατικού
  if (parstatiko) {
    const existing = await py('check_parstatiko', { arithmos_parstatikos: parstatiko });
    if (existing.length > 0) {
      showDiploModal(parstatiko, existing);
      return;
    }
  }

  let promId = null;
  if (promName) {
    let p = allProm.find(x=>x.onoma.toLowerCase()===promName.toLowerCase());
    if (!p) {
      try { await py('add_promitheftis', {onoma: promName}); } catch(e) {}
      setProm(await py('get_promitheftes'));
      p = allProm.find(x=>x.onoma.toLowerCase()===promName.toLowerCase());
    }
    promId = p?.id || null;
  }

  let adeiaId = null;
  if (adeiaNum) {
    let a = allAdeies.find(x=>x.arithmos_adeias===adeiaNum);
    if (!a) {
      try { await py('add_adeia', {arithmos_adeias: adeiaNum, perigrafi: ekdousaArchi||null}); } catch(e) {}
      setAdeies(await py('get_adeies'));
      a = allAdeies.find(x=>x.arithmos_adeias===adeiaNum);
    }
    adeiaId = a?.id || null;
  }

  let saved = 0, errors = [];
  for (let i=0; i<window.pdfGrammesCount; i++) {
    const onoma = document.getElementById(`pdf-g-onoma-${i}`)?.value?.trim().toUpperCase();
    const pos   = parseFloat(document.getElementById(`pdf-g-pos-${i}`)?.value);
    const mon   = document.getElementById(`pdf-g-mon-${i}`)?.value;
    if (!onoma || isNaN(pos)) continue;
    let yliko = allYlika.find(y=>y.onoma===onoma);
    if (!yliko) {
      try { await py('add_yliko', {onoma, monada_metrisis:mon, paratirishis:'Αυτόματη εισαγωγή PDF'}); } catch(e) {}
      setYlika(await py('get_ylika'));
      yliko = allYlika.find(y=>y.onoma===onoma);
    }
    if (!yliko) { errors.push(onoma+': δεν βρέθηκε'); continue; }
    try {
      await py('add_kinisi', {imerominia, tipos, yliko_id:yliko.id,
        posotita:pos, arithmos_parstatikos:parstatiko,
        adeia_id:adeiaId, promitheftis_id:promId, paratirishis:'Εισαγωγή από PDF'});
      saved++;
    } catch(e) { errors.push(onoma+': '+e.message); }
  }
  const alertEl = document.getElementById('pdf-alert');
  alertEl.innerHTML = '';
  if (errors.length) alertEl.innerHTML += `<div class="alert alert-error">Σφάλματα: ${escapeHtml(errors.join(', '))}</div>`;
  if (saved) {
    alertEl.innerHTML += `<div class="alert alert-success">✅ Καταχωρήθηκαν ${saved} γραμμές!</div>`;

    if (tipos === 'ΕΠΙΣΤΡΟΦΗ') {
      // ── ΕΠΙΣΤΡΟΦΗ: ζήτα το συσχετιζόμενο τιμολόγιο αγοράς ──
      window._lastEpistrofiParst = parstatiko; // αποθήκευση πριν καθαριστεί
      // Προτίμηση στο ρητό agora_ref του ίδιου του παραστατικού (αν υπάρχει —
      // βλ. import_data.py) έναντι της ευρετικής "τελευταία αγορά που
      // καταχωρήθηκε", που είναι αναξιόπιστη σε batch import με πολλές αγορές
      // στην ουρά (θα έδειχνε πάντα την τελευταία, όχι απαραίτητα τη σωστή).
      const lastAgora = window._pdfSuggestedAgoraRef ? null : await py('get_last_eisagogi_parstatiko', {});
      const lastParst = window._pdfSuggestedAgoraRef || lastAgora?.arithmos_parstatikos || '';
      alertEl.innerHTML += `
        <div class="alert" style="background:#fff3cd;border:1px solid #ffc107;color:#856404;margin-top:8px;">
          <strong>⚠️ Βήμα 2: Συσχέτισε με τιμολόγιο αγοράς</strong>
          <div style="margin:8px 0;font-size:13px;">Ποιο τιμολόγιο αγοράς αφορά η επιστροφή <strong>${escapeHtml(parstatiko)}</strong>;</div>
          <div style="display:flex;gap:8px;align-items:center;margin-top:8px;">
            <input type="text" id="ekk-parst-input" value="${escapeHtml(lastParst)}"
              style="flex:1;padding:6px 10px;border:1px solid #ffc107;border-radius:4px;font-size:13px;"
              placeholder="π.χ. ΔΙΧΝ - 19586">
            <button class="btn btn-sm btn-accent" onclick="checkEkkremotitaByParst()">🔍 Έλεγχος</button>
          </div>
        </div>`;
    } else {
      // ── ΕΙΣΑΓΩΓΗ: ρώτα αν υπάρχει επιστροφή ──
      alertEl.innerHTML += `
        <div class="alert" style="background:#e8f4fd;border:1px solid #90cdf4;color:#2b6cb0;margin-top:8px;" id="ekk-eisagogi-prompt">
          <strong>📋 Βήμα 2: Έχεις επιστροφή για το <em>${escapeHtml(parstatiko)}</em>;</strong>
          <div style="display:flex;gap:8px;margin-top:10px;">
            <button class="btn btn-sm btn-outline" data-ekk-wait="${escapeHtml(parstatiko)}">🔄 ΝΑΙ — Θα περάσω πιστωτικό</button>
            <button class="btn btn-sm btn-success" data-ekk-auto="${escapeHtml(parstatiko)}">✅ ΟΧΙ — Καταχώρηση Κατανάλωσης</button>
          </div>
        </div>`;
      document.querySelector('[data-ekk-wait]')?.addEventListener('click', function() { showEkkEisagogiWait(this.dataset.ekkWait); });
      document.querySelector('[data-ekk-auto]')?.addEventListener('click', function() { doAutoKataxorisiEisagogi(this.dataset.ekkAuto); });
    }
  }
}

export function showEkkEisagogiWait(parstatiko) {
  const alertEl = document.getElementById('pdf-alert');
  alertEl.innerHTML += `
    <div class="alert" style="background:#e8f4fd;border:1px solid #90cdf4;color:#2b6cb0;margin-top:8px;">
      ℹ️ Πέρασε το πιστωτικό τιμολόγιο — μετά η εφαρμογή θα σε καθοδηγήσει για την κατανάλωση του <strong>${escapeHtml(parstatiko)}</strong>.
    </div>`;
  document.getElementById('ekk-eisagogi-prompt')?.remove();
}

export async function doAutoKataxorisiEisagogi(parstatiko) {
  // Παίρνει ΟΛΕΣ τις γραμμές ΕΙΣΑΓΩΓΗΣ του παραστατικού
  // Κατανάλωση = ολόκληρη η αγορά (οι επιστροφές αφαιρούνται μετά ξεχωριστά)
  const kiniseis = await py('get_kiniseis', {});
  const eisagogi = kiniseis.filter(k => k.tipos === 'ΕΙΣΑΓΩΓΗ' && k.arithmos_parstatikos === parstatiko);

  if (!eisagogi.length) {
    const alertEl = document.getElementById('pdf-alert');
    alertEl.innerHTML += `<div class="alert" style="background:#c6f6d5;border:1px solid #68d391;color:#276749;margin-top:8px;">✅ Δεν βρέθηκαν γραμμές αγοράς για <strong>${escapeHtml(parstatiko)}</strong>.</div>`;
    document.getElementById('ekk-eisagogi-prompt')?.remove();
    return;
  }

  // Μετατροπή σε ekkData format
  // Χρήση ημερομηνίας αγοράς — η πρώτη imerominia από τις γραμμές ΕΙΣΑΓΩΓΗΣ
  const agoraImerominia = eisagogi[0]?.imerominia || '';
  window._ekkData = eisagogi.map(k => ({
    yliko_id:   k.yliko_id,
    yliko_onoma: k.yliko_onoma,
    monada:     k.monada_metrisis,
    posotita:   k.posotita,
    imerominia: agoraImerominia,
    tipo:       'ΚΑΤΑΝΑΛΩΣΗ'
  }));
  window._ekkParstatiko = parstatiko;
  window._ekkImerominia = agoraImerominia;
  document.getElementById('ekk-eisagogi-prompt')?.remove();

  const lines = window._ekkData.map(e => {
    const fmt = e.posotita.toFixed(3).replace('.',',');
    return `<div>• 🔥 <strong>${escapeHtml(e.yliko_onoma)}</strong>: ${fmt} ${escapeHtml(e.monada)}</div>`;
  }).join('');
  const alertEl = document.getElementById('pdf-alert');
  alertEl.innerHTML += `
    <div class="alert" style="background:#fff3cd;border:1px solid #ffc107;color:#856404;margin-top:8px;">
      <strong>🔥 Καταναλώσεις για <em>${escapeHtml(parstatiko)}</em>:</strong>
      <div style="margin:8px 0;font-size:12px;">${lines}</div>
      <button class="btn btn-sm btn-accent" onclick="autoKataxorisiAll()">✅ Καταχώρηση Κατανάλωσης</button>
    </div>`;
}

export function closeDiploModal() {
  document.getElementById('diplo-modal').classList.remove('open');
}

export function showDiploModal(parstatiko, existing) {
  window._diploParstatiko = parstatiko;
  document.getElementById('diplo-msg').textContent =
    `Το παραστατικό "${parstatiko}" έχει ήδη καταχωρηθεί:`;
  document.getElementById('diplo-list').innerHTML = existing.map(e =>
    `<div>• ${escapeHtml(e.yliko_onoma)}: ${e.posotita.toFixed(3)} ${escapeHtml(e.monada_metrisis)} (${escapeHtml(e.imerominia)})</div>`
  ).join('');
  document.getElementById('diplo-modal').classList.add('open');
}

export async function deleteParstatiko() {
  const parstatiko = window._diploParstatiko;
  if (!parstatiko) return;
  try {
    await py('delete_kiniseis_by_parstatiko', { arithmos_parstatikos: parstatiko });
    closeDiploModal();
    // Συνέχισε αυτόματα με την καταχώρηση
    await submitPdfEntries();
  } catch(e) { alert('Σφάλμα διαγραφής: ' + e.message); }
}

// ── ΕΚΚΡΕΜΟΤΗΤΑ ΑΝΑ ΠΑΡΑΣΤΑΤΙΚΟ ────────────────────────────────────────────
export async function checkEkkremotitaByParst() {
  const parst = document.getElementById('ekk-parst-input')?.value?.trim();
  if (!parst) { alert('Εισάγετε παραστατικό αγοράς'); return; }

  // Αποθήκευση agora_ref στις γραμμές της επιστροφής
  const epistrofiParst = window._lastEpistrofiParst || document.getElementById('pdf-parstatiko')?.value?.trim() || '';
  if (epistrofiParst) {
    await py('update_agora_ref', { arithmos_parstatikos: epistrofiParst, agora_ref: parst });
  }
  const r = await py('check_ekkremotita', { parstatiko: parst });
  const alertEl = document.getElementById('pdf-alert');

  if (!r.ekkremotita || !r.ekkremes?.length) {
    alertEl.innerHTML += `
      <div class="alert" style="background:#c6f6d5;border:1px solid #68d391;color:#276749;margin-top:8px;">
        ✅ Πλήρης επιστροφή — δεν απαιτείται κατανάλωση για <strong>"${escapeHtml(parst)}"</strong>.
      </div>`;
    return;
  }

  window._ekkData = r.ekkremes;
  window._ekkParstatiko = parst;
  // Ημερομηνία κατανάλωσης = ημερομηνία αγοράς
  window._ekkImerominia = r.ekkremes[0]?.imerominia || '';
  const lines = r.ekkremes.map(e => {
    const fmt = e.posotita.toFixed(3).replace('.',',');
    return `<div>• 🔥 <strong>${escapeHtml(e.yliko_onoma)}</strong>: ${fmt} ${escapeHtml(e.monada)}</div>`;
  }).join('');

  alertEl.innerHTML += `
    <div class="alert" style="background:#fff3cd;border:1px solid #ffc107;color:#856404;margin-top:8px;">
      <strong>🔥 Καταναλώσεις για <em>${escapeHtml(parst)}</em>:</strong>
      <div style="margin:8px 0;font-size:12px;">${lines}</div>
      <div style="display:flex;gap:8px;margin-top:8px;">
        <button class="btn btn-sm btn-accent" onclick="autoKataxorisiAll()">✅ Καταχώρηση Κατανάλωσης</button>
      </div>
    </div>`;
}
