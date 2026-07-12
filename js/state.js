import { escapeHtml, py } from './utils.js';

// ── STATE ─────────────────────────────────────────────────────────────────────
export let allYlika = [], allProm = [], allAdeies = [];

export function setYlika(arr) { allYlika = arr; }
export function setProm(arr) { allProm = arr; }
export function setAdeies(arr) { allAdeies = arr; }

// ── DROPDOWNS ─────────────────────────────────────────────────────────────────
export async function loadDropdowns() {
  [allYlika, allProm, allAdeies] = await Promise.all([
    py('get_ylika'),
    py('get_promitheftes'),
    py('get_adeies')
  ]);
  fillYlikoSelects();
  fillPromSelects();
  fillAdeiesSelects();
  await fillAgoraDatalist();
}

export async function fillAgoraDatalist() {
  const kiniseis = await py('get_kiniseis', { tipos: 'ΕΙΣΑΓΩΓΗ' });
  const parst = [...new Set(
    kiniseis.filter(k => k.arithmos_parstatikos).map(k => k.arithmos_parstatikos)
  )].sort();
  const opts = parst.map(p => `<option value="${escapeHtml(p)}">`).join('');
  ['kin-agora-datalist', 'ek-agora-datalist'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.innerHTML = opts;
  });
}

export function ylikoLabel(y) { return escapeHtml(y.onoma) + (y.diatomi_mm ? ` (${escapeHtml(y.diatomi_mm)}mm)` : '') + ` — ${escapeHtml(y.monada_metrisis)}`; }

export function fillYlikoSelects() {
  const opts = allYlika.map(y => `<option value="${y.id}">${ylikoLabel(y)}</option>`).join('');
  ['kin-yliko','flt-yliko'].forEach(id => {
    const el = document.getElementById(id);
    if (!el) return;
    const prev = el.value;
    el.innerHTML = (id==='flt-yliko'?'<option value="">Όλα</option>':'<option value="">— Επιλογή —</option>') + opts;
    if (prev) el.value = prev;
  });
}
export function fillPromSelects() {
  const opts = '<option value="">— Κανένας —</option>' + allProm.map(p=>`<option value="${p.id}">${escapeHtml(p.onoma)}</option>`).join('');
  const el = document.getElementById('kin-prom');
  if (el) { const v=el.value; el.innerHTML=opts; if(v) el.value=v; }
}
export function fillAdeiesSelects() {
  const opts = '<option value="">— Καμία —</option>' + allAdeies.map(a=>`<option value="${a.id}">${escapeHtml(a.arithmos_adeias)}</option>`).join('');
  const el = document.getElementById('kin-adeia');
  if (el) { const v=el.value; el.innerHTML=opts; if(v) el.value=v; }
}
