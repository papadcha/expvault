import { py, closeConfirm } from './utils.js';
import { loadKiniseis } from './kiniseis.js';
import { loadYlika, clearYlikoForm } from './ylika.js';
import { loadProm, clearPromForm } from './promitheftes.js';
import { loadAdeies, clearAdeiaForm } from './adeies.js';

// ── CONFIRM DELETE ────────────────────────────────────────────────────────────
let _delType, _delId;
export function confirmDelete(type, id) {
  _delType=type; _delId=id;
  const msgs = {
    kinisi:'Διαγραφή αυτής της κίνησης;',
    yliko:'Διαγραφή αυτού του υλικού;',
    prom:'Διαγραφή αυτού του προμηθευτή;',
    adeia:'Διαγραφή αυτής της άδειας;'
  };
  document.getElementById('confirm-msg').textContent = msgs[type] || 'Επιβεβαίωση διαγραφής;';
  document.getElementById('confirm-modal').classList.add('open');
  setTimeout(() => document.getElementById('confirm-cancel-btn').focus(), 50);
}

document.getElementById('confirm-ok-btn').onclick = async () => {
  const cmds = {kinisi:'delete_kinisi', yliko:'delete_yliko', prom:'delete_promitheftis', adeia:'delete_adeia'};
  try {
    await py(cmds[_delType], { id: parseInt(_delId) });
    closeConfirm();
    if (_delType==='kinisi')   loadKiniseis();
    if (_delType==='yliko')    { clearYlikoForm(); loadYlika(); }
    if (_delType==='prom')     { clearPromForm(); loadProm(); }
    if (_delType==='adeia')    { clearAdeiaForm(); loadAdeies(); }
  } catch(e) { closeConfirm(); alert('Σφάλμα: '+e.message); }
};
