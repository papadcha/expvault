// ── HTML ESCAPING ────────────────────────────────────────────────────────────
// Χρήση σε κείμενο που προέρχεται από εξωτερικές πηγές (π.χ. αναγνώριση PDF)
// πριν την εισαγωγή του σε innerHTML, ώστε να μην ερμηνεύεται ως markup.
export function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

// ── API HELPERS ──────────────────────────────────────────────────────────────
// Αντί για fetch() → api.call() μέσω IPC
export async function py(cmd, payload = {}) {
  const r = await window.api.call(cmd, payload);
  if (!r.ok) throw new Error(r.error || 'Άγνωστο σφάλμα');
  // Side-channel: κάποιες εντολές (π.χ. add_kinisi) επιστρέφουν επιπλέον
  // adeia_alerts όταν η καταχώρηση άγγιξε άδεια με χαμηλό υπόλοιπο.
  if (r.result && Array.isArray(r.result.adeia_alerts)) {
    r.result.adeia_alerts.forEach(a => window._showToast?.(adeiaAlertMessage(a), 'warn'));
  }
  return r.result;
}

// ── ΆΔΕΙΕΣ: ΧΑΜΗΛΟ ΥΠΟΛΟΙΠΟ ──────────────────────────────────────────────────
export function adeiaAlertMessage(a) {
  return `⚠️ Άδεια ${a.arithmos_adeias} — ${a.nomiki_katigoria}: υπόλοιπο ${a.ypoloipo} ${a.monada_metrisis} (κάτω από το κατώφλι προειδοποίησης)`;
}

// Έλεγχος όλων των αδειών κατά την εκκίνηση της εφαρμογής.
export async function checkAdeiaThresholdsOnStartup() {
  try {
    const alerts = await py('check_adeia_thresholds');
    (alerts || []).forEach(a => window._showToast?.(adeiaAlertMessage(a), 'warn'));
  } catch (e) {
    console.error('[Adeia Alerts] startup check failed:', e);
  }
}

// Ετήσιο backup (ημερολογιακό) + backup ανά άδεια (event-driven, βάσει υπολοίπου) —
// και τα δύο ελέγχονται στην εκκίνηση της εφαρμογής. Το backup #1 ανά άδεια τρέχει
// σιωπηλά· μόνο το backup #2 (υπόλοιπο πολύ κοντά στο μηδέν) δείχνει toast.
export async function checkAdeiaBackupsOnStartup() {
  try {
    const r = await py('check_startup_backups');
    (r?.adeia_notify || []).forEach(a => window._showToast?.(
      `🔒 Αυτόματο backup — Άδεια ${a.arithmos_adeias}, ${a.nomiki_katigoria}: υπόλοιπο ${a.ypoloipo} ${a.monada_metrisis} (πολύ κοντά σε εξάντληση)`,
      'warn'
    ));
  } catch (e) {
    console.error('[Adeia Backups] startup check failed:', e);
  }
}

// ── DATE HELPERS ─────────────────────────────────────────────────────────────
export function todayInput() { return new Date().toISOString().slice(0,10); }

export function _lock(btn) {
  if (!btn) return () => {};
  const orig = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = '⏳ …';
  return () => { btn.disabled = false; btn.innerHTML = orig; };
}
export function fmtDate(s) { if (!s) return ''; const [y,m,d] = s.split('-'); return d?`${d}/${m}/${y}`:s; }

// ── CONFIRM MODAL ────────────────────────────────────────────────────────────
export function closeConfirm() {
  document.getElementById('confirm-modal').classList.remove('open');
  document.getElementById('confirm-ok-btn').onclick = null;
}

export function showConfirm(msg, onOk) {
  document.getElementById('confirm-msg').textContent = msg;
  document.getElementById('confirm-modal').classList.add('open');
  setTimeout(() => document.getElementById('confirm-cancel-btn').focus(), 50);
  document.getElementById('confirm-ok-btn').onclick = () => { closeConfirm(); onOk(); };
}
