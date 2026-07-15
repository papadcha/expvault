import { escapeHtml, py, fmtDate, _lock } from './utils.js';
import { allYlika, allAdeies, setYlika, setAdeies } from './state.js';
import { confirmDelete } from './delete-confirm.js';

// ── ΑΔΕΙΕΣ ───────────────────────────────────────────────────────────────────
export async function loadAdeies() {
  if (!allYlika.length) setYlika(await py('get_ylika'));
  setAdeies(await py('get_adeies'));
  // Γέμισμα dropdown υλικών στη φόρμα άδειας
  const ylikoSel = document.getElementById('adeia-yliko-new');
  if (ylikoSel) {
    ylikoSel.innerHTML = '<option value="">— Επιλογή —</option>' +
      allYlika.map(y => `<option value="${y.id}">${escapeHtml(y.onoma)}${y.diatomi_mm?` (${escapeHtml(y.diatomi_mm)}mm)`:''} — ${escapeHtml(y.monada_metrisis)}</option>`).join('');
  }
  const body=document.getElementById('adeia-body');
  body.innerHTML=allAdeies.map(a=>`<tr style="cursor:pointer" data-id="${a.id}">
    <td><strong>${escapeHtml(a.arithmos_adeias)}</strong></td><td>${escapeHtml(a.perigrafi)||'—'}</td><td>${escapeHtml(a.syntomografia_ekdousas)||'—'}</td>
    <td style="white-space:nowrap">${a.imerominia_lixis ? fmtDate(a.imerominia_lixis) : '—'}</td>
  </tr>`).join('')||'<tr><td colspan="4" style="padding:20px;color:var(--muted)">Δεν υπάρχουν</td></tr>';
  body.querySelectorAll('tr[data-id]').forEach(tr => {
    tr.addEventListener('click', () => {
      const a = allAdeies.find(x => x.id === parseInt(tr.dataset.id));
      if (a) fillAdeiaForm(a);
    });
  });
  renderAdeiaExpiryBadge(computeAdeiaExpiry(allAdeies));
}

// ── ΆΔΕΙΕΣ: ΥΠΕΝΘΥΜΙΣΗ ΛΗΞΗΣ ─────────────────────────────────────────────────
// Παράθυρο εντός του οποίου μια άδεια θεωρείται "προς λήξη" (μετράει στο badge).
const ADEIA_EXPIRY_WARNING_DAYS = 90;
// Εντός αυτού του παραθύρου (ή ήδη ληγμένη) εμφανίζεται και toast στην εκκίνηση.
const ADEIA_EXPIRY_TOAST_DAYS = 30;

// Υπολογίζει τις ημέρες μέχρι λήξη για κάθε άδεια με ημ. λήξης, ταξινομημένες
// από την πιο επείγουσα (ή ήδη ληγμένη) προς την πιο μακρινή.
function computeAdeiaExpiry(adeies, warningDays = ADEIA_EXPIRY_WARNING_DAYS) {
  const today = new Date(); today.setHours(0, 0, 0, 0);
  return adeies
    .filter(a => a.imerominia_lixis)
    .map(a => {
      const lixi = new Date(a.imerominia_lixis + 'T00:00:00');
      const days_left = Math.round((lixi - today) / 86400000);
      return { ...a, days_left };
    })
    .filter(a => a.days_left <= warningDays)
    .sort((a, b) => a.days_left - b.days_left);
}

function renderAdeiaExpiryBadge(rows) {
  const badge = document.getElementById('adeies-expiry-badge');
  if (!badge) return;
  if (!rows.length) { badge.style.display = 'none'; return; }
  const worst = rows[0].days_left;
  const cls = worst <= 15 ? 'nav-badge-urgent' : worst <= 30 ? 'nav-badge-warn' : 'nav-badge-notice';
  badge.className = 'nav-badge ' + cls;
  badge.textContent = rows.length;
  badge.style.display = 'inline-flex';
}

function adeiaExpiryMessage(a) {
  if (a.days_left < 0) return `🔴 Άδεια ${a.arithmos_adeias} ΕΛΗΞΕ στις ${fmtDate(a.imerominia_lixis)} (πριν ${-a.days_left} ημέρες)`;
  if (a.days_left === 0) return `🔴 Άδεια ${a.arithmos_adeias} λήγει ΣΗΜΕΡΑ (${fmtDate(a.imerominia_lixis)})`;
  return `⏰ Άδεια ${a.arithmos_adeias} λήγει σε ${a.days_left} ημέρες (${fmtDate(a.imerominia_lixis)})`;
}

// Έλεγχος λήξης αδειών κατά την εκκίνηση: ενημερώνει το badge και δείχνει toast
// για όσες λήγουν σύντομα ή έχουν ήδη λήξει.
export async function checkAdeiaExpiryOnStartup() {
  try {
    const adeies = await py('get_adeies');
    const rows = computeAdeiaExpiry(adeies);
    renderAdeiaExpiryBadge(rows);
    rows.filter(a => a.days_left <= ADEIA_EXPIRY_TOAST_DAYS)
      .forEach(a => window._showToast?.(adeiaExpiryMessage(a), a.days_left < 0 ? 'error' : 'warn'));
  } catch (e) {
    console.error('[Adeia Expiry] startup check failed:', e);
  }
}

