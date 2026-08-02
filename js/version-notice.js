import { escapeHtml, py } from './utils.js';

// Parser για VERSIONS.md — αναμένει επικεφαλίδες μορφής "vX.Y.Z — ημ/νία  [ΤΑΓ]"
// ακολουθούμενες από γραμμή παύλων, ίδιο format σε κάθε release. Το ίδιο το
// VERSIONS.md είναι χειροκίνητα word-wrapped (~70 χαρακτήρες) σαν αρχείο
// κειμένου — γραμμές που ΔΕΝ ξεκινούν νέο bullet ("Νέο:"/"Fix:"/"Αλλαγή:"/…)
// είναι συνέχεια του προηγούμενου, ενώνονται σε ένα μπλοκ ώστε να αναδιπλωθεί
// φυσικά στο πλάτος του modal αντί να "κόβεται" στη μέση (βλ. showVersionHistory).
export function parseVersionsMd(text) {
  const lines = text.split('\n');
  const entries = [];
  let current = null;
  const headerRe = /^v(\d+\.\d+\.\d+)\s+—\s+(\S+)(?:\s+\[(.+?)\])?\s*$/;
  const bulletRe = /^[Α-Ωα-ωA-Za-z][\wΑ-Ωα-ω]*(?:\s*\([^)]*\))?:\s/;
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const m = line.match(headerRe);
    if (m && /^-{5,}/.test(lines[i + 1] || '')) {
      if (current) entries.push(current);
      current = { version: m[1], date: m[2], tag: m[3] || null, body: [] };
      i++;
      continue;
    }
    const trimmed = line.trim();
    if (!current || !trimmed) continue;
    if (bulletRe.test(trimmed) || !current.body.length) {
      current.body.push(trimmed);
    } else {
      current.body[current.body.length - 1] += ' ' + trimmed;
    }
  }
  if (current) entries.push(current);
  return entries;
}

