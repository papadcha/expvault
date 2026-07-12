import { escapeHtml, py, fmtDate } from './utils.js';

// ── DASHBOARD ─────────────────────────────────────────────────────────────────
export async function loadDashboard() {
  const [apo, kin] = await Promise.all([
    py('get_apothemates'),
    py('get_kiniseis')
  ]);

  document.getElementById('stat-kiniseis').textContent = kin.length;
  document.getElementById('stat-eisagogi').textContent = new Set(kin.filter(k=>k.tipos==='ΕΙΣΑΓΩΓΗ' && k.arithmos_parstatikos).map(k=>k.arithmos_parstatikos)).size;
  document.getElementById('stat-epistrofi').textContent = new Set(kin.filter(k=>k.tipos==='ΕΠΙΣΤΡΟΦΗ' && k.arithmos_parstatikos).map(k=>k.arithmos_parstatikos)).size;
  document.getElementById('stat-ylika').textContent    = apo.length;

  const apoBody = document.getElementById('dash-apo-body');
  apoBody.innerHTML = apo.length ? apo.map(r => {
    const yp = r.ypoloipo;
    const cls   = yp > 0 ? 'pos' : 'zero';
    const badge = yp > 0
      ? '<span class="badge badge-neg">⚠️ ΑΔΙΚΑΙΟΛΟΓΗΤΟ</span>'
      : '<span class="badge badge-ok">✅ ΟΚ</span>';
    return `<tr>
      <td><strong>${escapeHtml(r.onoma)}</strong>${r.diatomi_mm?` <small>(${escapeHtml(r.diatomi_mm)}mm)</small>`:''}</td>
      <td>${escapeHtml(r.monada_metrisis)}</td>
      <td class="text-right mono">${r.synolo_eisagogon.toFixed(3)}</td>
      <td class="text-right mono">${r.synolo_katanalosis.toFixed(3)}</td>
      <td class="text-right mono">${r.synolo_epistrofon.toFixed(3)}</td>
      <td class="text-right ${cls}">${yp.toFixed(3)}</td>
      <td>${badge}</td>
    </tr>`;
  }).join('') : '<tr><td colspan="7" class="text-center" style="padding:24px;color:var(--muted)">Δεν υπάρχουν δεδομένα</td></tr>';

  const kinBody = document.getElementById('dash-kin-body');
  const last10 = kin.slice(-10).reverse();
  kinBody.innerHTML = last10.map(k => `<tr>
    <td class="mono">${k.auxon_arithmos}</td>
    <td>${fmtDate(k.imerominia)}</td>
    <td><span class="badge ${k.tipos==='ΕΙΣΑΓΩΓΗ'?'badge-in':k.tipos==='ΚΑΤΑΝΑΛΩΣΗ'?'badge-kat':'badge-out'}">${k.tipos==='ΕΙΣΑΓΩΓΗ'?'📥 ΕΙΣΑΓΩΓΗ':k.tipos==='ΚΑΤΑΝΑΛΩΣΗ'?'🔥 ΚΑΤΑΝΑΛΩΣΗ':k.tipos==='ΕΠΙΣΤΡΟΦΗ'?'🔄 ΕΠΙΣΤΡΟΦΗ':'📤 ΕΞΑΓΩΓΗ'}</span></td>
    <td>${escapeHtml(k.yliko_onoma)}${k.diatomi_mm?` (${escapeHtml(k.diatomi_mm)}mm)`:''}</td>
    <td class="text-right mono">${k.posotita.toFixed(3)} ${escapeHtml(k.monada_metrisis)}</td>
    <td class="mono">${escapeHtml(k.arithmos_parstatikos)||'—'}</td>
  </tr>`).join('') || '<tr><td colspan="6" style="text-align:center;padding:24px;color:var(--muted)">Δεν υπάρχουν κινήσεις</td></tr>';
}

// ── ΑΠΟΘΕΜΑΤΑ ─────────────────────────────────────────────────────────────────
export async function loadApothemates() {
  const apo = await py('get_apothemates');
  const body = document.getElementById('apo-body');
  body.innerHTML = apo.length ? apo.map(r => {
    const yp = r.ypoloipo;
    const cls   = yp > 0 ? 'pos' : 'zero';
    const badge = yp > 0
      ? '<span class="badge badge-neg">⚠️ ΑΔΙΚΑΙΟΛΟΓΗΤΟ</span>'
      : '<span class="badge badge-ok">✅ ΟΚ</span>';
    return `<tr>
      <td><strong>${escapeHtml(r.onoma)}</strong>${r.diatomi_mm?` <small>(${escapeHtml(r.diatomi_mm)}mm)</small>`:''}</td>
      <td>${escapeHtml(r.monada_metrisis)}</td>
      <td class="text-right mono">${r.synolo_eisagogon.toFixed(3)}</td>
      <td class="text-right mono">${r.synolo_katanalosis.toFixed(3)}</td>
      <td class="text-right mono">${r.synolo_epistrofon.toFixed(3)}</td>
      <td class="text-right ${cls}">${yp.toFixed(3)}</td>
      <td class="text-center">${badge}</td>
    </tr>`;
  }).join('') : '<tr><td colspan="7" style="text-align:center;padding:32px;color:var(--muted)">Δεν υπάρχουν υλικά</td></tr>';
}
