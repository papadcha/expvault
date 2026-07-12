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
  return r.result;
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
