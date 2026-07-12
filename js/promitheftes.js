import { escapeHtml, py, _lock } from './utils.js';
import { allProm, setProm } from './state.js';
import { confirmDelete } from './delete-confirm.js';

// ── ΠΡΟΜΗΘΕΥΤΕΣ ──────────────────────────────────────────────────────────────
export async function loadProm() {
  setProm(await py('get_promitheftes'));
  const body = document.getElementById('prom-body');
  body.innerHTML = allProm.map(p=>`<tr style="cursor:pointer" onclick='fillPromForm(${escapeHtml(JSON.stringify(p))})'>
    <td>${escapeHtml(p.onoma)}</td>
  </tr>`).join('') || '<tr><td style="padding:20px;color:var(--muted)">Δεν υπάρχουν</td></tr>';
}

export function fillPromForm(p) {
  document.getElementById('prom-edit-id').value=p.id;
  document.getElementById('prom-form-title').textContent='Επεξεργασία Προμηθευτή';
  document.getElementById('prom-onoma').value=p.onoma;
  document.getElementById('prom-syntomografia').value=p.syntomografia||'';
  document.getElementById('prom-del-btn').style.display='inline-flex';
}

export async function saveProm() {
  const id=document.getElementById('prom-edit-id').value;
  const body={onoma:document.getElementById('prom-onoma').value.trim(), syntomografia:document.getElementById('prom-syntomografia').value.trim()||null};
  if (!body.onoma) { alert('Το όνομα είναι υποχρεωτικό.'); return; }
  const _unlock = _lock(event?.target);
  try {
    if (id) await py('update_promitheftis', { id: parseInt(id), ...body });
    else     await py('add_promitheftis', body);
    clearPromForm(); loadProm();
  } catch(e) { alert('Σφάλμα: '+e.message); }
  finally { _unlock(); }
}

export async function deleteProm() {
  const id=document.getElementById('prom-edit-id').value;
  if (id) confirmDelete('prom',id);
}

export function clearPromForm() {
  document.getElementById('prom-edit-id').value='';
  document.getElementById('prom-form-title').textContent='Νέος Προμηθευτής';
  document.getElementById('prom-onoma').value='';
  document.getElementById('prom-syntomografia').value='';
  document.getElementById('prom-del-btn').style.display='none';
}