export async function fillAdeiaForm(a) {
  document.getElementById('adeia-edit-id').value=a.id;
  document.getElementById('adeia-form-title').textContent='Επεξεργασία Άδειας';
  document.getElementById('adeia-num').value=a.arithmos_adeias;
  document.getElementById('adeia-syntomografia').value=a.syntomografia_ekdousas||'';
  document.getElementById('adeia-perigrafi').value=a.perigrafi||'';
  document.getElementById('adeia-ekdosi').value=a.imerominia_ekdosis||'';
  document.getElementById('adeia-lixis').value=a.imerominia_lixis||'';
  document.getElementById('adeia-del-btn').style.display='inline-flex';
  document.getElementById('adeia-ylika-section').style.display='';
  await loadAdeiaYlika(a.id);
}

export async function loadAdeiaYlika(adeia_id) {
  const rows = await py('get_adeia_ylika', { adeia_id });
  const tbody = document.getElementById('adeia-ylika-body');
  if (!rows.length) {
    tbody.innerHTML = '<tr><td colspan="5" style="color:var(--muted);padding:6px 0;font-size:12px;">Δεν υπάρχουν εγκεκριμένες ποσότητες</td></tr>';
    return;
  }
  tbody.innerHTML = rows.map(r => {
    const yp = r.egekrimeni_posotita - r.xrisimopoiimeni;
    const ypCls = yp < 0 ? 'color:#c53030;font-weight:600' : yp === 0 ? 'color:#276749' : '';
    return `<tr>
      <td>${escapeHtml(r.nomiki_katigoria)}</td>
      <td class="text-right mono">${r.egekrimeni_posotita.toFixed(3)} ${escapeHtml(r.monada_metrisis)}</td>
      <td class="text-right mono">${r.xrisimopoiimeni.toFixed(3)}</td>
      <td class="text-right mono" style="${ypCls}">${yp.toFixed(3)}</td>
      <td><button class="btn btn-danger btn-sm" style="padding:2px 6px;" onclick="removeAdeiaYliko(${r.id},${r.adeia_id})">✖</button></td>
    </tr>`;
  }).join('');
}

export async function addAdeiaYliko() {
  const adeia_id        = parseInt(document.getElementById('adeia-edit-id').value);
  const nomiki_katigoria = document.getElementById('adeia-katigoria-new').value;
  const posotita        = parseFloat(document.getElementById('adeia-posotita-new').value);
  if (!adeia_id || !nomiki_katigoria || isNaN(posotita) || posotita <= 0) {
    alert('Επιλέξτε κατηγορία και εισάγετε έγκυρη ποσότητα.'); return;
  }
  await py('set_adeia_katigoria', { adeia_id, nomiki_katigoria, egekrimeni_posotita: posotita });
  document.getElementById('adeia-katigoria-new').value = '';
  document.getElementById('adeia-posotita-new').value = '';
  await loadAdeiaYlika(adeia_id);
}

export async function removeAdeiaYliko(id, adeia_id) {
  await py('delete_adeia_yliko', { id });
  await loadAdeiaYlika(adeia_id);
}

export async function saveAdeia() {
  const id=document.getElementById('adeia-edit-id').value;
  const body={
    arithmos_adeias: document.getElementById('adeia-num').value.trim(),
    perigrafi:       document.getElementById('adeia-perigrafi').value,
    syntomografia_ekdousas: document.getElementById('adeia-syntomografia').value.trim()||null,
    imerominia_ekdosis: document.getElementById('adeia-ekdosi').value||null,
    imerominia_lixis:   document.getElementById('adeia-lixis').value||null,
  };
  if (!body.arithmos_adeias) { alert('Ο αριθμός άδειας είναι υποχρεωτικός.'); return; }
  const _unlock = _lock(event?.target);
  try {
    if (id) {
      await py('update_adeia', { id: parseInt(id), ...body });
    } else {
      const r = await py('add_adeia', body);
      // Φόρτωσε αυτόματα για να εμφανιστεί το section ποσοτήτων
      document.getElementById('adeia-edit-id').value = r.id;
      document.getElementById('adeia-form-title').textContent = 'Επεξεργασία Άδειας';
      document.getElementById('adeia-del-btn').style.display = 'inline-flex';
      document.getElementById('adeia-ylika-section').style.display = '';
      await loadAdeiaYlika(r.id);
    }
    loadAdeies();
  } catch(e) { alert('Σφάλμα: '+e.message); }
  finally { _unlock(); }
}

export async function deleteAdeia() {
  const id=document.getElementById('adeia-edit-id').value;
  if (id) confirmDelete('adeia',id);
}

export function clearAdeiaForm() {
  document.getElementById('adeia-edit-id').value='';
  document.getElementById('adeia-form-title').textContent='Νέα Άδεια';
  ['adeia-num','adeia-perigrafi','adeia-syntomografia','adeia-ekdosi','adeia-lixis'].forEach(id => {
    document.getElementById(id).value='';
  });
  document.getElementById('adeia-del-btn').style.display='none';
  document.getElementById('adeia-ylika-section').style.display='none';
  document.getElementById('adeia-ylika-body').innerHTML='';
}
