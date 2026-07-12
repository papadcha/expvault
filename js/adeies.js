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
  body.innerHTML=allAdeies.map(a=>`<tr style="cursor:pointer" onclick='fillAdeiaForm(${escapeHtml(JSON.stringify(a))})'>
    <td><strong>${escapeHtml(a.arithmos_adeias)}</strong></td><td>${escapeHtml(a.perigrafi)||'—'}</td><td>${escapeHtml(a.syntomografia_ekdousas)||'—'}</td>
    <td style="white-space:nowrap">${a.imerominia_lixis ? fmtDate(a.imerominia_lixis) : '—'}</td>
  </tr>`).join('')||'<tr><td colspan="4" style="padding:20px;color:var(--muted)">Δεν υπάρχουν</td></tr>';
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