export async function showVersionHistory() {
  const modal = document.getElementById('version-history-modal');
  const body  = document.getElementById('version-history-body');
  body.innerHTML = '<p style="color:var(--muted);">Φόρτωση…</p>';
  modal.classList.add('open');

  const [historyResult, allowed, currentVersion] = await Promise.all([
    window.api.getVersionHistory(),
    window.api.getAllowedVersions(),
    window.api.getAppVersion(),
  ]);

  if (!historyResult?.ok) {
    body.innerHTML = '<p style="color:var(--muted);">Δεν ήταν δυνατή η φόρτωση του ιστορικού εκδόσεων.</p>';
    return;
  }

  const entries    = parseVersionsMd(historyResult.content);
  const allowedMap = new Map((allowed?.versions || []).map(v => [v.version, v]));

  const noticeHtml = allowed?.notice
    ? `<div style="background:rgba(220,38,38,0.1);border:1px solid #dc2626;
         border-radius:6px;padding:10px 14px;margin-bottom:12px;font-size:13px;">
         ⚠️ ${escapeHtml(allowed.notice)}</div>`
    : '';

  const entriesHtml = entries.map(e => {
    const safe      = allowedMap.get(e.version);
    const isCurrent = e.version === currentVersion;
    const color = safe ? '#22c55e' : '#ef4444';
    const bg    = safe ? 'rgba(34,197,94,0.06)' : 'rgba(239,68,68,0.06)';
    const action = safe
      ? `<button class="btn btn-outline btn-sm" onclick="window.api.openExternal('${escapeHtml(safe.downloadUrl)}')">⬇ Λήψη</button>`
      : `<span style="color:var(--muted);font-size:11px;">δεν συνιστάται downgrade</span>`;
    return `
      <div style="border-left:3px solid ${color};background:${bg};border-radius:6px;
           padding:8px 10px;margin-bottom:6px;">
        <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap;">
          <div>
            <strong>v${escapeHtml(e.version)}</strong>
            <span style="color:var(--muted);font-size:12px;">— ${escapeHtml(e.date)}</span>
            ${isCurrent ? `<span style="color:var(--accent);font-size:11px;margin-left:6px;">τρέχουσα</span>` : ''}
          </div>
          ${action}
        </div>
        <div style="font-size:12px;color:var(--muted);margin-top:4px;">${e.body.map(escapeHtml).join('<br>')}</div>
      </div>`;
  }).join('');

  const reportOptions = (allowed?.versions || []).map(v =>
    `<option value="${escapeHtml(v.version)}">v${escapeHtml(v.version)}</option>`
  ).join('');

  body.innerHTML = `
    ${noticeHtml}
    <div id="presence-section-box">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;">
        <div style="font-weight:600;font-size:13px;">👥 Συνδεδεμένοι χρήστες</div>
        <button class="btn btn-outline btn-sm" onclick="refreshPresenceList()">🔄 Ανανέωση</button>
      </div>
      <div id="presence-list" style="background:var(--bg);border:1px solid var(--border);border-radius:8px;overflow:hidden;font-size:13px;">
        <div style="padding:16px;color:var(--muted);text-align:center;">Φόρτωση...</div>
      </div>
    </div>
    <div style="display:grid;grid-template-columns:1.3fr 1fr;gap:20px;">
      <div style="max-height:40vh;overflow-y:auto;">${entriesHtml}</div>
      <div style="border-left:1px solid var(--border);padding-left:16px;">
        <div style="font-weight:600;font-size:13px;margin-bottom:6px;">🐞 Αναφορά Προβλήματος</div>
        <p style="font-size:11px;color:var(--muted);margin-bottom:8px;">
          Πράσινο = ασφαλές downgrade (με κουμπί λήψης). Κόκκινο = δεν συνιστάται
          επιστροφή τόσο παλιά. Αν εντοπίσατε από ποια έκδοση ξεκίνησε ένα
          πρόβλημα, αναφέρετέ το εδώ.
        </p>
        <label style="font-size:11px;">Τελευταία έκδοση που δούλευε σωστά</label>
        <select id="report-last-good-version" style="width:100%;margin-bottom:8px;">${reportOptions}</select>
        <label style="font-size:11px;">Περιγραφή προβλήματος</label>
        <textarea id="report-issue-description" rows="4" style="width:100%;margin-bottom:8px;"
                  placeholder="Τι παρατηρήσατε; Πότε συμβαίνει;"></textarea>
        <button class="btn btn-outline btn-sm" id="report-issue-btn"
                onclick="submitVersionIssueReport()">Αποστολή Αναφοράς</button>
      </div>
    </div>
  `;
  refreshPresenceList();
}

// ── PRESENCE (ποιος είναι online) ────────────────────────────────────────────
// Έκδοση + presence ενωμένα σε ένα badge στην κορυφή του sidebar (κλικ ανοίγει
// αυτό εδώ το modal). Η αναλυτική λίστα συνδεδεμένων χρηστών ζει πλέον μόνο
// εδώ μέσα, όχι πια σε ξεχωριστό πίνακα στη σελίδα Backup.
const PRESENCE_ONLINE_MS = 2 * 60 * 1000; // "online" αν last_seen < 2 λεπτά
let _myIdentity = null;

async function _getMyIdentity() {
  if (_myIdentity === null) {
    try { _myIdentity = await py('whoami'); } catch { _myIdentity = false; }
  }
  return _myIdentity || null;
}

function _isOnline(u) {
  const t = new Date(u.last_seen).getTime();
  return !isNaN(t) && (Date.now() - t) < PRESENCE_ONLINE_MS;
}

