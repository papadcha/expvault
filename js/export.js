import { escapeHtml, py } from './utils.js';
import { ylikoLabel } from './state.js';

// ── EXPORT ───────────────────────────────────────────────────────────────────
export async function loadExportDropdowns() {
  const [ylika, adeies] = await Promise.all([py('get_ylika'), py('get_adeies')]);
  const sel = document.getElementById('exp-yliko');
  sel.innerHTML = '<option value="">Όλα τα υλικά</option>' +
    ylika.map(y=>`<option value="${y.id}">${ylikoLabel(y)}</option>`).join('');
  document.getElementById('nonel-detail-cols').textContent = ylika.length;

  const ddSel = document.getElementById('dd-adeia');
  if (ddSel) {
    ddSel.innerHTML = '<option value="">Όλες οι άδειες</option>' +
      adeies.map(a=>`<option value="${a.id}">${escapeHtml(a.arithmos_adeias)}</option>`).join('');
  }
}

export async function doExport(fmt) {
  const btn = event.target;
  const origText = btn.textContent;
  btn.textContent = '⏳ Παραγωγή...';
  btn.disabled = true;
  const msgEl = document.getElementById('export-msg');
  msgEl.innerHTML = '';
  try {
    const yl = document.getElementById('exp-yliko').value;
    const ap = document.getElementById('exp-apo').value;
    const eo = document.getElementById('exp-eos').value;
    const font = document.getElementById('exp-font').value;
    const nonel_mode = document.querySelector('input[name="nonel-mode"]:checked')?.value || 'detail';
    const ext = fmt === 'excel' ? 'xlsx' : fmt;
    const savePath = await window.api.saveFile({
      defaultName: `vivlio_ekrktikon.${ext}`, ext
    });
    if (!savePath) return;
    await py(`export_${fmt}`, {
      yliko_id: yl ? parseInt(yl) : null,
      apo: ap || null, eos: eo || null,
      yliko_label: 'Όλα', period_label: `${ap||'—'} έως ${eo||'—'}`,
      out_path: savePath, font: font, nonel_mode: nonel_mode
    });
    msgEl.innerHTML = `<div class="alert alert-success">✅ Αποθηκεύτηκε: ${escapeHtml(savePath)}</div>`;
  } catch(e) {
    msgEl.innerHTML = `<div class="alert alert-error">❌ Σφάλμα: ${escapeHtml(e.message)}</div>`;
  } finally {
    btn.textContent = origText;
    btn.disabled = false;
  }
}

export async function exportListaAgores() {
  const btn = event.target;
  const origText = btn.textContent;
  btn.textContent = '⏳ Παραγωγή...';
  btn.disabled = true;
  const msgEl = document.getElementById('la-msg');
  msgEl.innerHTML = '';
  try {
    const ap = document.getElementById('la-apo').value;
    const eo = document.getElementById('la-eos').value;
    const savePath = await window.api.saveFile({ defaultName: 'katastasi_agoron.xlsx', ext: 'xlsx' });
    if (!savePath) return;
    await py('export_lista_agores', {
      apo: ap || null, eos: eo || null,
      apo_label: ap || '—', eos_label: eo || '—',
      out_path: savePath
    });
    msgEl.innerHTML = `<div class="alert alert-success">✅ Αποθηκεύτηκε: ${escapeHtml(savePath)}</div>`;
  } catch(e) {
    msgEl.innerHTML = `<div class="alert alert-error">❌ Σφάλμα: ${escapeHtml(e.message)}</div>`;
  } finally {
    btn.textContent = origText;
    btn.disabled = false;
  }
}

export async function exportDeltioDrastiriotitas(fmt) {
  const btn = event.target;
  const origText = btn.textContent;
  btn.textContent = '⏳ Παραγωγή...';
  btn.disabled = true;
  const msgEl = document.getElementById('dd-msg');
  msgEl.innerHTML = '';
  try {
    const ap = document.getElementById('dd-apo').value;
    const eo = document.getElementById('dd-eos').value;
    const adeiaSel = document.getElementById('dd-adeia');
    const adeiaId = adeiaSel?.value || '';
    const adeiaLabel = adeiaId ? adeiaSel.options[adeiaSel.selectedIndex].textContent : null;
    const ext = fmt === 'excel' ? 'xlsx' : 'pdf';
    const savePath = await window.api.saveFile({ defaultName: `deltio_drastiriotitas.${ext}`, ext });
    if (!savePath) return;
    await py(`export_deltio_drastiriotitas_${fmt}`, {
      apo: ap || null, eos: eo || null,
      apo_label: ap || '', eos_label: eo || '',
      adeia_id: adeiaId ? parseInt(adeiaId) : null,
      adeia_label: adeiaLabel,
      out_path: savePath
    });
    msgEl.innerHTML = `<div class="alert alert-success">✅ Αποθηκεύτηκε: ${escapeHtml(savePath)}</div>`;
  } catch(e) {
    msgEl.innerHTML = `<div class="alert alert-error">❌ Σφάλμα: ${escapeHtml(e.message)}</div>`;
  } finally {
    btn.textContent = origText;
    btn.disabled = false;
  }
}
