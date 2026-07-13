import { escapeHtml, py, _lock } from './utils.js';
import { allYlika, setYlika } from './state.js';
import { confirmDelete } from './delete-confirm.js';

// ── ΥΛΙΚΑ ────────────────────────────────────────────────────────────────────
export async function loadYlika() {
  setYlika(await py('get_ylika'));
  const body = document.getElementById('yl-body');
  body.innerHTML = allYlika.map(y => `<tr style="cursor:pointer" data-id="${y.id}">
    <td><strong>${escapeHtml(y.onoma)}</strong></td>
    <td>${escapeHtml(y.diatomi_mm)||'—'}</td>
    <td>${escapeHtml(y.monada_metrisis)}</td>
    <td>${escapeHtml(y.nomiki_katigoria)||'—'}</td>
    <td>${escapeHtml(y.paratirishis)||'—'}</td>
  </tr>`).join('') || '<tr><td colspan="5" style="text-align:center;padding:24px;color:var(--muted)">Δεν υπάρχουν υλικά</td></tr>';
  body.querySelectorAll('tr[data-id]').forEach(tr => {
    tr.addEventListener('click', () => {
      const y = allYlika.find(x => x.id === parseInt(tr.dataset.id));
      if (y) fillYlikoForm(y);
    });
  });
}

export function fillYlikoForm(y) {
  document.getElementById('yl-edit-id').value = y.id;
  document.getElementById('yl-form-title').textContent = 'Επεξεργασία Υλικού';
  document.getElementById('yl-onoma').value = y.onoma;
  document.getElementById('yl-diatomi').value = y.diatomi_mm||'';
  document.getElementById('yl-monada').value = y.monada_metrisis;
  document.getElementById('yl-export-group').value = y.export_group||'';
  document.getElementById('yl-nomiki-katigoria').value = y.nomiki_katigoria||'';
  document.getElementById('yl-paratirishis').value = y.paratirishis||'';
  document.getElementById('yl-del-btn').style.display = 'inline-flex';
}

export async function saveYliko() {
  const id = document.getElementById('yl-edit-id').value;
  const body = {
    onoma: document.getElementById('yl-onoma').value.trim(),
      export_group: document.getElementById('yl-export-group').value.trim()||null,
    nomiki_katigoria: document.getElementById('yl-nomiki-katigoria').value.trim()||null,
    diatomi_mm: document.getElementById('yl-diatomi').value || null,
    monada_metrisis: document.getElementById('yl-monada').value,
    paratirishis: document.getElementById('yl-paratirishis').value
  };
  if (!body.onoma) { alert('Το όνομα είναι υποχρεωτικό.'); return; }
  const _unlock = _lock(event?.target);
  try {
    if (id) await py('update_yliko', { id: parseInt(id), ...body });
    else     await py('add_yliko', body);
    clearYlikoForm(); loadYlika();
  } catch(e) { alert('Σφάλμα: ' + e.message); }
  finally { _unlock(); }
}

export async function deleteYliko() {
  const id = document.getElementById('yl-edit-id').value;
  if (!id) return;
  confirmDelete('yliko', id);
}

export function clearYlikoForm() {
  document.getElementById('yl-edit-id').value='';
  document.getElementById('yl-form-title').textContent='Νέο Υλικό';
  ['yl-onoma','yl-diatomi','yl-export-group','yl-nomiki-katigoria','yl-paratirishis'].forEach(id=>document.getElementById(id).value='');
  document.getElementById('yl-del-btn').style.display='none';
}