// Badge στην κορυφή του sidebar: πράσινο αν δεν υπάρχει *άλλος* συνδεδεμένος
// χρήστης (εξαιρείται το δικό μας heartbeat), κόκκινο αν υπάρχει.
export async function updateSidebarPresenceBadge() {
  const badgeEl = document.getElementById('sidebar-presence-badge');
  const labelEl = document.getElementById('sidebar-presence-label');
  if (!badgeEl || !labelEl) return;
  try {
    const [users, me] = await Promise.all([py('list_presence'), _getMyIdentity()]);
    const others = (users || []).filter(u => !(me && u.user === me.user && u.computer === me.computer));
    const onlineOthers = others.filter(_isOnline);
    const online = onlineOthers.length > 0;

    badgeEl.classList.toggle('presence-red', online);
    labelEl.textContent = online ? `${onlineOthers.length} online` : '';
    badgeEl.title = online
      ? onlineOthers.map(u => `${u.user} (${u.computer})`).join(', ')
      : 'Δες τι άλλαξε';
  } catch {
    // Χωρίς configured remote/rclone το list_presence επιστρέφει απλά άδεια
    // λίστα (χωρίς exception) — ένα throw εδώ σημαίνει κάτι πιο ασυνήθιστο,
    // παραμένει πράσινο χωρίς ετικέτα.
    badgeEl.classList.remove('presence-red');
    labelEl.textContent = '';
  }
}

// Λίστα συνδεδεμένων χρηστών μέσα στο modal Ιστορικού Εκδόσεων — όχι πίνακας,
// δυναμικές ισομεγέθεις κάρτες σε μία γραμμή, μόνο για currently-online
// χρήστες (offline/παλιές εγκαταστάσεις δεν έχουν θέση εδώ).
export async function refreshPresenceList() {
  const el  = document.getElementById('presence-list');
  const box = document.getElementById('presence-section-box');
  if (!el) return;
  try {
    const [fetched, me] = await Promise.all([py('list_presence'), _getMyIdentity()]);
    const users = (fetched || []).slice();

    // Όποιος βλέπει αυτή τη λίστα είναι, εξ ορισμού, online αυτή τη στιγμή —
    // αν το δικό του heartbeat δεν έχει προλάβει να συγχρονιστεί ακόμα (ή το
    // τελευταίο γνωστό heartbeat είναι παλιό/stale, π.χ. προηγούμενη
    // συνεδρία), προσθέτουμε φρέσκο entry εδώ ώστε η λίστα να μην ισχυρίζεται
    // ποτέ "κανένας χρήστης" ενώ κάποιος την κοιτάει.
    const alreadyListed = me && users.some(u => u.user === me.user && u.computer === me.computer && _isOnline(u));
    if (me && !alreadyListed) {
      users.push({ user: me.user, computer: me.computer, last_seen: new Date().toISOString(), _isMe: true });
    }

    const isOnline = u => u._isMe || _isOnline(u);
    const onlineUsers = users.filter(isOnline);
    const others = onlineUsers.filter(u => !u._isMe);
    if (box) {
      box.classList.toggle('presence-alert', others.length > 0);
      box.classList.toggle('presence-clear', others.length === 0);
    }

    // --accent = δική μας κάρτα όταν υπάρχει έστω κι ένας άλλος, ίδιο ύφος με
    // το lab-galatista (--ok/--fail) για το πράσινο/κόκκινο — το πορτοκαλί
    // παραμένει το δικό μας --accent (το lab-galatista δανείζεται εκεί το
    // πορτοκαλί του λογότυπου του, δεν είναι κοινό token ούτε στο δικό του app).
    const ME_ORANGE = '#e8a020', ME_GREEN = '#16a34a', OTHER_RED = '#dc2626';
    const cards = onlineUsers
      .slice()
      .sort((a, b) => new Date(b.last_seen) - new Date(a.last_seen))
      .map(u => {
        const color = u._isMe ? (others.length === 0 ? ME_GREEN : ME_ORANGE) : OTHER_RED;
        return `<div style="flex:1 1 0;min-width:0;padding:8px 10px;border-radius:6px;
             background:${color}20;border:1px solid ${color}60;overflow:hidden;
             white-space:nowrap;text-overflow:ellipsis;">
          <span style="font-weight:700;font-size:13px;color:${color};">${escapeHtml(u.user)}</span>
          <span style="font-size:12px;color:var(--muted);"> — ${escapeHtml(u.computer)}</span>
        </div>`;
      }).join('');
    el.innerHTML = `<div style="display:flex;gap:8px;padding:10px;">${cards}</div>`;
  } catch (e) {
    el.innerHTML = `<div style="padding:16px;color:#ef4444;">Σφάλμα: ${escapeHtml(e.message)}</div>`;
  }
}

export async function submitVersionIssueReport() {
  const lastGood = document.getElementById('report-last-good-version')?.value;
  const desc     = document.getElementById('report-issue-description')?.value?.trim();
  if (!lastGood) { window._showToast('⚠️ Επιλέξτε έκδοση', 'warn'); return; }
  if (!desc)     { window._showToast('⚠️ Περιγράψτε το πρόβλημα', 'warn'); return; }

  const btn = document.getElementById('report-issue-btn');
  if (btn) btn.disabled = true;
  try {
    const result = await window.api.reportVersionIssue(lastGood, desc);
    if (result?.ok) {
      window._showToast('✅ Η αναφορά στάλθηκε', 'success');
      document.getElementById('version-history-modal').classList.remove('open');
    } else {
      window._showToast('⚠️ Σφάλμα αναφοράς: ' + (result?.error || ''), 'error');
    }
  } finally {
    if (btn) btn.disabled = false;
  }
}

// Banner "νέα έκδοση διαθέσιμη" / "γνωστό πρόβλημα σε αυτή την έκδοση,
// προτείνεται προσωρινό downgrade" — από version-check.js, ξεχωριστό κανάλι
// (version-notice) από το update-status του electron-updater.
export function showVersionNotice(info) {
  const banner = document.getElementById('version-notice-banner');
  const msg    = document.getElementById('version-notice-msg');
  const btn    = document.getElementById('version-notice-btn');
  const isRollback = info.kind === 'rollback';

  msg.textContent = isRollback
    ? `Η έκδοσή σας (v${info.current}) έχει γνωστό πρόβλημα. Προτείνεται προσωρινή επιστροφή σε v${info.latest}${info.notes ? ' — ' + info.notes : ''}`
    : `Νέα έκδοση διαθέσιμη: v${info.latest} (τρέχουσα: v${info.current})`;
  btn.textContent = isRollback ? `Λήψη v${info.latest}` : 'Λήψη';
  btn.onclick = () => window.api.openExternal(info.url);
  banner.style.display = 'flex';
}
if (window.api?.onVersionNotice) {
  window.api.onVersionNotice(showVersionNotice);
}

// ── ΙΣΤΟΡΙΚΟ ΕΚΔΟΣΕΩΝ / SAFE DOWNGRADE FLOOR ─────────────────────────────────
// Ξεχωριστό, παράλληλο μηχανισμό από το AUTO-UPDATE (electron-updater) — αυτό
// καλύπτει "ποια έκδοση έχει γνωστό πρόβλημα / μέχρι πού μπορείς να κάνεις
// ασφαλές downgrade", κάτι που το electron-updater δεν ξέρει.
if (window.api?.getAppVersion) {
  window.api.getAppVersion().then(ver => {
    if (!ver) return;
    const el = document.getElementById('sidebar-version');
    if (el) el.textContent = 'v' + ver;
    const tbEl = document.getElementById('titlebar-version');
    if (tbEl) tbEl.textContent = 'v' + ver;
  });
}

// Ίδιο productName με το package.json's build.productName — έτσι ένα build
// "ExpVault+" (side-by-side με το κανονικό, βλ. dual-install setup) φαίνεται
// αμέσως διαφορετικό στο titlebar/sidebar, όχι μόνο στον αριθμό έκδοσης.
if (window.api?.getAppProductName) {
  window.api.getAppProductName().then(name => {
    if (!name) return;
    const tbNameEl = document.getElementById('titlebar-app-name');
    if (tbNameEl) tbNameEl.textContent = name;
    const logoBtn = document.getElementById('sidebar-logo-btn');
    if (logoBtn) logoBtn.title = `${name} — Αρχική`;
  });
}
